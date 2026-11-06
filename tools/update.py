"""Weekly update: run fetchers -> apply -> validate against the published file -> write data + report.

    python tools/update.py [--dry-run]

Exit 0: data valid (written, maybe unchanged). Exit 1: validation failed — nothing is written except the report,
so the published catalog stays as it was.
Sources:
  - VN page readers (tools/vn_parsers) — always.
  - Aristocles — NOT used (licence unclear, see README "Aristocles"); the step is reported as skipped.
"""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import validate  # noqa: E402
import vn_parsers  # noqa: E402


def apply(data: dict, readings, method: str, on: str):
    """Write readings into data. Returns list of (service/plan/region, old, new, status)."""
    rows = []
    for r in readings:
        plan = common.find_plan(data, r.service_id, r.plan_id)
        key = f"{r.service_id}/{r.plan_id}/{r.region}"
        if plan is None:
            rows.append((key, None, r.amount, "unknown plan — ignored"))
            continue
        old = plan["prices"].get(r.region)
        new = {"currency": r.currency, "amount": r.amount, "verifiedAt": on, "source": r.source, "method": method}
        if old is None:
            status = "new price"
        elif old.get("amount") != r.amount:
            status = "changed"
        else:
            status = "same (re-verified)"
        plan["prices"][r.region] = new
        rows.append((key, old.get("amount") if old else None, r.amount, status))
    return rows


def fmt(n):
    if n is None:
        return "—"
    return f"{n:,.0f}".replace(",", ".") if float(n).is_integer() else f"{n:.2f}"


def report(on, before, after, rows, read_errors, errors, warns, stats, written) -> str:
    lines = [f"# Báo cáo cập nhật catalog — {on}", ""]
    if errors:
        lines += ["**KẾT QUẢ: KHÔNG ĐĂNG** — validator báo lỗi, bản đang đăng giữ nguyên.", ""]
    elif after != before:
        verb = "ĐÃ ĐĂNG" if written else "SẼ ĐĂNG (chạy thử, chưa ghi)"
        lines += [f"**KẾT QUẢ: {verb}** version {before} → **{after}**.", ""]
    else:
        lines += [f"**KẾT QUẢ: không đổi dữ liệu** (version {before}).", ""]
    lines += [f"- Dịch vụ · gói · giá: {stats.get('services')} · {stats.get('plans')} · {stats.get('prices')}",
              f"- Giá chưa xác minh hoặc quá {common.STALE_AFTER_DAYS} ngày: {stats.get('unverified_or_stale')}",
              "- Aristocles (US): **bỏ qua** — chưa rõ quyền đăng lại dữ liệu (README › Aristocles).",
              ""]
    changed = [r for r in rows if r[3] != "same (re-verified)"]
    lines += ["## Giá đổi", ""]
    if changed:
        lines += ["| Dịch vụ/gói/vùng | Cũ | Mới | Ghi chú |", "|---|---:|---:|---|"]
        lines += [f"| `{k}` | {fmt(o)} | {fmt(n)} | {s} |" for k, o, n, s in changed]
    else:
        lines.append("Không có.")
    lines += ["", "## Đọc lại khớp (cập nhật verifiedAt)", ""]
    same = [r[0] for r in rows if r[3] == "same (re-verified)"]
    lines.append(", ".join(f"`{k}`" for k in same) if same else "Không có.")
    lines += ["", "## Lỗi đọc (giữ giá cũ)", ""]
    lines += [f"- {e}" for e in read_errors] or ["Không có."]
    lines += ["", "## Validator", ""]
    lines += [f"- LỖI: {e}" for e in errors]
    lines += [f"- Cảnh báo: {w}" for w in warns]
    if not errors and not warns:
        lines.append("OK.")
    return "\n".join(lines) + "\n"


def main() -> int:
    dry = "--dry-run" in sys.argv
    on = common.today()
    published = common.load()
    data = copy.deepcopy(published)

    readings, read_errors = vn_parsers.run_all()
    rows = apply(data, readings, "vn-parser", on)

    errors, warns, stats = validate.validate(data, published, on)
    written = False
    before = published["version"]
    after = before
    if not errors and common.content_key(data) != common.content_key(published):
        data["version"] = before + 1
        data["updatedAt"] = on
        after = data["version"]
        errors, warns, stats = validate.validate(data, published, on)  # re-check final file
        if not errors and not dry:
            common.write_outputs(data)
            written = True

    text = report(on, before, after, rows, read_errors, errors, warns, stats, written)
    if not dry:
        common.REPORTS.mkdir(exist_ok=True)
        (common.REPORTS / f"{on}.md").write_bytes(text.encode("utf-8"))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text)
    print(text)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
