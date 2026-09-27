"""CLI seed loader: creates police stations, ingests the 100 sample FIRs (through the
same extraction path — Bob first, deterministic fallback second — as any real upload),
then runs syndicate detection.

Usage:
    python -m app.seed                # full seed: stations + ingest + detect
    python -m app.seed --detect-only  # re-run detection against whatever is already ingested
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from sqlmodel import Session, select

from app.core.database import engine, init_db
from app.models.fir_models import PoliceStation
from app.services import intelligence

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bob_engine.seed")

SEED_PATH = Path(__file__).parent / "data" / "seed_firs.json"


def _ensure_stations(session: Session, stations: list[dict]) -> dict[str, int]:
    """Idempotent: insert any station not already present by (name, district). Returns
    a {station_name: station_id} lookup for the ingest step."""
    existing = {(s.name, s.district): s.id for s in session.exec(select(PoliceStation)).all()}
    name_to_id: dict[str, int] = {}
    for s in stations:
        key = (s["name"], s["district"])
        if key in existing:
            name_to_id[s["name"]] = existing[key]
            continue
        row = PoliceStation(name=s["name"], district=s["district"], zone=s["zone"], state="Uttar Pradesh")
        session.add(row)
        session.flush()
        name_to_id[s["name"]] = row.id  # type: ignore[assignment]
        existing[key] = row.id
    session.commit()
    return name_to_id


def run_seed() -> None:
    if not SEED_PATH.exists():
        logger.error("Seed file not found at %s — run `python -m app.data.generate_seed_firs` first.", SEED_PATH)
        sys.exit(1)

    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    stations = payload["stations"]
    firs = payload["firs"]

    init_db()

    with Session(engine) as session:
        name_to_id = _ensure_stations(session, stations)

        bob_count = 0
        fallback_count = 0
        failed = 0
        for i, item in enumerate(firs, start=1):
            station_id = name_to_id.get(item["station_hint"])
            try:
                result = intelligence.ingest_fir(session, item["raw_text"], station_id)
                if result.extraction_source == "bob":
                    bob_count += 1
                else:
                    fallback_count += 1
            except Exception:  # noqa: BLE001
                session.rollback()
                failed += 1
                logger.exception("Failed to ingest FIR #%d", i)

        logger.info(
            "Ingestion complete: %d via Bob, %d via fallback parser, %d failed (of %d total).",
            bob_count, fallback_count, failed, len(firs),
        )

        detect_result = intelligence.run_syndicate_detection(session)
        logger.info(
            "Detection complete: %d clusters, %d flagged as syndicates, %d inter-district MO edges.",
            detect_result.clusters_created, detect_result.syndicates_flagged, detect_result.inter_district_mo_edges,
        )


def run_detect_only() -> None:
    init_db()
    with Session(engine) as session:
        result = intelligence.run_syndicate_detection(session)
        logger.info(
            "Detection complete: %d clusters, %d flagged as syndicates, %d inter-district MO edges.",
            result.clusters_created, result.syndicates_flagged, result.inter_district_mo_edges,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Bob Engine's database with sample FIRs.")
    parser.add_argument("--detect-only", action="store_true", help="Skip ingestion, only (re)run detection.")
    args = parser.parse_args()

    if args.detect_only:
        run_detect_only()
    else:
        run_seed()


if __name__ == "__main__":
    main()
