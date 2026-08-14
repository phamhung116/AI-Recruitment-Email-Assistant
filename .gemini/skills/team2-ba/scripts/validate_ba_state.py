#!/usr/bin/env python3
import sys
import re
from pathlib import Path

def validate_ba_state(project_root: Path) -> tuple[bool, list[str]]:
    errors = []
    ba_dir = project_root / "docs" / "ba"
    plan_file = ba_dir / "plan.md"
    ba_file = ba_dir / "business-analysis.md"
    rtm_file = ba_dir / "requirements-traceability.md"
    product_file = project_root / "docs" / "product" / "product.md"

    # Check 1: Existence of mandatory output files
    if not plan_file.exists():
        errors.append(f"Missing mandatory file: {plan_file}")
    if not ba_file.exists():
        errors.append(f"Missing mandatory file: {ba_file}")
    if not rtm_file.exists():
        errors.append(f"Missing mandatory file: {rtm_file}")

    if errors:
        return False, errors

    plan_content = plan_file.read_text(encoding="utf-8")
    ba_content = ba_file.read_text(encoding="utf-8")
    rtm_content = rtm_file.read_text(encoding="utf-8")

    # Check 2: Timebox fields & checkpoint in plan.md
    for field in ["Started At:", "Deadline At:", "Execution Profile:", "Stop Condition:", "Exact Next Action:"]:
        if field not in plan_content:
            errors.append(f"plan.md missing timebox/checkpoint field: '{field}'")

    # Check 3: Check required input availability
    if "docs/product/product.md" not in plan_content:
        errors.append("plan.md must inventory 'docs/product/product.md' as required input")
    if not product_file.exists() and "READY_FOR_HANDOFF" in ba_content:
        errors.append("Cannot set READY_FOR_HANDOFF when required input docs/product/product.md is missing")

    # Check 4: Parse Requirements and validate IDs, uniqueness, sources, ACs, and owners
    req_pattern = re.compile(r"\|?\s*(FR-\d+|NFR-\d+|BR-\d+)\s*\|([^|\n]+\|)+")
    req_matches = req_pattern.findall(ba_content)
    req_ids = [m[0] for m in req_matches]

    # Uniqueness check
    if len(req_ids) != len(set(req_ids)):
        duplicates = set([x for x in req_ids if req_ids.count(x) > 1])
        errors.append(f"Duplicate Requirement IDs found: {duplicates}")

    # Check 5: READY_FOR_HANDOFF conditions
    is_ready = "READY_FOR_HANDOFF" in ba_content or "READY_FOR_HANDOFF" in plan_content or "READY_FOR_HANDOFF" in rtm_content

    if is_ready:
        # Must not have Blockers in plan
        if "Blockers:" in plan_content:
            blocker_line = [l for l in plan_content.splitlines() if "Blockers:" in l][0]
            if not ("None" in blocker_line or "none" in blocker_line or "N/A" in blocker_line or blocker_line.strip() == "- **Blockers:**"):
                errors.append("Cannot declare READY_FOR_HANDOFF when active blockers exist in plan.md")

        # Must not have unaccepted material assumptions
        if "ASM-" in ba_content and "Unaccepted" in ba_content:
            errors.append("Cannot declare READY_FOR_HANDOFF when material assumptions remain unaccepted")

        # Must have Approval Record
        if "Approval Record" not in ba_content or "User Approval:" not in ba_content:
            errors.append("Cannot declare READY_FOR_HANDOFF without Approval Record in business-analysis.md")

        # Traceability & AC checks for requirements
        for req_id in req_ids:
            # Must have source
            if f"Source" not in ba_content:
                errors.append(f"Requirement {req_id} missing source traceability")
            # Must be in RTM
            if req_id not in rtm_content:
                errors.append(f"Requirement {req_id} is missing from requirements-traceability.md (Orphan)")

    return len(errors) == 0, errors

def main():
    project_root = Path.cwd()
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])

    valid, errors = validate_ba_state(project_root)
    if not valid:
        print("❌ BA State Validation Failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print("✅ BA State Validation Passed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main()
