#!/usr/bin/env python3
"""
Fingerprint canonical input files for team1-ba skill.
Calculates SHA-256 hashes to detect input updates or staleness in resume mode.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

CANONICAL_INPUTS = [
    "docs/product/product.md",
    "docs/architecture/architecture.md",
    "docs/database/database.md",
    "docs/ui-ux/ui-to-frontend.md",
    "docs/backend/backend.md",
]

def hash_file(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def fingerprint_inputs(project_root: str) -> dict:
    root = Path(project_root).resolve()
    inventory = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "inputs": {}
    }

    for rel_path in CANONICAL_INPUTS:
        full_path = root / rel_path
        if full_path.exists() and full_path.is_file():
            try:
                file_hash = hash_file(full_path)
                mtime = os.path.getmtime(full_path)
                inventory["inputs"][rel_path] = {
                    "available": True,
                    "sha256": file_hash,
                    "last_modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                    "status": "valid"
                }
            except Exception as e:
                inventory["inputs"][rel_path] = {
                    "available": False,
                    "error": str(e),
                    "status": "error"
                }
        else:
            inventory["inputs"][rel_path] = {
                "available": False,
                "status": "missing"
            }

    return inventory

def main():
    parser = argparse.ArgumentParser(description="Fingerprint BA canonical input files.")
    parser.add_argument("--root", default=".", help="Project root directory path")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    res = fingerprint_inputs(args.root)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"Fingerprint report generated at {res['generated_at']}")
        for path, info in res["inputs"].items():
            if info["available"]:
                print(f"[FOUND] {path} | Hash: {info['sha256'][:12]}... | Status: {info['status']}")
            else:
                print(f"[MISSING] {path}")

if __name__ == "__main__":
    main()
