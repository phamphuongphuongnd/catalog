"""Export the bundled copy for the Subnest app: services.json without `note` + a standalone validator.

    python tools/export_app_asset.py ../apps/A001-subnest/assets/catalog
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

HEAD = '''#!/usr/bin/env python3
"""Validate assets/catalog/services.json (Subnest catalog schema v4, see ../README.md). Standard library only.

GENERATED from the catalog repo (tools/validate.py + tools/common.py by tools/export_app_asset.py) — do not edit
here; change the catalog repo and regenerate.

    python assets/catalog/tool/validate_catalog.py [services.json] [--published OLD.json] [--json]
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

DEFAULT = Path(__file__).resolve().parent.parent / "services.json"
'''


def build_validator() -> str:
    tools = Path(__file__).resolve().parent
    c = (tools / "common.py").read_text(encoding="utf-8")
    v = (tools / "validate.py").read_text(encoding="utf-8")
    consts = [re.search(rf"^{n} = .*$", c, re.M).group(0)
              for n in ("SCHEMA_VERSION", "STALE_AFTER_DAYS", "REGIONS", "METHODS", "PLAN_STATUSES")]
    funcs = "".join(re.search(rf"^def {f}\(.*?(?=^def |\Z)", c, re.M | re.S).group(0)
                    for f in ("today", "load", "counts", "is_stale"))
    funcs = funcs.replace("def load(path: Path = SERVICES)", "def load(path: Path = DEFAULT)")
    body = v.split("import common  # noqa: E402\n", 1)[1].replace("common.", "")
    body = body.replace("path = Path(args[0]) if args else SERVICES", "path = Path(args[0]) if args else DEFAULT")
    return HEAD + "\n".join(consts) + "\n\n\n" + funcs + body


def main(argv) -> int:
    out = Path(argv[0])
    data = common.strip_for_min(common.load())
    (out / "services.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                       newline="\n")
    (out / "tool").mkdir(exist_ok=True)
    (out / "tool" / "validate_catalog.py").write_text(build_validator(), encoding="utf-8", newline="\n")
    print(f"exported version {data['version']}: {common.counts(data)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
