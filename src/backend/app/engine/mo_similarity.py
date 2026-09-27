"""Modus-operandi semantic clustering.

Vectorizes each FIR's `modus_operandi` narrative with a sentence-transformer and
flags pairs from DIFFERENT police stations whose cosine similarity clears a
threshold as an inter-district "signature match" — the thing a human analyst
would never spot by reading FIRs one at a time, three districts apart.

The model loads lazily and once (module-level singleton) since it's the slow part
(~80MB download on first run, then fast). If the model can't load for any reason,
MO-similarity edges are simply skipped — entity resolution still runs on
identifiers + name matching alone, so the pipeline degrades gracefully rather
than failing.
"""
from __future__ import annotations

import logging

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger("bob_engine.mo_similarity")

_model = None
_model_load_failed = False


def _get_model():
    global _model, _model_load_failed
    if _model is not None or _model_load_failed:
        return _model
    try:
        from sentence_transformers import SentenceTransformer

        settings = get_settings()
        _model = SentenceTransformer(settings.mo_embedding_model)
        logger.info("mo_similarity: loaded embedding model '%s'", settings.mo_embedding_model)
    except Exception:  # noqa: BLE001
        logger.exception("mo_similarity: failed to load embedding model — MO edges will be skipped")
        _model_load_failed = True
        _model = None
    return _model


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def compute_inter_district_mo_edges(
    fir_records: list[tuple[int, str, str]],  # (fir_id, station_district, modus_operandi)
    fir_to_suspect_ids: dict[int, list[int]],  # fir_id -> [suspect_id, ...]
) -> list[tuple[int, int, float]]:
    """Returns (suspect_id_a, suspect_id_b, cosine_similarity) edges for every pair of
    FIRs from different districts whose MO text is semantically similar above threshold,
    projected onto every suspect-pair named in those two FIRs (so entity_resolution can
    fold the signal directly into its union-find)."""
    settings = get_settings()
    usable = [(fid, dist, mo) for fid, dist, mo in fir_records if mo and mo.strip()]
    if len(usable) < 2:
        return []

    model = _get_model()
    if model is None:
        return []

    ids = [u[0] for u in usable]
    districts = [u[1] for u in usable]
    texts = [u[2] for u in usable]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    edges: list[tuple[int, int, float]] = []
    n = len(usable)
    for i in range(n):
        for j in range(i + 1, n):
            if districts[i] == districts[j]:
                continue  # only inter-district edges are interesting here
            score = _cosine(embeddings[i], embeddings[j])
            if score >= settings.mo_similarity_threshold:
                suspects_i = fir_to_suspect_ids.get(ids[i], [])
                suspects_j = fir_to_suspect_ids.get(ids[j], [])
                for sa in suspects_i:
                    for sb in suspects_j:
                        if sa != sb:
                            edges.append((sa, sb, round(score, 4)))
    return edges
