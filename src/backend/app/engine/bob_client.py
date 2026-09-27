"""IBM Bob inference client — the ONE place Bob is called from.

Scope, by design (per project decision): Bob is used exclusively as the
extraction "copilot" for turning a raw digital FIR copy into structured JSON.
It never talks to the user, never sees another user's data, and never drives
any decision outside of extraction — entity resolution, MO clustering, the
graph, RBAC and stats are all deterministic (see engine/entity_resolution.py,
engine/mo_similarity.py, engine/graph_builder.py).

Bob exposes an OpenAI-compatible inference surface:
  GET  {BOB_API_BASE_URL}/inference/v1/model/info      -> discover available models
  POST {BOB_API_BASE_URL}/inference/v1/chat/completions -> chat completion

This client is defensive on purpose: if the key, base URL, model discovery, or
network is wrong in ways we cannot fully verify offline, extraction must fall
back to the deterministic parser rather than take the whole ingestion pipeline
down. Every failure is logged with enough detail to diagnose and fix.
"""
from __future__ import annotations

import json
import logging

import httpx

from app.core.config import get_settings
from app.schemas.fir_schema import ExtractedFIR

logger = logging.getLogger("bob_engine.bob_client")

_SYSTEM_PROMPT = """You are a forensic FIR (First Information Report) information extraction \
engine for Indian police records. You are given the raw text of one digitized FIR document. \
Extract ONLY what is explicitly present in the text — never invent names, numbers, or facts.

Return STRICT JSON matching exactly this shape, and nothing else (no markdown fences, no prose):

{
  "fir_number": string or null,
  "station_name": string or null,
  "district": string or null,
  "timestamp": string or null,
  "crime_category": string or null,
  "ipc_sections": [string, ...],
  "modus_operandi": string,
  "suspects": [
    {
      "name": string or null,
      "aliases": [string, ...],
      "phone_numbers": [string, ...],
      "vehicle_numbers": [string, ...],
      "physical_description": string or null
    }
  ]
}

If no accused is named, still extract any suspect identifiers (phone numbers, vehicle numbers, \
physical description) as a single suspect entry with name set to null. If a field is not present \
in the text, use null (or an empty list for list fields). Do not summarize or paraphrase the \
modus_operandi beyond lightly cleaning it up from the source text."""


class BobExtractionError(Exception):
    """Raised on any failure of the Bob inference call — caller falls back to the regex parser."""


class BobClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._cached_model: str | None = self._settings.bob_model or None
        self._model_discovery_failed = False

    @property
    def enabled(self) -> bool:
        return self._settings.bob_configured

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._settings.bob_api_key}",
            "Content-Type": "application/json",
        }

    def _discover_model(self, client: httpx.Client) -> str:
        if self._cached_model:
            return self._cached_model
        url = f"{self._settings.bob_api_base_url}/inference/v1/model/info"
        resp = client.get(url, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data") or data.get("models") or []
        if not models:
            raise BobExtractionError(f"Bob model discovery returned no models: {data!r}")
        first = models[0]
        model_id = first.get("id") or first.get("model") or first.get("name")
        if not model_id:
            raise BobExtractionError(f"Could not read model id from discovery response: {first!r}")
        self._cached_model = model_id
        logger.info("bob_client: discovered model '%s'", model_id)
        return model_id

    def extract(self, raw_text: str) -> ExtractedFIR:
        """Call Bob to extract structured fields from a raw FIR text. Raises BobExtractionError
        on any failure — caller is expected to fall back to engine.parser.parse_fir_text()."""
        if not self.enabled:
            raise BobExtractionError("Bob extraction is disabled or no API key is configured.")

        timeout = self._settings.bob_request_timeout_seconds
        try:
            with httpx.Client(timeout=timeout) as client:
                model = self._discover_model(client)
                url = f"{self._settings.bob_api_base_url}/inference/v1/chat/completions"
                payload = {
                    "model": model,
                    "temperature": 0,
                    "max_tokens": 1200,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": raw_text},
                    ],
                }
                resp = client.post(url, headers=self._headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise BobExtractionError(
                f"Bob inference HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise BobExtractionError(f"Bob inference network error: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BobExtractionError(f"Unexpected Bob response shape: {data!r}") from exc

        parsed_json = _extract_json_object(content)
        try:
            return ExtractedFIR.model_validate(parsed_json)
        except Exception as exc:  # noqa: BLE001 - any validation failure -> fallback
            raise BobExtractionError(f"Bob returned JSON that failed schema validation: {exc}") from exc


def _extract_json_object(content: str) -> dict:
    """Bob is asked for raw JSON, but be tolerant of ```json fences some models add anyway."""
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise BobExtractionError(f"No JSON object found in Bob response: {content[:300]!r}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise BobExtractionError(f"Bob response was not valid JSON: {exc}") from exc


_client_singleton: BobClient | None = None


def get_bob_client() -> BobClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = BobClient()
    return _client_singleton
