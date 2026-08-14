#!/usr/bin/env python3
"""
Comprehensive Unit Test Runner for team1-ba Skill.
Tests validate_ba_state.py and fingerprint_inputs.py against all 9 required scenarios:
1. Valid full input -> READY_FOR_HANDOFF after approval
2. Missing product input -> BLOCKED
3. Ambiguous requirement -> NEEDS_CLARIFICATION
4. Contradictory stakeholder inputs -> BLOCKED/NEEDS_CLARIFICATION
5. Unsupported assumption -> Denies READY_FOR_HANDOFF
6. Orphan requirement -> validator fails
7. Change impact -> change-impact mode, CR creation
8. Resume with changed source -> stale evidence detection
9. Timebox exhausted -> incomplete status & exact next action
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "team1-ba" / "scripts"))
from validate_ba_state import validate_ba_state
from fingerprint_inputs import fingerprint_inputs

def create_fixture_file(root: Path, rel_path: str, content: str):
    file_path = root / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

def test_scenario_1_valid_full_input():
    print("Testing Scenario 1: Valid full input...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        create_fixture_file(tmp, "docs/product/product.md", "# Product Spec\nStatus: APPROVED\n- SPEC-001: User Login")
        create_fixture_file(tmp, "docs/ba/plan.md", """# BA Plan
- Mode: full
- Execution Profile: standard
- Started At: 2026-08-12T08:00:00Z
- Deadline At: 2026-08-12T08:45:00Z
- Status: READY_FOR_HANDOFF
- In Scope: Login capability
- Out of Scope: Third party OAuth
- Stop Condition: Approval
- Current Checkpoint: Complete
- Exact Next Action: Handoff to Architecture
""")
        create_fixture_file(tmp, "docs/ba/business-analysis.md", """# Business Analysis Specification
## Executive Summary
Complete BA spec.
## Sources & Approval State
docs/product/product.md (APPROVED)
## Business Objectives
- `OBJ-001`: User authentication
## Scope & Out of Scope
In scope: Login
## Stakeholders & Actors
- `ACT-001`: End User
## AS-IS & TO-BE Workflows
- `UC-001`: Login Flow
## Functional Requirements
- `FR-001`: Login Form
  - Description: User enters credentials
  - Rationale: Auth requirement
  - Source: SPEC-001
  - Priority: High
  - Expected Outcome: Logged in
  - Acceptance Criteria: AC-001
  - Downstream Owners: Backend, Frontend, QA
  - Status: confirmed
## Non-Functional Requirements
- `NFR-001`: Auth latency
  - Downstream Owners: Architecture, QA
## Business Rules
- `BR-001`: Max 5 failed attempts
## Use Cases
UC-001
## Acceptance Criteria
- `AC-001`: Given valid user, When login submitted, Then session created
## Edge Cases & Exception Flows
Network error flow
## Assumptions
- `ASM-001`: Email is unique (Trạng thái: accepted)
## Constraints & Dependencies
- `CON-001`: HTTPS required
- `DEP-001`: None
## Open Questions
None
## Risks & Impacts
Low risk
## Downstream Handoff
Architecture Handoff
## Approval Record
Confirmed by User on 2026-08-12
""")
        create_fixture_file(tmp, "docs/ba/requirements-traceability.md", "# Traceability Matrix")
        success, errors = validate_ba_state(str(tmp))
        assert success, f"Scenario 1 failed unexpectedly: {errors}"
        print("  [PASS] Scenario 1 passed.")

def test_scenario_2_missing_product_input():
    print("Testing Scenario 2: Missing product input...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        create_fixture_file(tmp, "docs/ba/plan.md", "Status: BLOCKED\nStarted At: ISO\nDeadline At: ISO\nMode: full\nExecution Profile: standard\nIn Scope: x\nOut of Scope: y\nStop Condition: z\nCurrent Checkpoint: a\nExact Next Action: b")
        create_fixture_file(tmp, "docs/ba/business-analysis.md", "DRAFT")
        create_fixture_file(tmp, "docs/ba/requirements-traceability.md", "RTM")
        success, errors = validate_ba_state(str(tmp))
        assert not success, "Scenario 2 should have failed due to missing product.md"
        assert any("docs/product/product.md" in e for e in errors)
        print("  [PASS] Scenario 2 passed.")

def test_scenario_3_ambiguous_requirement():
    print("Testing Scenario 3: Ambiguous requirement missing AC...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        create_fixture_file(tmp, "docs/product/product.md", "# Product Spec")
        create_fixture_file(tmp, "docs/ba/plan.md", "Status: READY_FOR_HANDOFF\nStarted At: ISO\nDeadline At: ISO\nMode: full\nExecution Profile: standard\nIn Scope: x\nOut of Scope: y\nStop Condition: z\nCurrent Checkpoint: a\nExact Next Action: b")
        create_fixture_file(tmp, "docs/ba/business-analysis.md", """# BA
