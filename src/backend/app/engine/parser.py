"""Deterministic fallback FIR parser.

This is the guarantee that Bob Engine works end-to-end even if the Bob inference
API is unreachable, unauthenticated, or slow: every field Bob's extraction would
produce can also be recovered — less gracefully, but reliably — with regexes and
keyword heuristics against the standard CCTNS/NCRB "digital FIR copy" text layout
(the labeled-field format real digitized FIRs are OCR'd/typed into).

Nothing here calls an LLM. It is intentionally boring.
"""
from __future__ import annotations

import re

from app.schemas.fir_schema import ExtractedFIR, ExtractedSuspect

_PHONE_RE = re.compile(r"(?:\+?91[-\s]?)?[6-9]\d{9}\b")
_VEHICLE_RE = re.compile(r"\b[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{4}\b")

_FIELD_RE = {
    "fir_number": re.compile(r"FIR\s*No\.?\s*[:\-]?\s*([A-Za-z0-9/\-]+)", re.IGNORECASE),
    "district": re.compile(r"District\s*[:\-]\s*([A-Za-z .]+?)(?:\n|,|$)", re.IGNORECASE),
    "station_name": re.compile(r"(?:P\.?S\.?|Police\s+Station)\s*[:\-]\s*([A-Za-z0-9 .]+?)(?:\n|,|$)", re.IGNORECASE),
    "timestamp": re.compile(r"Date(?:/Time)?\s*(?:of\s*(?:FIR|Occurrence))?\s*[:\-]\s*([0-9./\-: ]+?)(?:\n|,|$)", re.IGNORECASE),
    "ipc_sections_line": re.compile(r"(?:Act\s*&?\s*Sections?|Sections?)\s*[:\-]\s*(.+?)(?:\n|$)", re.IGNORECASE),
}

# Ordered so a longer/more-specific label is tried before a shorter one that could
# prefix-match it (e.g. "Modus Operandi" before a bare "Operandi" would never happen,
# but keeping this explicit avoids subtle ordering bugs as labels are added).
_SECTION_LABELS: list[str] = [
    "Modus Operandi",
    "Manner of Occurrence",
    "Manner of the Occurrence",
    "Brief Facts",
    "Accused Details",
    "Accused Person(s)",
    "Accused Name(s)",
    "Property/Loss",
    "Property Details",
    "Action Taken",
    "Complainant Name",
    "Complainant Address",
    "Date/Time of Occurrence",
    "Place of Occurrence",
]

_SECTION_SPLIT_RE = re.compile(
    r"(?P<label>" + "|".join(re.escape(lbl) for lbl in sorted(_SECTION_LABELS, key=len, reverse=True)) + r")\s*[:\-]\s*",
    re.IGNORECASE,
)


def _split_into_sections(text: str) -> dict[str, str]:
    """Find every known section header in `text` and return {lowercased label: body},
    where each body runs from right after its header to right before the next known
    header (of any kind) or end of string. Robust to inconsistent blank-line usage —
    the real failure mode of naive per-field stop-token regexes."""
    matches = list(_SECTION_SPLIT_RE.finditer(text))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        label = m.group("label").strip().lower()
        body = text[start:end].strip()
        # First match wins for a given label (a document shouldn't repeat headers,
        # but be defensive rather than let a duplicate silently overwrite good data).
        sections.setdefault(label, body)
    return sections

_CRIME_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Cyber Fraud", ["otp", "upi", "kyc update", "sim swap", "phishing", "net banking", "fraudulent transaction", "cyber fraud", "online fraud", "investment scheme"]),
    ("Theft", ["theft", "stolen", "stole", "burglary", "chain snatching", "broke the lock"]),
    ("Robbery", ["robbery", "snatched", "knifepoint", "gunpoint", "looted"]),
    ("Assault", ["assault", "grievous hurt", "beaten", "attacked with"]),
    ("Extortion", ["extortion", "ransom", "blackmail", "protection money"]),
    ("Narcotics", ["narcotic", "drugs", "smack", "ganja", "nds act", "ndps"]),
    ("Missing Person", ["missing since", "untraced", "missing person"]),
]

# Real FIRs classify almost unambiguously by their IPC / special-Act sections — far more
# reliable than keyword-spotting free text. Tried first; keyword matching is the fallback
# for narratives whose Act & Sections line the parser couldn't read.
_SECTION_CATEGORY_MAP: list[tuple[str, list[str]]] = [
    ("Cyber Fraud", ["419", "420", "465", "468", "471", "66c", "66d"]),
    ("Theft", ["379", "380", "454", "457"]),
    ("Robbery", ["392", "393", "394", "395", "397"]),
    ("Assault", ["323", "324", "325", "341", "506"]),
    ("Extortion", ["384", "387"]),
    ("Narcotics", ["ndps"]),
]


