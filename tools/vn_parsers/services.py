"""One fixed reader per Vietnamese price page.

Each reader fetches ONE official page, extracts prices with a pattern anchored on the plan name and returns
Reading(service_id, plan_id, amount, source). Any exception = that reader failed this week; the runner keeps the
old price and lists the failure in the report. Keep patterns strict: a wrong match is worse than no match.

Pages checked 2026-11-06 from a VN IP (static HTML contains the price). Whether they answer the US-based GitHub
runner is recorded in the weekly report; a reader that keeps failing there should move to UNREADABLE.
"""
from __future__ import annotations

from .base import Reading, fetch, find_vnd, page_text

READERS = []


def reader(fn):
    READERS.append(fn)
    return fn


@reader
def netflix():
    # Netflix help centre, Vietnamese, country forced by the /vn suffix (not by IP).
    url = "https://help.netflix.com/vi/node/24926/vn"
    t = page_text(fetch(url))
    if "Việt Nam Đồng" not in t:
        raise ValueError("page is not showing VND prices")
    out = []
    for plan_id, label in (("mobile", "Di động"), ("basic", "Cơ bản"), ("standard", "Tiêu chuẩn"),
                           ("premium", "Cao cấp")):
        amt = find_vnd(t, label + r"\s*:\s*([\d.]+)\s*VNĐ\s*/\s*tháng", f"netflix {plan_id}")
        out.append(Reading("netflix", plan_id, amt, url))
    return out


@reader
def spotify():
    # Spotify Vietnam premium page; locale in the path, so readable from any IP. Only Individual shows a price.
    url = "https://www.spotify.com/vn-vi/premium/"
    t = page_text(fetch(url))
    amt = find_vnd(t, r"Premium Individual.{0,160}?[Ss]au đó là ([\d.]+) ₫\s*/\s*tháng", "spotify individual")
    return [Reading("spotify", "individual", amt, url)]


@reader
def vnpt_internet():
    url = "https://vnpt.vn/goi-home/home-internet"
    t = page_text(fetch(url))
    amt = find_vnd(t, r"Home 1 Internet.{0,300}?Giá:\s*([\d.]+)\s*đ\s*/\s*tháng", "vnpt-internet Home 1")
    return [Reading("vnpt-internet", "basic", amt, url)]


@reader
def vinaphone():
    out, errors = [], []
    for plan_id, code in (("big90", "BIG90"), ("big120", "BIG120")):
        url = f"https://vnpt.vn/4g/{code.lower()}"
        try:
            t = page_text(fetch(url))
            if code not in t:
                raise ValueError(f"{code} not mentioned on page")
            amt = find_vnd(t, r"Giá\s*([\d.]+)\s*đ", f"vinaphone {plan_id}")
            out.append(Reading("vinaphone", plan_id, amt, url))
        except Exception as e:  # noqa: BLE001 — one plan failing must not hide the other
            errors.append(f"{plan_id}: {e}")
    if errors and not out:
        raise ValueError("; ".join(errors))
    for e in errors:
        out.append(e)  # partial failure: runner reports strings as errors
    return out


@reader
def mobifone():
    url = "https://www.mobifone.vn/dich-vu-di-dong/chi-tiet-goi-cuoc/tk135-TK135"
    t = page_text(fetch(url))
    amt = find_vnd(t, r"Tên gói cước TK135 Giá gói ([\d.]+)\s*đ Thời hạn 30 ngày", "mobifone tk135")
    return [Reading("mobifone", "tk135", amt, url)]


@reader
def monkey_junior():
    url = "https://monkey.edu.vn/san-pham/monkey-junior"
    t = page_text(fetch(url))
    amt = find_vnd(t, r"1 Năm [\d.]+ ?đ ?/ ?Ngày ([\d.]+)\s*đ", "monkey-junior 1 năm")
    return [Reading("monkey-junior", "junior-annual", amt, url)]


@reader
def fpt_internet():
    url = "https://fpt.vn/internet"
    t = page_text(fetch(url))
    amt = find_vnd(t, r"Internet GIGA \(Internet\) ([\d.]+)\s*₫", "fpt-internet GIGA")
    return [Reading("fpt-internet", "basic", amt, url)]


# Checked 2026-11-06 and NOT read automatically (reason). Update these by hand (method "manual").
UNREADABLE = {
    "fpt-play": "fpt.vn/.../fpt-play-menu.html chỉ có combo Internet+TV trong HTML tĩnh; giá MAX/VIP nạp bằng JS",
    "tv360": "tv360.vn là ứng dụng JS, HTML tĩnh không có giá; giá đổi qua thông báo trên viettel.vn",
    "vieon": "giá gói chỉ hiện sau đăng nhập/trong app",
    "galaxy-play": "trang công khai duy nhất có giá là điều khoản cũ (giá 2020) — không dùng được",
    "zing-mp3": "zingmp3.vn/vip là ứng dụng JS; chỉ ghi 'từ X đ/tháng'",
    "viettel-mobile": "vietteltelecom.vn / viettel.vn là ứng dụng JS, HTML tĩnh không có giá",
    "viettel-internet": "viettel.vn/internet là ứng dụng JS",
    "mobifone/kc90": "trang chi tiết KC90 trả 404 (2026-11-06); chỉ TK135 đọc được",
    "elsa-speak": "elsaspeak.vn/bang-gia hết thời gian chờ khi tải bằng script",
    "zcloud": "help.zalo.me chỉ ghi 'từ 15.800đ/tháng', không có bảng giá",
    "youtube-premium": "youtube.com/premium chọn vùng theo IP — runner GitHub ở Mỹ chỉ thấy giá US",
    "bkav-pro / voiz-fm": "trang không ghi ngày/giá đầy đủ",
}
