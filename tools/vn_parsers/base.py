"""Fetch + text helpers for the fixed Vietnamese price-page readers (standard library only)."""
from __future__ import annotations

import html
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0 Safari/537.36 SubnestCatalogBot/1.0 (+https://github.com/phamphuongphuongnd/catalog)")
TIMEOUT = 30
MIN_VND, MAX_VND = 1_000, 50_000_000


class ParseError(Exception):
    """Page fetched but the expected price was not found / not plausible."""


@dataclass
class Reading:
    service_id: str
    plan_id: str
    amount: int
    source: str
    region: str = "VN"
    currency: str = "VND"


def _open(url: str, ctx: ssl.SSLContext | None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.5"})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def fetch(url: str) -> str:
    """GET a page. Some VN sites (vnpt.vn) still use small DH keys -> retry with OpenSSL security level 1."""
    try:
        return _open(url, None)
    except (ssl.SSLError, urllib.error.URLError) as e:
        reason = getattr(e, "reason", e)
        if not isinstance(reason, ssl.SSLError) and not isinstance(e, ssl.SSLError):
            raise
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        return _open(url, ctx)


def page_text(raw_html: str) -> str:
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw_html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", t)


def vnd(s: str) -> int:
    """'74.000' / '74,000' / '74000' -> 74000, with a plausibility check."""
    n = int(re.sub(r"[.,\s]", "", s))
    if not MIN_VND <= n <= MAX_VND:
        raise ParseError(f"implausible VND amount {s!r}")
    return n


def find_vnd(text: str, pattern: str, what: str) -> int:
    """First regex group of `pattern` in `text` as VND, else ParseError naming `what`."""
    m = re.search(pattern, text)
    if not m:
        raise ParseError(f"{what}: price pattern not found (page layout changed?)")
    return vnd(m.group(1))