def _classify_by_sections(section_line: str | None) -> str | None:
    if not section_line:
        return None
    lowered = section_line.lower()
    if "missing person" in lowered:
        return "Missing Person"
    tokens = {t.lower() for t in re.findall(r"\d{2,3}[A-Za-z]{0,2}|ndps", lowered)}
    for category, codes in _SECTION_CATEGORY_MAP:
        if tokens & set(codes):
            return category
    return None

_IPC_SECTION_TOKEN_RE = re.compile(r"\b\d{1,3}[A-Za-z]?\b")


def _extract_field(text: str, key: str) -> str | None:
    m = _FIELD_RE[key].search(text)
    if not m:
        return None
    return m.group(1).strip()


def _classify_crime_category(text: str, section_line: str | None) -> str:
    by_section = _classify_by_sections(section_line)
    if by_section:
        return by_section
    lowered = text.lower()
    for category, keywords in _CRIME_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return category
    return "Other / Unclassified"


def _split_ipc_sections(line: str | None) -> list[str]:
    if not line:
        return []
    # e.g. "IPC 419, 420, 66D IT Act" -> ["419", "420", "66D"]
    tokens = re.findall(r"\d{2,3}[A-Za-z]{0,2}", line)
    # de-dupe, keep order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _extract_suspects(text: str, sections: dict[str, str]) -> list[ExtractedSuspect]:
    block = sections.get("accused details") or sections.get("accused person(s)") or sections.get("accused name(s)") or ""
    phones_global = _PHONE_RE.findall(text)
    vehicles_global = _VEHICLE_RE.findall(text)

    if not block.strip():
        # No labeled accused block at all — still surface any identifiers found
        # in the narrative as a single "unknown" suspect if we found any.
        if phones_global or vehicles_global:
            return [
                ExtractedSuspect(
                    name=None,
                    phone_numbers=list(dict.fromkeys(phones_global)),
                    vehicle_numbers=list(dict.fromkeys(vehicles_global)),
                )
            ]
        return []

    # Accused block may list multiple suspects separated by ';' or numbered lines.
    entries = re.split(r"\n\s*\d+[.)]\s*|;\s*", block)
    suspects: list[ExtractedSuspect] = []
    for entry in entries:
        entry = entry.strip()
        # The first entry keeps its "1) " marker (nothing precedes it to split on) —
        # strip any leading list numbering before field regexes run.
        entry = re.sub(r"^\d+[.)]\s*", "", entry)
        if not entry:
            continue
        name_match = re.search(r"^(?:Name\s*[:\-]\s*)?([A-Za-z .]+?)(?:,|\balias\b|\(|$)", entry, re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else None
        if name and re.match(r"^(unknown|not\s*known|unidentified|na|n/a)\b", name, re.IGNORECASE):
            name = None

        aliases = re.findall(r"alias\s+([A-Za-z .]+?)(?:,|\)|$)", entry, re.IGNORECASE)
        phones = _PHONE_RE.findall(entry) or (phones_global if len(entries) == 1 else [])
        vehicles = _VEHICLE_RE.findall(entry) or (vehicles_global if len(entries) == 1 else [])
        desc_match = re.search(r"(?:description|built|complexion)\s*[:\-]\s*(.+?)(?:,|$)", entry, re.IGNORECASE)

        suspects.append(
            ExtractedSuspect(
                name=name,
                aliases=[a.strip() for a in aliases],
                phone_numbers=list(dict.fromkeys(phones)),
                vehicle_numbers=list(dict.fromkeys(vehicles)),
                physical_description=desc_match.group(1).strip() if desc_match else None,
            )
        )

    if not suspects and (phones_global or vehicles_global):
        suspects.append(
            ExtractedSuspect(
                phone_numbers=list(dict.fromkeys(phones_global)),
                vehicle_numbers=list(dict.fromkeys(vehicles_global)),
            )
        )
    return suspects


def parse_fir_text(raw_text: str) -> ExtractedFIR:
    """Regex/heuristic extraction. Never raises — worst case, returns mostly-empty fields."""
    sections = _split_into_sections(raw_text)
    mo = sections.get("modus operandi") or sections.get("manner of occurrence") or sections.get("manner of the occurrence") or sections.get("brief facts") or ""
    return ExtractedFIR(
        fir_number=_extract_field(raw_text, "fir_number"),
        station_name=_extract_field(raw_text, "station_name"),
        district=_extract_field(raw_text, "district"),
        timestamp=_extract_field(raw_text, "timestamp"),
        crime_category=_classify_crime_category(raw_text, _extract_field(raw_text, "ipc_sections_line")),
        ipc_sections=_split_ipc_sections(_extract_field(raw_text, "ipc_sections_line")),
        modus_operandi=" ".join(mo.split()),
        suspects=_extract_suspects(raw_text, sections),
    )
