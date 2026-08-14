#!/usr/bin/env python3
"""
Deterministic state validator for team1-ba skill.
Validates BA outputs against Section 11 quality gate rules.
Exits with 0 on success, non-zero on validation failure.
"""

import argparse
import re
import sys
from pathlib import Path

VALID_ID_PATTERNS = {
    "OBJ": r"^OBJ-\d{3,}$",
    "ACT": r"^ACT-\d{3,}$",
    "FR": r"^FR-\d{3,}$",
    "NFR": r"^NFR-\d{3,}$",
    "BR": r"^BR-\d{3,}$",
    "UC": r"^UC-\d{3,}$",
    "AC": r"^AC-\d{3,}$",
    "ASM": r"^ASM-\d{3,}$",
    "CON": r"^CON-\d{3,}$",
    "DEP": r"^DEP-\d{3,}$",
    "OQ": r"^OQ-\d{3,}$",
    "DEC": r"^DEC-\d{3,}$",
    "CR": r"^CR-\d{3,}$",
}

VALID_DOWNSTREAM_OWNERS = {"Architecture", "Database", "UI/UX", "Backend", "Frontend", "QA"}

REQUIRED_SECTIONS_BA = [
    "Executive Summary",
    "Sources & Approval State",
    "Business Objectives",
    "Scope & Out of Scope",
    "Stakeholders & Actors",
    "AS-IS & TO-BE Workflows",
    "Functional Requirements",
    "Non-Functional Requirements",
    "Business Rules",
    "Use Cases",
    "Acceptance Criteria",
    "Edge Cases & Exception Flows",
    "Assumptions",
    "Constraints & Dependencies",
    "Open Questions",
    "Risks & Impacts",
    "Downstream Handoff",
    "Approval Record",
]

REQUIRED_FIELDS_PLAN = [
    "Mode",
    "Execution Profile",
    "Started At",
    "Deadline At",
    "Status",
    "In Scope",
    "Out of Scope",
    "Stop Condition",
    "Current Checkpoint",
    "Exact Next Action",
]

