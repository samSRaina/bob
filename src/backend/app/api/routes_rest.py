"""REST endpoints for the React dashboard. Every read depends on `get_scope`
(app.core.rbac) so RBAC filtering is structurally impossible to skip."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.rbac import Scope, get_scope
from app.models.fir_models import PoliceStation
from app.services import intelligence
from app.schemas.fir_schema import (
    DashboardSummaryOut,
    DetectResponse,
    GraphOut,
    IngestRequest,
    IngestResponse,
    IngestResultItem,
    OffenderClusterOut,
    StationOut,
    SuspectDossierOut,
)

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/stations", response_model=list[StationOut])
def get_stations(session: Session = Depends(get_session), scope: Scope = Depends(get_scope)):
    stations = intelligence.list_stations(session, scope)
    return [StationOut(id=s.id, name=s.name, district=s.district, zone=s.zone, state=s.state) for s in stations]


@router.get("/stations/all", response_model=list[StationOut])
def get_all_stations_for_role_switcher(session: Session = Depends(get_session)):
    """Unscoped station directory — feeds the demo Role Switcher dropdown, which needs
    to list every station a judge could pretend to log in as. Not used for data reads."""
    stations = session.exec(select(PoliceStation)).all()
    return [StationOut(id=s.id, name=s.name, district=s.district, zone=s.zone, state=s.state) for s in stations]


@router.post("/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest, session: Session = Depends(get_session)):
    ingested: list[IngestResultItem] = []
    failed: list[dict] = []
    for item in payload.items:
        try:
            result = intelligence.ingest_fir(session, item.raw_text, item.station_id)
            ingested.append(result)
        except HTTPException as exc:
            session.rollback()
            failed.append({"error": exc.detail, "raw_text_preview": item.raw_text[:120]})
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            failed.append({"error": str(exc), "raw_text_preview": item.raw_text[:120]})
    return IngestResponse(ingested=ingested, failed=failed)


@router.post("/detect", response_model=DetectResponse)
def detect(session: Session = Depends(get_session)):
    return intelligence.run_syndicate_detection(session)


@router.get("/dashboard/summary", response_model=DashboardSummaryOut)
def dashboard_summary(session: Session = Depends(get_session), scope: Scope = Depends(get_scope)):
    return intelligence.dashboard_summary(session, scope)


@router.get("/offenders", response_model=list[OffenderClusterOut])
def offenders(session: Session = Depends(get_session), scope: Scope = Depends(get_scope)):
    return intelligence.list_offenders(session, scope)


@router.get("/graph", response_model=GraphOut)
def graph(session: Session = Depends(get_session), scope: Scope = Depends(get_scope)):
    return intelligence.offender_graph(session, scope)


@router.get("/suspects/{suspect_id}", response_model=SuspectDossierOut)
def suspect_dossier(suspect_id: int, session: Session = Depends(get_session), scope: Scope = Depends(get_scope)):
    return intelligence.suspect_dossier(session, scope, suspect_id)
