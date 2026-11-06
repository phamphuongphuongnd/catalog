"""Shared helpers for the Subnest catalog: load/save, build outputs (min + meta), small utilities.

Standard library only (runs on a bare GitHub Actions runner).
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "subnest" / "v1"
SERVICES = DATA_DIR / "services.json"
SERVICES_MIN = DATA_DIR / "services.min.json"
META = DATA_DIR / "meta.json"
REPORTS = ROOT / "reports"

SCHEMA_VERSION = 4
STALE_AFTER_DAYS = 90
REGIONS = {"VN": "VND", "US": "USD", "UK": "GBP", "AU": "AUD", "CA": "CAD", "IN": "INR"}
METHODS = ("aristocles", "vn-parser", "manual")
PLAN_STATUSES = ("active", "closed_to_new", "discontinued")
PAGES_BASE = "https://phamphuongphuongnd.github.io/catalog"


def today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def load(path: Path = SERVICES) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_pretty(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def strip_for_min(data: dict) -> dict:
    """App-facing copy: drop maintainer-only fields (`note`)."""
    out = copy.deepcopy(data)
    for s in out.get("services", []):
        s.pop("note", None)
    return out


def dump_min(data: dict) -> str:
    return json.dumps(strip_for_min(data), ensure_ascii=False, separators=(",", ":"))


def counts(data: dict) -> dict:
    services = data.get("services", [])
    plans = [p for s in services for p in s.get("plans", [])]
    prices = [pr for p in plans for pr in p.get("prices", {}).values()]
    return {"services": len(services), "plans": len(plans), "prices": len(prices)}


def is_stale(price: dict, on: str | None = None) -> bool:
    """`approx` in v3 terms: no verifiedAt, or verifiedAt older than STALE_AFTER_DAYS."""
    v = price.get("verifiedAt")
    if not v:
        return True
    ref = dt.date.fromisoformat(on or today())
    return (ref - dt.date.fromisoformat(v)).days > STALE_AFTER_DAYS


def write_outputs(data: dict) -> dict:
    """Write services.json (pretty, with notes), services.min.json (app) and meta.json. Returns meta."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pretty = dump_pretty(data).encode("utf-8")
    mini = dump_min(data).encode("utf-8")
    SERVICES.write_bytes(pretty)
    SERVICES_MIN.write_bytes(mini)
    meta = {
        "schemaVersion": data["schemaVersion"],
        "version": data["version"],
        "updatedAt": data["updatedAt"],
        **counts(data),
        "files": {
            "services.min.json": {"sha256": hashlib.sha256(mini).hexdigest(), "bytes": len(mini),
                                  "url": f"{PAGES_BASE}/subnest/v1/services.min.json"},
            "services.json": {"sha256": hashlib.sha256(pretty).hexdigest(), "bytes": len(pretty),
                              "url": f"{PAGES_BASE}/subnest/v1/services.json"},
        },
    }
    META.write_bytes(dump_pretty(meta).encode("utf-8"))
    return meta


def content_key(data: dict) -> str:
    """Hash of the data ignoring version/updatedAt — tells whether a new version is needed."""
    d = copy.deepcopy(data)
    d.pop("version", None)
    d.pop("updatedAt", None)
    return hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def find_plan(data: dict, service_id: str, plan_id: str) -> dict | None:
    for s in data.get("services", []):
        if s.get("id") == service_id:
            for p in s.get("plans", []):
                if p.get("id") == plan_id:
                    return p
    return None
