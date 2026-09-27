# Solution Overview

## What We Built

**Bob Engine** ingests digitized FIRs and automatically surfaces repeat offenders
and criminal syndicates that span multiple police stations and districts - links a
human analyst would otherwise have to notice by memory. It ships as a small
dashboard (station statistics, a flagged repeat-offender list, and an interactive
syndicate graph) backed by a FastAPI service, with role-based access control so a
Station Officer, a District SP, and the State DGP each see only what their rank is
entitled to see. IBM Bob is used specifically as the FIR extraction step - turning
a raw digitized FIR document into structured fields - not as a chatbot bolted onto
the UI.

## How It Works

1. A digitized FIR (raw text, following the standard CCTNS labeled-field layout)
   is submitted via `POST /ingest`.
2. **Extraction**: Bob's inference API is called first to pull structured fields
   (station, district, crime category, IPC/Act sections, modus operandi, and every
   named or described suspect with their identifiers) out of the raw text. If Bob
   is unreachable or returns something unusable, a deterministic regex/section
   parser (`engine/parser.py`) does the same job as a fallback - the pipeline never
   blocks on Bob being available.
3. **Entity resolution** (`engine/entity_resolution.py`) links suspects across
   FIRs by three independent signals, in order of strength: an exact shared phone
   number or vehicle number (strongest), a phonetic + fuzzy name match (handles
   transliteration variants like "Mohd. Aslam" / "Mohammad Aslaam" / "M. Aslam"),
   and modus-operandi similarity across stations. No suspect is dropped for lacking
   a name - identifier- and description-only suspects still link.
4. **MO similarity** (`engine/mo_similarity.py`) embeds each FIR's narrative with
   a sentence-transformer and flags near-identical "scripts" reused in a different
   district - the actual Jamtara-style signal.
5. A **union-find** merges every linked pair into `RepeatOffenderCluster` records,
   each carrying a confidence score and a human-readable list of *why* the link was
   made - never a black-box number.
6. The **graph builder** (`engine/graph_builder.py`) exports a station/FIR/suspect
   graph for the dashboard's interactive syndicate view.
7. Every read - dashboard stats, the offender list, the graph, a suspect dossier -
   passes through one shared, **RBAC-scoped** service layer before it reaches the
   API, so jurisdiction filtering cannot be bypassed by a route that "forgets" to
   apply it.

## Architecture Diagram

> See [`architecture.md`](architecture.md) for the full diagram and component table.

```
[Digital FIR text] -> [Bob extraction, w/ deterministic fallback] -> [PostgreSQL]
                                                                          |
                                    +-------------------------------------+
                                    v
      [Entity resolution + MO similarity + Graph builder]  (all deterministic)
                                    |
                                    v
                    [RBAC-scoped service layer]  <-- X-User-Role / X-User-Station
                                    |
                                    v
                         [REST API]  ->  [React dashboard]
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Bob is used *only* for extraction, not as a chatbot | Keeps the LLM out of every decision that must be explainable and reproducible (linking, scoring, RBAC). A judge or officer can audit every match without asking "what did the model think." |
| Deterministic fallback parser runs whenever Bob is unavailable | The whole pipeline - and the demo - must work even if the inference endpoint is unreachable, rate-limited, or slow. Reproducibility does not depend on a live third-party call. |
| Confidence is weighted by evidence *type*, not raw score | A shared phone number is much stronger proof of common identity than two narratives reading alike, even when the raw MO cosine similarity is numerically higher than a phonetic match. Pure MO-only evidence is deliberately capped below identifier- or name-based evidence so it can never outrank real proof. |
| `syndicate_flag` requires either an exact identifier or high aggregate confidence, not just "2+ districts" | Reserves the "syndicate" label - a strong claim - for links backed by real evidence, not a coincidental cross-district name collision. |
| RBAC resolved once per request, in a FastAPI dependency, against the database | Every read (stats, offender list, graph, dossier) is scoped identically; there is no route where scoping could be forgotten. |
| No copilot / chat UI, no real-time alerting | Deliberately cut from an earlier, broader design to keep the demo's core - ingest, link, explain, scope - fully built and fully working end-to-end, rather than partially building a larger surface. |
| Union-find + phonetic blocking for entity resolution | Naive pairwise suspect comparison is O(n^2), which does not survive CCTNS's 3-crore-FIR scale. Blocking candidate pairs by Double Metaphone key, then merging with a disjoint-set union, keeps resolution close to linear and incremental. |

## IBM Technologies Used

- **IBM Bob (inference API)**: called from `engine/bob_client.py` as the sole FIR
  extraction path when reachable - given a raw FIR document, it returns the
  structured JSON (station, district, crime category, sections, modus operandi,
  and every suspect with name/aliases/identifiers) that the rest of the pipeline
  is built on. Every field the deterministic fallback parser reconstructs is the
  same field Bob is asked to extract, so the two paths are interchangeable from
  the ingestion service's point of view.
