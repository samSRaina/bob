"""Role-based access control: roles, scope resolution, and the FastAPI dependency.

Three tiers, matching UP Police's real chain of command:
  STATION_OFFICER (PI, one police station) -> DISTRICT_SP (all stations in a district)
  -> STATE_DGP (global visibility).

Scoping is resolved here ONCE per request and then applied identically by every
read in `services/intelligence.py` — stats, offender list, graph, dossier alike.
This is deliberate: RBAC lives in the query layer, never in a prompt, and never
only in the UI.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.fir_models import PoliceStation


class Role(str, Enum):
    STATION_OFFICER = "STATION_OFFICER"
    DISTRICT_SP = "DISTRICT_SP"
    STATE_DGP = "STATE_DGP"


@dataclass(frozen=True)
class Scope:
    """The resolved visibility window for the current request."""

    role: Role
    station_id: int | None          # the officer's own station (STATION_OFFICER only)
    district: str | None            # the officer's own district (STATION_OFFICER / DISTRICT_SP)
    station_ids: list[int] | None   # concrete allow-list of station ids, or None = all (STATE_DGP)

    def station_allowed(self, station_id: int) -> bool:
        if self.station_ids is None:
            return True
        return station_id in self.station_ids


def get_scope(
    x_user_role: str = Header(..., alias="X-User-Role"),
    x_user_station: int | None = Header(None, alias="X-User-Station"),
    session: Session = Depends(get_session),
) -> Scope:
    """FastAPI dependency: parse RBAC headers, validate against the DB, return a Scope.

    Every REST route that reads FIR data depends on this — never on the headers
    directly — so scoping can never be bypassed by a route that "forgets" to filter.
    """
    try:
        role = Role(x_user_role)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-User-Role '{x_user_role}'. Must be one of {[r.value for r in Role]}.",
        ) from exc

    if role == Role.STATE_DGP:
        return Scope(role=role, station_id=None, district=None, station_ids=None)

    if x_user_station is None:
        raise HTTPException(
            status_code=400,
            detail="X-User-Station header is required for STATION_OFFICER and DISTRICT_SP roles.",
        )

    station = session.get(PoliceStation, x_user_station)
    if station is None:
        raise HTTPException(status_code=404, detail=f"Unknown station_id {x_user_station} in X-User-Station.")

    if role == Role.STATION_OFFICER:
        return Scope(role=role, station_id=station.id, district=station.district, station_ids=[station.id])

    # DISTRICT_SP: every station in the same district
    district_station_ids = session.exec(
        select(PoliceStation.id).where(PoliceStation.district == station.district)
    ).all()
    return Scope(
        role=role,
        station_id=station.id,
        district=station.district,
        station_ids=list(district_station_ids),
    )
