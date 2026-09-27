"""Entity resolution: collapse SuspectEntity rows into canonical RepeatOffenderCluster
groups, across name-transliteration variants, shared identifiers, and (via the hook
`apply_mo_edges`) shared modus operandi across stations.

Scale note: naive pairwise comparison of N suspects is O(N^2), which does not survive
CCTNS-scale data (crores of FIRs). We avoid it with:
  - an inverted index on normalized phone/vehicle numbers for O(1) exact-identifier lookup,
  - blocking candidate name-pairs by Double Metaphone key so fuzzy comparison only runs
    within a phonetic bucket, not across the whole suspect pool,
  - a union-find (disjoint set union) to merge clusters incrementally in near-linear time.
A production system would swap the in-memory DSU + NetworkX for a graph database
(e.g. Neo4j) with the same blocking strategy; the algorithm itself does not change.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from metaphone import doublemetaphone
from rapidfuzz import fuzz

from app.core.config import get_settings

_PHONE_NORM_RE = re.compile(r"\D")


def _normalize_phone(phone: str) -> str:
    digits = _PHONE_NORM_RE.sub("", phone)
    return digits[-10:] if len(digits) >= 10 else digits


def _normalize_vehicle(plate: str) -> str:
    return re.sub(r"[\s\-]", "", plate).upper()


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z ]", "", name).strip().lower()


def _metaphone_key(name: str) -> str:
    tokens = _normalize_name(name).split()
    if not tokens:
        return ""
    # Use the primary metaphone code of the longest token (most distinctive), which is
    # robust to honorifics/initials like "Mohd." / "M." being dropped or reordered.
    longest = max(tokens, key=len)
    primary, _ = doublemetaphone(longest)
    return primary


@dataclass
class SuspectRecord:
    suspect_id: int
    fir_id: int
    station_district: str
    name: str | None
    aliases: list[str]
    phone_numbers: list[str]
    vehicle_numbers: list[str]


@dataclass
class _DSU:
    parent: dict[int, int] = field(default_factory=dict)
    reasons: dict[tuple[int, int], str] = field(default_factory=dict)

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int, reason: str) -> None:
        self.parent.setdefault(a, a)
        self.parent.setdefault(b, b)
        ra, rb = self.find(a), self.find(b)
        key = (min(a, b), max(a, b))
        self.reasons[key] = reason
        if ra != rb:
            self.parent[ra] = rb


@dataclass
class ClusterResult:
    canonical_id: str
    member_suspect_ids: list[int]
    member_fir_ids: list[int]
    districts_involved: list[str]
    confidence_score: float
    match_reasons: list[str]
    syndicate_flag: bool


def resolve_entities(
    suspects: list[SuspectRecord],
    mo_edges: list[tuple[int, int, float]] | None = None,
) -> list[ClusterResult]:
    """Run identifier + phonetic/fuzzy resolution, then fold in MO-similarity edges
    (suspect_id, suspect_id, cosine_similarity) supplied by engine.mo_similarity.

    Returns one ClusterResult per connected component that contains >= 2 suspects OR
    exactly 1 suspect linked across >=1 FIR (still surfaced, syndicate_flag reflects
    whether >=2 districts are involved).
    """
    settings = get_settings()
    threshold = settings.entity_fuzzy_threshold

    named = [s for s in suspects if s.name]
    dsu = _DSU()
    pair_reasons: dict[tuple[int, int], list[str]] = defaultdict(list)
    pair_scores: dict[tuple[int, int], float] = {}
    # Evidence type per pair, strongest kind wins if a pair is linked more than one way:
    # "exact" (shared phone/vehicle) > "phonetic" (name match) > "mo" (narrative similarity
    # alone). This matters for confidence: a shared phone number is much stronger proof of
    # common identity than two crime narratives reading alike, even when the raw MO cosine
    # score is numerically higher than the phonetic composite score.
    _KIND_RANK = {"exact": 3, "phonetic": 2, "mo": 1}
    pair_kind: dict[tuple[int, int], str] = {}

    def _note_kind(key: tuple[int, int], kind: str) -> None:
        if _KIND_RANK[kind] > _KIND_RANK.get(pair_kind.get(key, "mo"), 0) or key not in pair_kind:
            pair_kind[key] = kind

    # --- Priority 1: exact identifier match (phone / vehicle) — inverted index, O(N) ---
    phone_index: dict[str, list[int]] = defaultdict(list)
    vehicle_index: dict[str, list[int]] = defaultdict(list)
    for s in suspects:
        for p in s.phone_numbers:
            norm = _normalize_phone(p)
            if len(norm) >= 7:  # avoid over-merging on short/garbage numbers
                phone_index[norm].append(s.suspect_id)
        for v in s.vehicle_numbers:
            norm = _normalize_vehicle(v)
            if len(norm) >= 6:
                vehicle_index[norm].append(s.suspect_id)

    for norm, ids in phone_index.items():
        if len(ids) < 2:
            continue
        base = ids[0]
        for other in ids[1:]:
            key = (min(base, other), max(base, other))
            dsu.union(base, other, "exact phone match")
            pair_reasons[key].append(f"exact phone match (ending {norm[-4:]})")
            pair_scores[key] = max(pair_scores.get(key, 0.0), 1.0)
            _note_kind(key, "exact")

    for norm, ids in vehicle_index.items():
        if len(ids) < 2:
            continue
        base = ids[0]
        for other in ids[1:]:
            key = (min(base, other), max(base, other))
            dsu.union(base, other, "exact vehicle match")
            pair_reasons[key].append(f"exact vehicle match ({norm})")
            pair_scores[key] = max(pair_scores.get(key, 0.0), 1.0)
            _note_kind(key, "exact")

    # --- Priority 2: phonetic blocking + fuzzy match — only compare within a bucket ---
    blocks: dict[str, list[SuspectRecord]] = defaultdict(list)
    for s in named:
        key = _metaphone_key(s.name)  # type: ignore[arg-type]
        if key:
            blocks[key].append(s)

    for key, members in blocks.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if a.suspect_id == b.suspect_id:
                    continue
                string_ratio = fuzz.token_sort_ratio(_normalize_name(a.name), _normalize_name(b.name))  # type: ignore[arg-type]
                if string_ratio < threshold:
                    continue
                phonetic_match = 1.0  # they're in the same metaphone block by construction
                a_aliases = {al.lower() for al in a.aliases} | {a.name.lower()}  # type: ignore[union-attr]
                b_aliases = {al.lower() for al in b.aliases} | {b.name.lower()}  # type: ignore[union-attr]
                alias_overlap = 1.0 if (a_aliases & b_aliases) else 0.0
                composite = 0.5 * (string_ratio / 100) + 0.3 * phonetic_match + 0.2 * alias_overlap
                reason = f"phonetic+fuzzy name match {composite:.2f} ('{a.name}' ~ '{b.name}')"
                key = (min(a.suspect_id, b.suspect_id), max(a.suspect_id, b.suspect_id))
                dsu.union(a.suspect_id, b.suspect_id, reason)
                pair_reasons[key].append(reason)
                pair_scores[key] = max(pair_scores.get(key, 0.0), composite)
                _note_kind(key, "phonetic")

    # --- Fold in MO-similarity edges from a different engine (inter-district signature match) ---
    for sid_a, sid_b, score in mo_edges or []:
        reason = f"MO similarity {score:.2f} across stations"
        key = (min(sid_a, sid_b), max(sid_a, sid_b))
        dsu.union(sid_a, sid_b, reason)
        pair_reasons[key].append(reason)
        pair_scores[key] = max(pair_scores.get(key, 0.0), score)
        _note_kind(key, "mo")

    # --- Materialize connected components ---
    by_id = {s.suspect_id: s for s in suspects}
    components: dict[int, list[int]] = defaultdict(list)
    all_ids = {s.suspect_id for s in suspects}
    # ensure every suspect has a DSU entry even if never unioned (singleton cluster, dropped later)
    for sid in all_ids:
        dsu.parent.setdefault(sid, sid)
    for sid in all_ids:
        root = dsu.find(sid)
        components[root].append(sid)

    results: list[ClusterResult] = []
    for root, member_ids in components.items():
        if len(member_ids) < 2:
            continue  # singletons are not "repeat offenders" — nothing to flag
        members = [by_id[i] for i in member_ids]
        fir_ids = sorted({m.fir_id for m in members})
        districts = sorted({m.station_district for m in members})
        reasons: list[str] = []
        scores_by_kind: dict[str, list[float]] = defaultdict(list)
        for i in range(len(member_ids)):
            for j in range(i + 1, len(member_ids)):
                key = (min(member_ids[i], member_ids[j]), max(member_ids[i], member_ids[j]))
                reasons.extend(pair_reasons.get(key, []))
                if key in pair_scores:
                    scores_by_kind[pair_kind[key]].append(pair_scores[key])
        reasons = list(dict.fromkeys(reasons))  # de-dupe, preserve order

        # Confidence reflects the STRONGEST evidence type present, not just the highest raw
        # number — a shared phone/vehicle is much stronger proof of common identity than two
        # narratives reading alike, even when the MO cosine score is numerically higher than
        # a phonetic composite score. Pure MO-similarity-only evidence (no name or identifier
        # corroboration at all) is deliberately dampened: it is a pattern worth a human
        # analyst's attention, not proof, and must never outrank identifier-based matches.
        if scores_by_kind["exact"]:
            confidence = 0.97
        elif scores_by_kind["phonetic"]:
            confidence = round(sum(scores_by_kind["phonetic"]) / len(scores_by_kind["phonetic"]), 2)
        elif scores_by_kind["mo"]:
            raw = sum(scores_by_kind["mo"]) / len(scores_by_kind["mo"])
            confidence = round(min(raw * 0.8, 0.80), 2)
        else:
            confidence = 0.75

        primary_name = next((m.name for m in members if m.name), f"Unknown-{root}")
        # "Syndicate" is a strong claim — reserve it for cross-district links backed by
        # hard evidence (a shared phone/vehicle) or high aggregate confidence, not a
        # single coincidental same-district-spanning name match. A 2-district cluster
        # held together only by a 0.72 phonetic score is a lead worth surfacing, not
        # something to badge as an organized operation.
        has_exact_evidence = any("exact" in r for r in reasons)
        syndicate_flag = len(districts) >= 2 and (has_exact_evidence or confidence >= 0.85)
        results.append(
            ClusterResult(
                canonical_id=f"cluster-{root}",
                member_suspect_ids=sorted(member_ids),
                member_fir_ids=fir_ids,
                districts_involved=districts,
                confidence_score=min(confidence, 0.99),
                match_reasons=reasons,
                syndicate_flag=syndicate_flag,
            )
        )

    results.sort(key=lambda c: (-c.syndicate_flag, -c.confidence_score, -len(c.member_fir_ids)))
    return results