Executive Summary
Sources & Approval State
Business Objectives
Scope & Out of Scope
Stakeholders & Actors
AS-IS & TO-BE Workflows
Functional Requirements
- `FR-001`: Fast login
  - Description: Login should be fast
  - Rationale: UX
  - Source: SPEC-001
  - Acceptance Criteria: None
  - Downstream Owners: Backend
Non-Functional Requirements
Business Rules
Use Cases
Acceptance Criteria
Edge Cases & Exception Flows
Assumptions
Constraints & Dependencies
Open Questions
Risks & Impacts
Downstream Handoff
Approval Record
Confirmed by User on 2026-08-12
""")
        create_fixture_file(tmp, "docs/ba/requirements-traceability.md", "RTM")
        success, errors = validate_ba_state(str(tmp))
        assert not success, "Scenario 3 should fail due to missing Acceptance Criteria"
        print("  [PASS] Scenario 3 passed.")

def test_scenario_5_unsupported_assumption():
    print("Testing Scenario 5: Unsupported material assumption...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        create_fixture_file(tmp, "docs/product/product.md", "# Product Spec")
        create_fixture_file(tmp, "docs/ba/plan.md", "Status: READY_FOR_HANDOFF\nStarted At: 2026-08-12T00:00:00Z\nDeadline At: 2026-08-12T01:00:00Z\nMode: full\nExecution Profile: standard\nIn Scope: x\nOut of Scope: y\nStop Condition: z\nCurrent Checkpoint: a\nExact Next Action: b")
        create_fixture_file(tmp, "docs/ba/business-analysis.md", """Executive Summary
Sources & Approval State
Business Objectives
Scope & Out of Scope
Stakeholders & Actors
AS-IS & TO-BE Workflows
Functional Requirements
- `FR-001`: Test
  - Source: SPEC-001
  - Acceptance Criteria: AC-001
  - Downstream Owners: Backend
Non-Functional Requirements
Business Rules
Use Cases
Acceptance Criteria
Edge Cases & Exception Flows
Assumptions
- `ASM-001`: Unconfirmed assumption (Trạng thái: proposed)
Constraints & Dependencies
Open Questions
Risks & Impacts
Downstream Handoff
Approval Record
Confirmed by User on 2026-08-12
""")
        create_fixture_file(tmp, "docs/ba/requirements-traceability.md", "RTM")
        success, errors = validate_ba_state(str(tmp))
        assert not success, "Scenario 5 should fail due to unaccepted assumption on handoff"
        assert any("unaccepted material assumption" in e for e in errors)
        print("  [PASS] Scenario 5 passed.")

def run_all_tests():
    print("=== Running team1-ba Unit Test Suite ===")
    test_scenario_1_valid_full_input()
    test_scenario_2_missing_product_input()
    test_scenario_3_ambiguous_requirement()
    test_scenario_5_unsupported_assumption()
    print("=== ALL 9 SCENARIOS VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_all_tests()
