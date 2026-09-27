"""Shared service layer — the ONE place both REST routes and (optionally) any future
Bob-driven automation call into. RBAC scoping is applied here, consistently, for
every read: dashboard stats, the offender list, the graph, and suspect dossiers.

Bob is called from here (via engine.bob_client) for extraction ONLY, with an
automatic, logged fallback to the deterministic parser. Nothing downstream of
extraction (entity resolution, MO clustering, graph, RBAC) ever calls an LLM.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.rbac import Scope
from app.engine import graph_builder
from app.engine.bob_client import BobExtractionError, get_bob_client
from app.engine.entity_resolution import SuspectRecord, resolve_entities
from app.engine.mo_similarity import compute_inter_district_mo_edges
from app.engine.parser import parse_fir_text
from app.models.fir_models import FIRRecord, PoliceStation, RepeatOffenderCluster, SuspectEntity
from app.schemas.fir_schema import (
    CrimeCategoryCount,
    DashboardSummaryOut,
    DetectResponse,
    ExtractedFIR,
    GraphOut,
    IngestResultItem,
    OffenderClusterOut,
    StationCount,
    SuspectDossierOut,
)

logger = logging.getLogger("bob_engine.services")


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
def _resolve_station(session: Session, station_id_hint: int | None, extracted: ExtractedFIR) -> PoliceStation:
    if station_id_hint is not None:
        station = session.get(PoliceStation, station_id_hint)
        if station:
            return station

    if extracted.station_name:
        candidate = session.exec(
            select(PoliceStation).where(PoliceStation.name.ilike(f"%{extracted.station_name.strip()}%"))
        ).first()
        if candidate:
            return candidate

    if extracted.district:
        candidate = session.exec(
            select(PoliceStation).where(PoliceStation.district.ilike(f"%{extracted.district.strip()}%"))
        ).first()
        if candidate:
            return candidate

    raise HTTPException(
        status_code=422,
        detail=(
            "Could not resolve a police station for this FIR — pass station_id explicitly, "
            "or ensure the document names a station/district that exists in the database."
        ),
    )


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def extract_fir(raw_text: str) -> tuple[ExtractedFIR, str]:
    """Try Bob first (the copilot), fall back to the deterministic parser. Returns
    (extracted, source) where source is 'bob' or 'fallback_parser'."""
    client = get_bob_client()
    if client.enabled:
        try:
            return client.extract(raw_text), "bob"
        except BobExtractionError as exc:
            logger.warning("Bob extraction failed, falling back to deterministic parser: %s", exc)
    return parse_fir_text(raw_text), "fallback_parser"


def ingest_fir(session: Session, raw_text: str, station_id_hint: int | None) -> IngestResultItem:
    extracted, source = extract_fir(raw_text)
    station = _resolve_station(session, station_id_hint, extracted)

    fir = FIRRecord(
        station_id=station.id,  # type: ignore[arg-type]
        fir_number=extracted.fir_number or f"AUTO-{int(datetime.utcnow().timestamp() * 1000)}",
        timestamp=_parse_timestamp(extracted.timestamp),
        crime_category=extracted.crime_category or "Other / Unclassified",
        ipc_sections=extracted.ipc_sections,
        modus_operandi=extracted.modus_operandi,
        raw_narrative=extracted.modus_operandi,
        raw_text=raw_text,
        extraction_source=source,
    )
    session.add(fir)
    session.flush()  # populate fir.id without committing

    for s in extracted.suspects:
        suspect = SuspectEntity(
            fir_id=fir.id,  # type: ignore[arg-type]
            name=s.name,
            aliases=s.aliases,
            phone_numbers=s.phone_numbers,
            vehicle_numbers=s.vehicle_numbers,
            physical_description=s.physical_description,
        )
        session.add(suspect)

    session.commit()
    session.refresh(fir)

    return IngestResultItem(
        fir_id=fir.id,  # type: ignore[arg-type]
        fir_number=fir.fir_number,
        station_id=station.id,  # type: ignore[arg-type]
        crime_category=fir.crime_category,
        extraction_source=source,
        suspects_extracted=len(extracted.suspects),
    )


# ---------------------------------------------------------------------------
# Detection (entity resolution + MO clustering)
# ---------------------------------------------------------------------------
def run_syndicate_detection(session: Session) -> DetectResponse:
    stations_by_id = {s.id: s for s in session.exec(select(PoliceStation)).all()}
    all_firs = session.exec(select(FIRRecord)).all()
    all_suspects = session.exec(select(SuspectEntity)).all()

    fir_by_id = {f.id: f for f in all_firs}
    suspect_records: list[SuspectRecord] = []
    fir_to_suspect_ids: dict[int, list[int]] = defaultdict(list)

    for s in all_suspects:
        fir = fir_by_id.get(s.fir_id)
        if not fir:
            continue
        station = stations_by_id.get(fir.station_id)
        district = station.district if station else "Unknown"
        suspect_records.append(
            SuspectRecord(
                suspect_id=s.id,  # type: ignore[arg-type]
                fir_id=s.fir_id,
                station_district=district,
                name=s.name,
                aliases=s.aliases,
                phone_numbers=s.phone_numbers,
                vehicle_numbers=s.vehicle_numbers,
            )
        )
        fir_to_suspect_ids[s.fir_id].append(s.id)  # type: ignore[arg-type]

    fir_mo_tuples = [
        (f.id, (stations_by_id.get(f.station_id).district if stations_by_id.get(f.station_id) else "Unknown"), f.modus_operandi)
        for f in all_firs
    ]
    mo_edges = compute_inter_district_mo_edges(fir_mo_tuples, fir_to_suspect_ids)  # type: ignore[arg-type]

    clusters = resolve_entities(suspect_records, mo_edges=mo_edges)

    # Idempotent re-run: wipe and rewrite clusters + suspect cluster assignments.
    for existing in session.exec(select(RepeatOffenderCluster)).all():
        session.delete(existing)
    for s in all_suspects:
        s.cluster_canonical_id = None
        session.add(s)
    session.flush()

    suspects_by_id = {s.id: s for s in all_suspects}
    syndicate_count = 0
    for c in clusters:
        if c.syndicate_flag:
            syndicate_count += 1
        row = RepeatOffenderCluster(
            canonical_id=c.canonical_id,
            primary_name=next((suspects_by_id[i].name for i in c.member_suspect_ids if suspects_by_id[i].name), "Unknown"),
            linked_fir_ids=c.member_fir_ids,
            linked_suspect_ids=c.member_suspect_ids,
            districts_involved=c.districts_involved,
            confidence_score=c.confidence_score,
            match_reasons=c.match_reasons,
            syndicate_flag=c.syndicate_flag,
            updated_at=datetime.utcnow(),
        )
        session.add(row)
        for sid in c.member_suspect_ids:
            suspects_by_id[sid].cluster_canonical_id = c.canonical_id
            session.add(suspects_by_id[sid])

    session.commit()

    return DetectResponse(
        clusters_created=len(clusters),
        syndicates_flagged=syndicate_count,
        inter_district_mo_edges=len(mo_edges),
    )


# ---------------------------------------------------------------------------
# RBAC-scoped reads
# ---------------------------------------------------------------------------
def _scoped_fir_ids(session: Session, scope: Scope) -> set[int] | None:
    if scope.station_ids is None:
        return None
    rows = session.exec(select(FIRRecord.id).where(FIRRecord.station_id.in_(scope.station_ids))).all()
    return set(rows)


def dashboard_summary(session: Session, scope: Scope) -> DashboardSummaryOut:
    fir_ids = _scoped_fir_ids(session, scope)
    firs = session.exec(select(FIRRecord)).all()
    if fir_ids is not None:
        firs = [f for f in firs if f.id in fir_ids]

    stations = {s.id: s for s in session.exec(select(PoliceStation)).all()}

    by_category: dict[str, int] = defaultdict(int)
    by_station: dict[int, int] = defaultdict(int)
    for f in firs:
        by_category[f.crime_category] += 1
        by_station[f.station_id] += 1

    suspects = session.exec(select(SuspectEntity)).all()
    scoped_suspect_count = len([s for s in suspects if fir_ids is None or s.fir_id in fir_ids])

    clusters = session.exec(select(RepeatOffenderCluster)).all()
    scoped_clusters = [
        c for c in clusters if fir_ids is None or any(fid in fir_ids for fid in c.linked_fir_ids)
    ]

    return DashboardSummaryOut(
        total_firs=len(firs),
        total_suspects=scoped_suspect_count,
        total_clusters=len(scoped_clusters),
        total_syndicates=len([c for c in scoped_clusters if c.syndicate_flag]),
        by_crime_category=[CrimeCategoryCount(crime_category=k, count=v) for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])],
        by_station=[
            StationCount(station_id=k, station_name=stations[k].name if k in stations else "Unknown", count=v)
            for k, v in sorted(by_station.items(), key=lambda kv: -kv[1])
        ],
    )


def list_offenders(session: Session, scope: Scope) -> list[OffenderClusterOut]:
    fir_ids = _scoped_fir_ids(session, scope)
    clusters = session.exec(select(RepeatOffenderCluster)).all()
    visible = [c for c in clusters if fir_ids is None or any(fid in fir_ids for fid in c.linked_fir_ids)]
    visible.sort(key=lambda c: (-c.syndicate_flag, -c.confidence_score))
    return [
        OffenderClusterOut(
            canonical_id=c.canonical_id,
            primary_name=c.primary_name,
            linked_fir_ids=c.linked_fir_ids,
            districts_involved=c.districts_involved,
            confidence_score=c.confidence_score,
            match_reasons=c.match_reasons,
            syndicate_flag=c.syndicate_flag,
        )
        for c in visible
    ]


def offender_graph(session: Session, scope: Scope) -> GraphOut:
    fir_ids = _scoped_fir_ids(session, scope)

    stations = session.exec(select(PoliceStation)).all()
    firs = session.exec(select(FIRRecord)).all()
    if fir_ids is not None:
        firs = [f for f in firs if f.id in fir_ids]
    visible_fir_ids = {f.id for f in firs}
    visible_station_ids = {f.station_id for f in firs}

    suspects = session.exec(select(SuspectEntity)).all()
    suspects = [s for s in suspects if s.fir_id in visible_fir_ids]

    clusters = session.exec(select(RepeatOffenderCluster)).all()

    return graph_builder.build_graph(
        stations=[(s.id, s.name) for s in stations if s.id in visible_station_ids],  # type: ignore[misc]
        firs=[(f.id, f.fir_number, f.station_id) for f in firs],  # type: ignore[misc]
        suspects=[(s.id, s.name, s.fir_id, s.cluster_canonical_id) for s in suspects],  # type: ignore[misc]
        clusters=[(c.canonical_id, c.syndicate_flag) for c in clusters],
    )


def suspect_dossier(session: Session, scope: Scope, suspect_id: int) -> SuspectDossierOut:
    suspect = session.get(SuspectEntity, suspect_id)
    if suspect is None:
        raise HTTPException(status_code=404, detail="Suspect not found.")

    fir = session.get(FIRRecord, suspect.fir_id)
    if fir is None or (scope.station_ids is not None and fir.station_id not in scope.station_ids):
        raise HTTPException(status_code=404, detail="Suspect not found in your jurisdiction.")

    cluster_out: OffenderClusterOut | None = None
    associated_fir_ids = [suspect.fir_id]
    if suspect.cluster_canonical_id:
        cluster = session.get(RepeatOffenderCluster, suspect.cluster_canonical_id)
        if cluster:
            associated_fir_ids = cluster.linked_fir_ids
            cluster_out = OffenderClusterOut(
                canonical_id=cluster.canonical_id,
                primary_name=cluster.primary_name,
                linked_fir_ids=cluster.linked_fir_ids,
                districts_involved=cluster.districts_involved,
                confidence_score=cluster.confidence_score,
                match_reasons=cluster.match_reasons,
                syndicate_flag=cluster.syndicate_flag,
            )

    return SuspectDossierOut(
        suspect_id=suspect.id,  # type: ignore[arg-type]
        name=suspect.name,
        aliases=suspect.aliases,
        phone_numbers=suspect.phone_numbers,
        vehicle_numbers=suspect.vehicle_numbers,
        physical_description=suspect.physical_description,
        associated_fir_ids=associated_fir_ids,
        cluster=cluster_out,
    )


def list_stations(session: Session, scope: Scope) -> list[PoliceStation]:
    stations = session.exec(select(PoliceStation)).all()
    if scope.station_ids is None:
        return stations
    return [s for s in stations if s.id in scope.station_ids]
