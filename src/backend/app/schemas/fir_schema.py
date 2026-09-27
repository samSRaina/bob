"""Pydantic v2 request/response schemas for the REST API and the extraction contract
shared by the Bob inference client and the deterministic fallback parser."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Extraction contract — what BOTH the Bob client and the fallback parser return.
# ---------------------------------------------------------------------------
class ExtractedSuspect(BaseModel):
    name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    vehicle_numbers: list[str] = Field(default_factory=list)
    physical_description: str | None = None


class ExtractedFIR(BaseModel):
    fir_number: str | None = None
    station_name: str | None = None
    district: str | None = None
    timestamp: str | None = None  # ISO string; caller parses/defaults
    crime_category: str | None = None
    ipc_sections: list[str] = Field(default_factory=list)
    modus_operandi: str = ""
    suspects: list[ExtractedSuspect] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
class IngestItem(BaseModel):
    raw_text: str
    station_id: int | None = None  # optional hint; extraction may also resolve station by name


class IngestRequest(BaseModel):
    items: list[IngestItem]


class IngestResultItem(BaseModel):
    fir_id: int
    fir_number: str
    station_id: int
    crime_category: str
    extraction_source: str
    suspects_extracted: int


class IngestResponse(BaseModel):
    ingested: list[IngestResultItem]
    failed: list[dict]


class DetectResponse(BaseModel):
    clusters_created: int
    syndicates_flagged: int
    inter_district_mo_edges: int


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
class StationOut(BaseModel):
    id: int
    name: str
    district: str
    zone: str
    state: str


class CrimeCategoryCount(BaseModel):
    crime_category: str
    count: int


class StationCount(BaseModel):
    station_id: int
    station_name: str
    count: int


class DashboardSummaryOut(BaseModel):
    total_firs: int
    total_suspects: int
    total_clusters: int
    total_syndicates: int
    by_crime_category: list[CrimeCategoryCount]
    by_station: list[StationCount]


class OffenderClusterOut(BaseModel):
    canonical_id: str
    primary_name: str
    linked_fir_ids: list[int]
    districts_involved: list[str]
    confidence_score: float
    match_reasons: list[str]
    syndicate_flag: bool


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "Suspect" | "FIR" | "Station"
    meta: dict = Field(default_factory=dict)


class GraphLink(BaseModel):
    source: str
    target: str
    type: str  # "named_in" | "filed_at" | "syndicate"


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class SuspectDossierOut(BaseModel):
    suspect_id: int
    name: str | None
    aliases: list[str]
    phone_numbers: list[str]
    vehicle_numbers: list[str]
    physical_description: str | None
    associated_fir_ids: list[int]
    cluster: OffenderClusterOut | None
