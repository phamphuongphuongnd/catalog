"""One-off: convert the app-bundled catalog v3 (A001-subnest assets/catalog/services.json) to schema v4.

    python -I -X utf8 tools/migrate_v3.py <path/to/v3/services.json>

- prices: `approx` flag -> {verifiedAt, source, method}. Non-approx v3 prices were checked on 2026-11-05 (v3
  `priceSurveyDate`); their human-readable sources live in the v3 `note`, frozen in docs/sources-v3.md, so `source`
  points to that service's section. Approx prices get no verifiedAt/source (= unverified).
- service.logoDomain from the hand-made map below; plan.status / renamedFrom from STATUS below.
- writes subnest/v1/services.json + services.min.json + meta.json and docs/sources-v3.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

SOURCES_DOC = "docs/sources-v3.md"
SOURCES_URL = "https://github.com/phamphuongphuongnd/catalog/blob/main/docs/sources-v3.md"

LOGO_DOMAINS = {
    "netflix": "netflix.com", "youtube-premium": "youtube.com", "disney-plus": "disneyplus.com",
    "prime-video": "primevideo.com", "apple-tv": "tv.apple.com", "hbo-max": "hbomax.com", "hulu": "hulu.com",
    "peacock": "peacocktv.com", "paramount-plus": "paramountplus.com", "crunchyroll": "crunchyroll.com",
    "fpt-play": "fptplay.vn", "vieon": "vieon.vn", "galaxy-play": "galaxyplay.vn", "tv360": "tv360.vn",
    "spotify": "spotify.com", "apple-music": "music.apple.com", "youtube-music": "music.youtube.com",
    "zing-mp3": "zingmp3.vn", "tidal": "tidal.com", "deezer": "deezer.com", "amazon-music": "music.amazon.com",
    "soundcloud": "soundcloud.com", "chatgpt": "chatgpt.com", "claude": "claude.ai", "gemini": "gemini.google.com",
    "copilot": "copilot.microsoft.com", "midjourney": "midjourney.com", "perplexity": "perplexity.ai",
    "grok": "grok.com", "cursor": "cursor.com", "github-copilot": "github.com", "elevenlabs": "elevenlabs.io",
    "icloud": "icloud.com", "google-one": "one.google.com", "dropbox": "dropbox.com",
    "microsoft-365": "microsoft365.com", "zcloud": "zalo.me", "backblaze": "backblaze.com", "canva": "canva.com",
    "adobe-cc": "adobe.com", "notion": "notion.so", "1password": "1password.com", "bitwarden": "bitwarden.com",
    "nordvpn": "nordvpn.com", "expressvpn": "expressvpn.com", "surfshark": "surfshark.com",
    "grammarly": "grammarly.com", "figma": "figma.com", "capcut": "capcut.com", "zoom": "zoom.us",
    "evernote": "evernote.com", "todoist": "todoist.com", "proton": "proton.me", "bkav-pro": "bkav.com.vn",
    "xbox-game-pass": "xbox.com", "playstation-plus": "playstation.com", "nintendo-switch-online": "nintendo.com",
    "apple-arcade": "apple.com", "google-play-pass": "play.google.com", "ea-play": "ea.com",
    "ubisoft-plus": "ubisoft.com", "geforce-now": "nvidia.com", "roblox-premium": "roblox.com",
    "discord-nitro": "discord.com", "kindle-unlimited": "amazon.com", "audible": "audible.com",
    "medium": "medium.com", "apple-news-plus": "apple.com", "nytimes": "nytimes.com", "voiz-fm": "voiz.vn",
    "strava": "strava.com", "headspace": "headspace.com", "calm": "calm.com", "myfitnesspal": "myfitnesspal.com",
    "apple-fitness-plus": "apple.com", "fitbit-premium": "fitbit.com", "duolingo": "duolingo.com",
    "coursera": "coursera.org", "elsa-speak": "elsaspeak.com", "quizlet": "quizlet.com",
    "monkey-junior": "monkey.edu.vn", "viettel-mobile": "viettel.vn", "vinaphone": "vinaphone.com.vn",
    "mobifone": "mobifone.vn", "viettel-internet": "viettel.vn", "fpt-internet": "fpt.vn",
    "vnpt-internet": "vnpt.vn", "amazon-prime": "amazon.com", "apple-one": "apple.com", "x-premium": "x.com",
    "telegram-premium": "telegram.org", "uber-one": "uber.com", "linkedin-premium": "linkedin.com",
    "snapchat-plus": "snapchat.com", "youtube-tv": "tv.youtube.com", "twitch-turbo": "twitch.tv",
    "peloton-app": "onepeloton.com", "everand": "everand.com", "blinkist": "blinkist.com",
}

# (service, plan) -> fields; everything else is "active".
STATUS = {
    ("copilot", "pro"): {"status": "closed_to_new"},  # replaced by Microsoft 365 Premium (10/2025)
    ("adobe-cc", "photography-20gb"): {"status": "closed_to_new"},  # Adobe: 20GB plan no longer sold to new users
    ("grok", "supergrok"): {"status": "closed_to_new"},  # sold via "The X Subscription" since 10/2026
    ("evernote", "personal"): {"name": "Starter", "renamedFrom": "Personal"},
    ("evernote", "personal-annual"): {"name": "Starter (annual)", "renamedFrom": "Personal (annual)"},
    ("prime-video", "ad-free"): {"renamedFrom": "Prime Video ad-free"},
}

SERVICE_KEYS = ["id", "name", "category", "color", "monogram", "market", "logoDomain", "aliases",
                "cancelUrl", "manageUrl", "plans", "note"]
PLAN_KEYS = ["id", "name", "status", "renamedFrom", "cycle", "members", "prices"]


def anchor(service_id: str) -> str:
    # GitHub heading anchors: lowercase, keep [a-z0-9-]
    return re.sub(r"[^a-z0-9-]", "", service_id.lower())


def convert(v3: dict) -> dict:
    survey = v3.get("priceSurveyDate") or v3["updatedAt"]
    services = []
    for s in v3["services"]:
        sid = s["id"]
        if sid not in LOGO_DOMAINS:
            raise SystemExit(f"missing logoDomain for {sid}")
        ns = dict(s)
        ns["market"] = s.get("market", "global")
        ns["logoDomain"] = LOGO_DOMAINS[sid]
        plans = []
        for p in s["plans"]:
            np = dict(p)
            np["status"] = "active"
            np.update(STATUS.get((sid, p["id"]), {}))
            prices = {}
            for region, pr in p["prices"].items():
                q = {"currency": pr["currency"], "amount": pr["amount"]}
                if not pr.get("approx"):
                    q["verifiedAt"] = survey
                    q["source"] = f"{SOURCES_URL}#{anchor(sid)}"
                q["method"] = "manual"
                prices[region] = q
            np["prices"] = prices
            plans.append({k: np[k] for k in PLAN_KEYS if k in np})
        ns["plans"] = plans
        services.append({k: ns[k] for k in SERVICE_KEYS if k in ns})
    return {
        "schemaVersion": common.SCHEMA_VERSION,
        "version": int(v3["version"]) + 1,
        "updatedAt": common.today(),
        "staleAfterDays": common.STALE_AFTER_DAYS,
        "regions": dict(common.REGIONS),
        "services": services,
    }


def sources_doc(v3: dict) -> str:
    lines = [
        "# Nguồn giá catalog v3 (bản đóng băng)",
        "",
        "Ghi chú nguồn của từng dịch vụ trong catalog v3 (A001-subnest, khảo sát 2026-11-04/05), chép nguyên văn từ",
        "trường `note`. Các giá v4 có `method: manual` và `source` trỏ về mục dưới đây nghĩa là được người bảo trì",
        "đối chiếu tay theo ghi chú này. Khi bộ đọc tự động xác minh lại, `source` đổi sang URL trang giá thật.",
        "",
    ]
    for s in v3["services"]:
        lines += [f"## {anchor(s['id'])}", "", f"**{s['name']}** — {s.get('note') or '(không có ghi chú)'}", ""]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    v3 = common.load(common.Path(sys.argv[1]))
    if v3.get("version") != 3:
        raise SystemExit("expected catalog version 3")
    v4 = convert(v3)
    meta = common.write_outputs(v4)
    (common.ROOT / SOURCES_DOC).write_bytes(sources_doc(v3).encode("utf-8"))
    print(f"v4 written: version {v4['version']}, {meta['services']} services, {meta['plans']} plans, "
          f"{meta['prices']} prices")
    return 0


if __name__ == "__main__":
    sys.exit(main())