def validate_ba_state(project_root: str) -> tuple[bool, list[str]]:
    errors = []
    root = Path(project_root).resolve()

    plan_file = root / "docs/ba/plan.md"
    ba_file = root / "docs/ba/business-analysis.md"
    rtm_file = root / "docs/ba/requirements-traceability.md"
    product_file = root / "docs/product/product.md"

    # 1. Check required product input
    if not product_file.exists():
        errors.append("[ERROR] Missing required product input: 'docs/product/product.md'")

    # 2. Check BA output files existence
    if not plan_file.exists():
        errors.append("[ERROR] Missing required BA output: 'docs/ba/plan.md'")
    if not ba_file.exists():
        errors.append("[ERROR] Missing required BA output: 'docs/ba/business-analysis.md'")
    if not rtm_file.exists():
        errors.append("[ERROR] Missing required BA output: 'docs/ba/requirements-traceability.md'")

    if errors:
        return False, errors

    # Read file contents
    plan_content = plan_file.read_text(encoding="utf-8")
    ba_content = ba_file.read_text(encoding="utf-8")
    rtm_content = rtm_file.read_text(encoding="utf-8")

    # Parse Plan status and fields
    status_match = re.search(r"Status\*\*:\s*\[?([A-Z_]+)\]?", plan_content)
    plan_status = status_match.group(1).strip() if status_match else "UNKNOWN"

    for field in REQUIRED_FIELDS_PLAN:
        if field not in plan_content:
            errors.append(f"[ERROR] plan.md missing required field: '{field}'")

    # Check timebox fields
    if "Started At" in plan_content and "[ISO-8601 Timestamp]" in plan_content:
        errors.append("[ERROR] plan.md contains unpopulated Started At timestamp placeholder")

    # Check required BA sections
    for sec in REQUIRED_SECTIONS_BA:
        if sec not in ba_content:
            errors.append(f"[ERROR] business-analysis.md missing required section: '{sec}'")

    # Parse IDs
    id_regex = r"\b(OBJ|ACT|FR|NFR|BR|UC|AC|ASM|CON|DEP|OQ|DEC|CR)-\d{3,}\b"
    found_ids = set(re.findall(id_regex, ba_content))
    all_id_matches = re.findall(r"\b((?:OBJ|ACT|FR|NFR|BR|UC|AC|ASM|CON|DEP|OQ|DEC|CR)-\d{3,})\b", ba_content)

    # Check duplicate IDs in definitions
    def_ids = re.findall(r"-\s*`(FR-\d{3,}|NFR-\d{3,}|OBJ-\d{3,}|ACT-\d{3,}|AC-\d{3,}|ASM-\d{3,})`:", ba_content)
    seen_ids = set()
    for d_id in def_ids:
        if d_id in seen_ids:
            errors.append(f"[ERROR] Duplicate requirement ID definition found: '{d_id}'")
        seen_ids.add(d_id)

    # Parse Functional Requirements blocks
    fr_blocks = re.findall(r"-\s*`(FR-\d{3,})`:\s*([^\n]+(?:\n\s+-[^\n]+)*)", ba_content)

    confirmed_frs = []
    for fr_id, fr_text in fr_blocks:
        # Check source
        source_match = re.search(r"Source:\s*\[?([^\]\n]+)\]?", fr_text)
        if not source_match or not source_match.group(1).strip() or source_match.group(1).strip() in ["SPEC-###", "None", "N/A"]:
            errors.append(f"[ERROR] {fr_id} missing valid source (SOURCE_BEFORE_REQUIREMENT violation)")

        # Check acceptance criteria
        ac_match = re.search(r"Acceptance Criteria:\s*\[?([^\]\n]+)\]?", fr_text)
        if not ac_match or not ac_match.group(1).strip() or ac_match.group(1).strip() == "None":
            errors.append(f"[ERROR] {fr_id} missing Acceptance Criteria")

        # Check downstream owners
        owner_match = re.search(r"Downstream Owners:\s*\[?([^\]\n]+)\]?", fr_text)
        if not owner_match or not owner_match.group(1).strip():
            errors.append(f"[ERROR] {fr_id} missing Downstream Owners")
        else:
            owners = [o.strip() for o in owner_match.group(1).split(",")]
            invalid_owners = [o for o in owners if o not in VALID_DOWNSTREAM_OWNERS]
            if invalid_owners:
                errors.append(f"[ERROR] {fr_id} has invalid downstream owner(s): {invalid_owners}")

        status_m = re.search(r"Status:\s*\[?([a-z_]+)\]?", fr_text)
        if status_m and status_m.group(1).strip() == "confirmed":
            confirmed_frs.append(fr_id)

    # Check READY_FOR_HANDOFF gate rules
    if plan_status == "READY_FOR_HANDOFF":
        # 1. No unresolved open questions / blockers
        if "OQ-" in ba_content and "Status: blocker" in ba_content:
            errors.append("[ERROR] Cannot handoff: unresolved blocker Open Questions exist")

        # 2. No unaccepted material assumptions
        asm_matches = re.findall(r"-\s*`(ASM-\d{3,})`:.*\(Trạng thái:\s*\[?([a-z_]+)\]?\)", ba_content)
        for asm_id, asm_status in asm_matches:
            if asm_status.strip() != "accepted":
                errors.append(f"[ERROR] Cannot handoff: unaccepted material assumption '{asm_id}' ({asm_status})")

        # 3. Must have explicit approval record
        if "Confirmed by User" not in ba_content and "Stakeholder Approval: [APPROVED" not in ba_content:
            errors.append("[ERROR] Cannot handoff: missing explicit user approval record in Section 18")

    return (len(errors) == 0), errors

def main():
    parser = argparse.ArgumentParser(description="Validate BA state artifacts.")
    parser.add_argument("--root", default=".", help="Project root directory path")
    args = parser.parse_args()

    success, errors = validate_ba_state(args.root)
    if success:
        print("[SUCCESS] BA state is valid and ready!")
        sys.exit(0)
    else:
        print(f"[FAIL] BA state validation failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
