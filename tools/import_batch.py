"""Add services / patch fields in subnest/v1/services.json from a compact text batch (standard library only).

    python tools/import_batch.py BATCH.txt [--dry-run]

Batch format (UTF-8, '#' comments, blank lines ignored, fields separated by '|'):

    ## global | ## vn                      section marker -> `market` of following services (default global)
    id|Name|category|logoDomain|color|mono|aliases;..|storeNames;..|cancelUrl|manageUrl
      plan-id|Plan name|cycle|US|VN|members  plan line (indented). cycle = m1, m3, y1, w1, d30...
                                            US/VN = amount or empty; members optional
    @id|storeName;storeName                 add storeNames to an existing service
    !id/plan|amount|YYYY-MM-DD|https://...  set a VERIFIED US price (method manual, verifiedAt, source)

Empty color/mono -> generated (unique tile); empty URLs -> null. New prices without '!' are Reference prices
(no verifiedAt). Existing service ids are never overwritten. Bumps `version` when data changed.
"""
from __future__ import annotations

import colorsys
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

CAT_ALIAS = {"video": "xem phim", "music": "nghe nhac", "ai": "tri tue nhan tao", "storage": "luu tru",
             "software": "phan mem", "gaming": "choi game", "reading": "doc sach", "health": "suc khoe",
             "education": "hoc", "telecom": "nha mang"}
UNITS = {"d": "day", "w": "week", "m": "month", "y": "year"}
REF_NOTE = "C1 2026-11-06: gia US uoc luong tu hieu biet chung (Gia tham khao), chua tra trang hang."


def gen_color(sid: str) -> str:
    h = int(hashlib.md5(sid.encode()).hexdigest()[:6], 16)
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, 0.42, 0.62)
    return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))


def gen_mono(name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", name)
    if not words:
        return name[:2]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    w = words[0]
    return w[0].upper() + (w[1].lower() if len(w) > 1 else "")


def money(x: str, cur: str):
    v = float(x)
    return int(v) if cur == "VND" or v == int(v) else round(v, 2)


def price(amount: str, cur: str) -> dict:
    return {"currency": cur, "amount": money(amount, cur), "method": "manual"}


def main(argv) -> int:
    path, dry = Path(argv[0]), "--dry-run" in argv
    data = common.load()
    before = common.content_key(data)
    by_id = {s["id"]: s for s in data["services"]}
    tiles = {(s["color"].upper(), s["monogram"]) for s in data["services"]}
    market, cur, added, patched, verified, errs = "global", None, 0, 0, 0, []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("# "):
            continue
        if line.startswith("## "):
            market = line[3:].strip()
            continue
        f = [x.strip() for x in line.strip().split("|")]
        try:
            if line.startswith("@"):
                s = by_id[f[0][1:]]
                names = s.setdefault("storeNames", [])
                for x in f[1].split(";"):
                    if x and x not in names:
                        names.append(x)
                patched += 1
            elif line.startswith("!"):
                sid, pid = f[0][1:].split("/")
                p = common.find_plan(data, sid, pid)
                if p is None:
                    raise KeyError(f"{sid}/{pid}")
                p["prices"]["US"] = {"currency": "USD", "amount": money(f[1], "USD"), "verifiedAt": f[2],
                                     "source": f[3], "method": "manual"}
                s = by_id[sid]
                if s.get("note", "").startswith("C1 2026-11-06: gia US uoc"):
                    s["note"] = f"C1 2026-11-06: gia US xac minh tren trang hang ({f[3]})."
                verified += 1
            elif raw.startswith((" ", "\t")):
                if cur is None:
                    raise ValueError("plan line without service")
                pid, pname, cyc, us, vn = (f + [""] * 6)[:5]
                members = f[5] if len(f) > 5 else ""
                plan = {"id": pid, "name": pname, "status": "active",
                        "cycle": {"unit": UNITS[cyc[0]], "count": int(cyc[1:] or 1)}, "prices": {}}
                if members:
                    plan["members"] = int(members)
                if us:
                    plan["prices"]["US"] = price(us, "USD")
                if vn:
                    plan["prices"]["VN"] = price(vn, "VND")
                cur["plans"].append(plan)
            else:
                sid, name, cat, dom, color, mono, al, sn, cancel, manage = (f + [""] * 10)[:10]
                if sid in by_id:
                    raise ValueError(f"service '{sid}' already exists")
                color = (color or gen_color(sid)).upper()
                mono = mono or gen_mono(name)
                while (color, mono) in tiles:
                    color = "#%06X" % ((int(color[1:], 16) + 0x050301) & 0xFFFFFF)
                tiles.add((color, mono))
                aliases = []
                for a in [name.lower()] + [x.lower() for x in al.split(";") if x] + [CAT_ALIAS.get(cat, "")]:
                    if a and a not in aliases:
                        aliases.append(a)
                cur = {"id": sid, "name": name, "category": cat, "color": color, "monogram": mono,
                       "market": market, "logoDomain": dom, "aliases": aliases}
                if sn:
                    cur["storeNames"] = [x for x in sn.split(";") if x]
                cur.update({"cancelUrl": cancel or None, "manageUrl": manage or None, "plans": [],
                            "note": REF_NOTE if market == "global" else
                            "C1 2026-11-06: gia VN uoc luong (Gia tham khao), chua tra trang hang."})
                data["services"].append(cur)
                by_id[sid] = cur
                added += 1
        except (KeyError, ValueError, IndexError) as e:
            errs.append(f"line {n}: {e!r}: {line.strip()[:80]}")
    if errs:
        print("\n".join(errs))
        return 1
    order = list(common_categories())
    data["services"].sort(key=lambda s: order.index(s["category"]))  # stable: keeps order inside a category
    changed = common.content_key(data) != before
    print(f"added {added}, storeNames patched {patched}, verified {verified}, changed={changed}")
    if changed and not dry:
        data["version"] += 1
        data["updatedAt"] = common.today()
        common.write_outputs(data)
    return 0


def common_categories():
    return ["video", "music", "ai", "storage", "software", "gaming", "reading", "health", "education", "telecom",
            "other"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
