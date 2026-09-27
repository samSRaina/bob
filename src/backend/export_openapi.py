"""Dumps the live FastAPI app's OpenAPI schema to src/openapi.json — the shared
contract the frontend's typed client is generated from.

Usage: python export_openapi.py   (run from src/backend, with the venv active)
"""
from __future__ import annotations

import json
from pathlib import Path

from app.main import app

OUT_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUT_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote OpenAPI schema to {OUT_PATH}")


if __name__ == "__main__":
    main()
