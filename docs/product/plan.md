# Product Plan & Checkpoint

- **Mode**: scope-audit
- **Execution Profile**: standard
- **Started At**: 2026-08-17T00:10:00+07:00
- **Deadline At**: 2026-08-17T00:55:00+07:00
- **Status**: APPROVED_FOR_DELIVERY

## 1. Scope & Boundaries

- **In Scope**: Minimal Real-Email MVP for one candidate at a time; deterministic safety checks; fixed templates; draft revisioning; explicit HR inspection and Send confirmation; Resend provider integration; idempotent Logical Send Operation; delivery outcome reconciliation; decision correction; immutable audit trail.
- **Out of Scope**: Batch or automatic sending, campaigns, bounce tracking, AI hiring decisions, CV screening, LLM blocking the send path, custom template CRUD, multi-level approval, and automatic retry from `DELIVERY_UNKNOWN`.
- **Stop Condition**: Product scope audit passes, BA requirements remain traceable, and the approved baseline is handed to the existing architecture/database/backend delivery plans.

## 2. Input Inventory & Fingerprints

| Input Source | Type | Approval State | Fingerprint (SHA-256) | Last Checked | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `docs/product/product.md` | Product Spec | APPROVED | `316e189df41671e629c9c370a03f39b2068b422dc8d6682a5e3ae0c1707246c7` | 2026-08-17 | valid |
| `docs/ba/business-analysis.md` | BA Spec | APPROVED | `d425d5f0de918d0261974906122dada3834be70cf5ee14bf1041e833eeef97ab` | 2026-08-17 | valid |
| `docs/ba/requirements-traceability.md` | BA RTM | APPROVED | `1926a124ca2918fc4754bc681237105c410773e7f793f9fd2f6d347636ce00b3` | 2026-08-17 | valid |
| `AGENTS.md` | Repository Guidance | CONTRADICTORY | Not canonical product input | 2026-08-17 | downstream gap |
| `README.md` | Runtime Documentation | STALE | Not canonical product input | 2026-08-17 | downstream gap |

## 3. Work Items & Progress

- [x] Inspect inputs and select scope-audit mode
- [x] Confirm primary user, pain point, core job, goals, and non-goals remain unchanged
- [x] Treat the user's 2026-08-17 real-email instruction as explicit confirmation of `DEC-001`
- [x] Verify every MVP capability remains linked to `PROB-001` and `JOB-001`
- [x] Confirm BA reconciliation is complete and no capability is `UNDECIDED`
- [x] Classify runtime/documentation conflicts as downstream implementation gaps
- [x] Record scope decisions in `docs/product/scope-register.md`
- [x] Prepare BA gap-analysis handoff
- [x] Run Product state validation

## 4. Key Decisions & Open Questions

- **DEC-001 Reconfirmed**: The MVP sends real, single-candidate recruitment email through the approved provider boundary after deterministic checks and explicit HR confirmation.
- **DEC-004 Reconfirmed**: One Logical Send Operation per Draft Revision; retries reuse operation identity; `DELIVERY_UNKNOWN` never auto-retries.
- **DEC-005 Reconfirmed**: Fixed templates are MVP. Legacy template CRUD is compatibility-only and must not drive the target workflow.
- **Open Questions**: None blocking delivery. Provider credentials remain an environment/deployment dependency and must never be committed.

## 5. Checkpoint & Exact Next Action

- **Current Checkpoint**: Product scope audit completed. User explicitly reconfirmed real-email delivery on 2026-08-17. Product and BA baselines already describe the same scope; contradictory repository guidance and legacy runtime are downstream gaps, not product ambiguity.
- **Exact Next Action**: Execute BA gap-analysis handoff, then resume backend delivery at `SLICE-011` without expanding into batch sending, AI decisions, or automatic unknown-state retry.
