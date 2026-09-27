"""SQLModel table definitions for Bob Engine.

Design notes:
  - `ipc_sections`, `aliases`, `phone_numbers`, `vehicle_numbers`, `linked_fir_ids`,
    `linked_suspect_ids`, `districts_involved`, `match_reasons` are all JSON list
    columns — fine for a hackathon prototype on Postgres (JSONB under the hood).
  - `SuspectEntity.name` is nullable: some FIRs name no accused, only a description
    and identifiers. Those suspects must still be linkable (see engine/entity_resolution.py).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class PoliceStation(SQLModel, table=True):
    __tablename__ = "police_stations"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    district: str = Field(index=True)
    zone: str
    state: str = Field(default="Uttar Pradesh")


class FIRRecord(SQLModel, table=True):
    __tablename__ = "fir_records"

    id: int | None = Field(default=None, primary_key=True)
    station_id: int = Field(foreign_key="police_stations.id", index=True)
    fir_number: str = Field(index=True)
    timestamp: datetime
    crime_category: str = Field(index=True)
    ipc_sections: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    modus_operandi: str = Field(default="")
    raw_narrative: str = Field(default="")
    raw_text: str = Field(default="")  # the original "digital FIR copy" text as ingested
    extraction_source: str = Field(default="fallback_parser")  # "bob" | "fallback_parser"


class SuspectEntity(SQLModel, table=True):
    __tablename__ = "suspect_entities"

    id: int | None = Field(default=None, primary_key=True)
    fir_id: int = Field(foreign_key="fir_records.id", index=True)
    name: str | None = Field(default=None, index=True)
    aliases: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    phone_numbers: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    vehicle_numbers: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    physical_description: str | None = Field(default=None)
    # set after entity resolution runs; null until then
    cluster_canonical_id: str | None = Field(default=None, index=True)


class RepeatOffenderCluster(SQLModel, table=True):
    __tablename__ = "repeat_offender_clusters"

    canonical_id: str = Field(primary_key=True)
    primary_name: str
    linked_fir_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    linked_suspect_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    districts_involved: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    confidence_score: float = Field(default=0.0)
    match_reasons: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    syndicate_flag: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
