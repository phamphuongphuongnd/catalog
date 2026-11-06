"""Validate a Subnest catalog v4 file (standard library only).

    python tools/validate.py [services.json] [--published OLD.json] [--json]

Errors (exit 1): broken structure, duplicate ids, bad enums/URLs/dates, currency not matching its region,
a service or plan that exists in the published file but is missing now (never delete — change `status`).
Warnings (exit 0, still publishable under the "always auto-publish" rule): price moved > 50 %, a region price
removed, plan status changed, stale/unverified prices (summary).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HOST = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
CURRENCY = re.compile(r"^[A-Z]{3}$")
CATEGORIES = {"video", "music", "ai", "storage", "software", "gaming", "reading", "health", "education",
              "telecom", "other"}
MARKETS = {"global", "vn"}
CYCLE_UNITS = {"day", "week", "month", "year"}
ZERO_DECIMAL = {"VND", "JPY", "KRW", "IDR"}
ROOT_REQ = {"schemaVersion", "version", "updatedAt", "staleAfterDays", "regions", "services"}
SERVICE_REQ = {"id", "name", "category", "color", "monogram", "market", "logoDomain", "aliases", "cancelUrl",
               "manageUrl", "plans"}
SERVICE_OPT = {"note", "storeNames"}
PLAN_REQ = {"id", "name", "status", "cycle", "prices"}
PLAN_OPT = {"members", "renamedFrom"}
PRICE_REQ = {"currency", "amount", "method"}
PRICE_OPT = {"verifiedAt", "source"}
BIG_CHANGE = 0.5


def is_https(u) -> bool:
    if not isinstance(u, str):
        return False
    p = urlparse(u)
    return p.scheme == "https" and bool(p.netloc) and " " not in u


def is_date(s) -> bool:
    if not isinstance(s, str) or not DATE.match(s):
        return False
    try:
        dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate(data, published=None, on: str | None = None):
    """Return (errors, warnings, stats)."""
    errors: list[str] = []
    warns: list[str] = []
    on = on or common.today()
    if not isinstance(data, dict):
        return ["root must be an object"], warns, {}

    def keys(obj, req, opt, where):
        for k in sorted(req - obj.keys()):
            errors.append(f"{where}: missing '{k}'")
        for k in sorted(obj.keys() - req - opt):
            errors.append(f"{where}: unknown field '{k}'")

    keys(data, ROOT_REQ, set(), "root")
    if data.get("schemaVersion") != common.SCHEMA_VERSION:
        errors.append(f"root.schemaVersion must be {common.SCHEMA_VERSION}")
    if not (isinstance(data.get("version"), int) and not isinstance(data.get("version"), bool)
            and data.get("version", 0) >= 1):
        errors.append("root.version must be an int >= 1")
    if not is_date(data.get("updatedAt")):
        errors.append("root.updatedAt must be YYYY-MM-DD")
    elif data["updatedAt"] > on:
        errors.append("root.updatedAt is in the future")
    if data.get("staleAfterDays") != common.STALE_AFTER_DAYS:
        errors.append(f"root.staleAfterDays must be {common.STALE_AFTER_DAYS}")
    regions = data.get("regions")
    if regions != common.REGIONS:
        errors.append(f"root.regions must be {common.REGIONS}")
        regions = common.REGIONS
    services = data.get("services")
    if not isinstance(services, list) or not services:
        errors.append("root.services must be a non-empty array")
        services = []

    seen_ids: set[str] = set()
    seen_tiles: dict[tuple, str] = {}
    n_prices = n_stale = 0
    for i, s in enumerate(services):
        w = f"services[{i}]"
        if not isinstance(s, dict):
            errors.append(f"{w}: must be an object")
            continue
        sid = s.get("id")
        w = f"service '{sid}'" if isinstance(sid, str) else w
        keys(s, SERVICE_REQ, SERVICE_OPT, w)
        if not (isinstance(sid, str) and SLUG.match(sid)):
            errors.append(f"{w}: id must be a slug")
        elif sid in seen_ids:
            errors.append(f"{w}: duplicate id")
        else:
            seen_ids.add(sid)
        if not (isinstance(s.get("name"), str) and s["name"].strip()):
            errors.append(f"{w}: name must be a non-empty string")
        if s.get("category") not in CATEGORIES:
            errors.append(f"{w}: category must be one of {sorted(CATEGORIES)}")
        if s.get("market") not in MARKETS:
            errors.append(f"{w}: market must be global|vn")
        if not (isinstance(s.get("color"), str) and HEX.match(s["color"])):
            errors.append(f"{w}: color must be #RRGGBB")
        mono = s.get("monogram")
        if not (isinstance(mono, str) and 1 <= len(mono) <= 2):
            errors.append(f"{w}: monogram must be 1-2 characters")
        tile = (str(s.get("color", "")).upper(), mono)
        if tile in seen_tiles:
            errors.append(f"{w}: (color, monogram) already used by '{seen_tiles[tile]}'")
        seen_tiles[tile] = sid
        if not (isinstance(s.get("logoDomain"), str) and HOST.match(s["logoDomain"])):
            errors.append(f"{w}: logoDomain must be a lowercase host name like 'netflix.com'")
        al = s.get("aliases")
        if not (isinstance(al, list) and all(isinstance(a, str) and a == a.lower() and a.strip() for a in al)):
            errors.append(f"{w}: aliases must be an array of lowercase strings")
        for k in ("cancelUrl", "manageUrl"):
            if k in s and s[k] is not None and not is_https(s[k]):
                errors.append(f"{w}: {k} must be an https URL or null")
        sn = s.get("storeNames")
        if "storeNames" in s and not (isinstance(sn, list) and sn and len(set(sn)) == len(sn)
                                      and all(isinstance(x, str) and x.strip() == x and x for x in sn)):
            errors.append(f"{w}: storeNames must be a non-empty array of unique, trimmed strings")
        if "note" in s and not isinstance(s["note"], str):
            errors.append(f"{w}: note must be a string")
        plans = s.get("plans")
        if not isinstance(plans, list) or not plans:
            errors.append(f"{w}: plans must be a non-empty array")
            continue
        plan_ids: set[str] = set()
        for j, p in enumerate(plans):
            pw = f"{w} plans[{j}]"
            if not isinstance(p, dict):
                errors.append(f"{pw}: must be an object")
                continue
            pid = p.get("id")
            pw = f"{w} plan '{pid}'" if isinstance(pid, str) else pw
            keys(p, PLAN_REQ, PLAN_OPT, pw)
            if not (isinstance(pid, str) and SLUG.match(pid)):
                errors.append(f"{pw}: id must be a slug")
            elif pid in plan_ids:
                errors.append(f"{pw}: duplicate plan id")
            else:
                plan_ids.add(pid)
            if not (isinstance(p.get("name"), str) and p["name"].strip()):
                errors.append(f"{pw}: name must be a non-empty string")
            if p.get("status") not in common.PLAN_STATUSES:
                errors.append(f"{pw}: status must be one of {common.PLAN_STATUSES}")
            if "renamedFrom" in p and not (isinstance(p["renamedFrom"], str) and p["renamedFrom"].strip()):
                errors.append(f"{pw}: renamedFrom must be a non-empty string")
            if "members" in p and not (isinstance(p["members"], int) and not isinstance(p["members"], bool)
                                       and p["members"] >= 2):
                errors.append(f"{pw}: members must be an int >= 2")
            cyc = p.get("cycle")
            if not (isinstance(cyc, dict) and set(cyc) == {"unit", "count"} and cyc.get("unit") in CYCLE_UNITS
                    and isinstance(cyc.get("count"), int) and not isinstance(cyc.get("count"), bool)
                    and cyc["count"] >= 1):
                errors.append(f"{pw}: cycle must be {{unit: day|week|month|year, count: int >= 1}}")
            prices = p.get("prices")
            if not isinstance(prices, dict):
                errors.append(f"{pw}: prices must be an object")
                continue
            if not prices and p.get("status") == "active":
                errors.append(f"{pw}: an active plan needs at least one price")
            for region, pr in prices.items():
                rw = f"{pw} {region}"
                if region not in regions:
                    errors.append(f"{rw}: unknown region (allowed {sorted(regions)})")
                    continue
                if not isinstance(pr, dict):
                    errors.append(f"{rw}: price must be an object")
                    continue
                n_prices += 1
                keys(pr, PRICE_REQ, PRICE_OPT, rw)
                cur = pr.get("currency")
                if not (isinstance(cur, str) and CURRENCY.match(cur)):
                    errors.append(f"{rw}: currency must be ISO 4217")
                elif cur != regions[region]:
                    errors.append(f"{rw}: currency {cur} does not match region currency {regions[region]}")
                amt = pr.get("amount")
                if not (is_num(amt) and amt > 0):
                    errors.append(f"{rw}: amount must be a number > 0")
                elif cur in ZERO_DECIMAL and amt != int(amt):
                    errors.append(f"{rw}: {cur} amount must be a whole number")
                elif round(amt, 2) != amt:
                    errors.append(f"{rw}: amount has more than 2 decimals")
                if pr.get("method") not in common.METHODS:
                    errors.append(f"{rw}: method must be one of {common.METHODS}")
                has_v, has_s = "verifiedAt" in pr, "source" in pr
                if has_v != has_s:
                    errors.append(f"{rw}: verifiedAt and source go together")
                if has_v:
                    if not is_date(pr["verifiedAt"]):
                        errors.append(f"{rw}: verifiedAt must be YYYY-MM-DD")
                    elif pr["verifiedAt"] > on:
                        errors.append(f"{rw}: verifiedAt is in the future")
                if has_s and not is_https(pr["source"]):
                    errors.append(f"{rw}: source must be an https URL")
                if not has_v or (is_date(pr.get("verifiedAt")) and common.is_stale(pr, on)):
                    n_stale += 1

    if published:
        compare(data, published, errors, warns)
    stats = {**common.counts(data), "unverified_or_stale": n_stale}
    if n_prices:
        warns.append(f"{n_stale}/{n_prices} prices unverified or older than {common.STALE_AFTER_DAYS} days "
                     "(apps show them as approximate)")
    return errors, warns, stats


def compare(new: dict, old: dict, errors: list, warns: list) -> None:
    def index(d):
        out = {}
        for s in d.get("services", []) if isinstance(d, dict) else []:
            if isinstance(s, dict) and isinstance(s.get("id"), str):
                out[s["id"]] = {p.get("id"): p for p in s.get("plans", []) if isinstance(p, dict)}
        return out

    ni, oi = index(new), index(old)
    for sid, oplans in oi.items():
        if sid not in ni:
            errors.append(f"service '{sid}' was published before and must not be removed (set plan status instead)")
            continue
        for pid, op in oplans.items():
            np_ = ni[sid].get(pid)
            if np_ is None:
                errors.append(f"plan '{sid}/{pid}' was published before and must not be removed (use status)")
                continue
            if op.get("status") != np_.get("status"):
                warns.append(f"plan '{sid}/{pid}' status {op.get('status')} -> {np_.get('status')}")
            for region, opr in (op.get("prices") or {}).items():
                npr = (np_.get("prices") or {}).get(region)
                if npr is None:
                    warns.append(f"price '{sid}/{pid}/{region}' removed")
                    continue
                a, b = opr.get("amount"), npr.get("amount")
                if is_num(a) and is_num(b) and a > 0 and abs(b - a) / a > BIG_CHANGE:
                    warns.append(f"price '{sid}/{pid}/{region}' changed {a} -> {b} "
                                 f"({(b - a) / a:+.0%}) — check the source")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in args
    if as_json:
        args.remove("--json")
    published = None
    if "--published" in args:
        i = args.index("--published")
        published = common.load(Path(args[i + 1]))
        del args[i:i + 2]
    path = Path(args[0]) if args else common.SERVICES
    try:
        data = common.load(path)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read {path}: {e}")
        return 1
    errors, warns, stats = validate(data, published)
    if as_json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warns, "stats": stats},
                         ensure_ascii=False, indent=2))
    else:
        for e in errors:
            print(f"ERROR: {e}")
        for w in warns:
            print(f"WARN:  {w}")
        print(f"{'OK' if not errors else 'FAILED'} — {stats.get('services', 0)} services, "
              f"{stats.get('plans', 0)} plans, {stats.get('prices', 0)} prices, {len(errors)} errors, "
              f"{len(warns)} warnings")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
