"""Export or verify the static OpenAPI artifact from the FastAPI runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
OUTPUT_PATH = PROJECT_ROOT / "docs" / "backend" / "openapi.json"
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app  # noqa: E402


def serialized_schema() -> str:
    return json.dumps(
        create_app().openapi(),
        indent=2,
        ensure_ascii=True,
        sort_keys=True,
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when the committed artifact differs from runtime OpenAPI.",
    )
    args = parser.parse_args()
    expected = serialized_schema()

    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != expected:
            print(f"OpenAPI drift detected: {OUTPUT_PATH}")
            return 1
        print(f"OpenAPI is synchronized: {OUTPUT_PATH}")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Exported OpenAPI: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
