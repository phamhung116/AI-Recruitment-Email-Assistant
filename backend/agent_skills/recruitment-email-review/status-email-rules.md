# Status And Email Rules

These mappings are explicit demo policy. Unknown statuses are unsupported and must not be interpreted by the agent.

| Candidate status | Allowed email type |
| --- | --- |
| `PENDING` | None |
| `PASS_CV` | `INTERVIEW_INVITATION` |
| `REJECT_CV` | `REJECTION_AFTER_CV` |
| `INTERVIEW_CONFIRMED` | `INTERVIEW_REMINDER` |
| `PASS_INTERVIEW` | `OFFER_EMAIL` |
| `REJECT_INTERVIEW` | `REJECTION_AFTER_INTERVIEW` |
| `OFFER_ACCEPTED` | `ONBOARDING_EMAIL` |

Sensitive email types:

- `REJECTION_AFTER_CV`
- `REJECTION_AFTER_INTERVIEW`
- `OFFER_EMAIL`

Sensitive drafts always require explicit HR approval. The agent may explain this requirement but cannot grant approval.
