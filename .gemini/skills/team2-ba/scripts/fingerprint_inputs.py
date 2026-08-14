#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

def calculate_sha256(filepath: Path) -> str:
    if not filepath.exists() or not filepath.is_file():
        return "FILE_NOT_FOUND"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    project_root = Path.cwd()
    if len(sys.argv) > 1:
        files_to_check = [Path(p) for p in sys.argv[1:]]
    else:
        files_to_check = [
            project_root / "docs" / "product" / "product.md",
            project_root / "docs" / "architecture" / "architecture.md",
            project_root / "docs" / "database" / "database.md",
            project_root / "docs" / "ui-ux" / "ui-to-frontend.md",
            project_root / "docs" / "backend" / "backend.md",
        ]

    results = {}
    for file_path in files_to_check:
        rel_path = str(file_path.relative_to(project_root)) if file_path.is_relative_to(project_root) else str(file_path)
        results[rel_path] = {
            "exists": file_path.exists(),
            "sha256": calculate_sha256(file_path)
        }

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
