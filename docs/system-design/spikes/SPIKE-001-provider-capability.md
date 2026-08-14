# SPIKE-001: Technical Spike — Email Provider API Capability Investigation

- **Status**: COMPLETED (Selected Provider: Resend)
- **Created Date**: 2026-08-12
- **Completed Date**: 2026-08-12
- **Author**: Principal System Software Architect
- **Target Component**: Email Provider Adapter (`provider_adapter.py`)

## 1. Objective & Scope

This technical spike investigated official candidate Email Provider APIs (Resend, SendGrid, Postmark) to evaluate provider capabilities required by Product Specification (`DEC-004`) and Business Analysis Specification (`FR-006`, `FR-007`, `ADI-001`).

Specifically, the spike evaluated:
1. Synchronous REST API payload structure and response mapping.
2. Support for outbound custom HTTP request deduplication headers (`Idempotency-Key`).
3. Status lookup and provider-backed idempotent reconciliation mechanisms for `DELIVERY_UNKNOWN` recovery.
4. Setup complexity, sender domain verification, demo limitations, and free-tier quotas.

## 2. Comparative Provider Analysis

Research performed using official provider documentation:
- **Resend Official API**: [Resend Email API Documentation](https://resend.com/docs/api-reference/emails/send-email)
- **SendGrid Official API**: [SendGrid v3 Mail Send API Documentation](https://docs.sendgrid.com/api-reference/mail-send/mail-send)
- **Postmark Official API**: [Postmark Send Email API Documentation](https://postmarkapp.com/developer/user-guide/send-email-with-api)

### Provider Comparison Matrix

| Evaluation Criterion | Resend (Selected) | SendGrid | Postmark |
| :--- | :--- | :--- | :--- |
| **API Type & SDK** | REST API, Official Python SDK (`resend`) | REST API v3, SDK (`sendgrid`) | REST API, SDK (`postmark`) |
| **Sync Acceptance Response** | HTTP 200/201 returning `{ "id": "msg_..." }` | HTTP 202 Accepted (empty body) | HTTP 200 OK returning `{ "MessageID": "..." }` |
| **Native Idempotency Header** | **Supported** (`Idempotency-Key`, 24h retention) | Not supported on REST POST | Not supported on REST POST |
| **Status Lookup API** | GET `/emails/{id}` (Requires known email `id`) | Event Webhook / Activity Feed (paid) | GET `/messages/outbound/{id}/details` |
| **Unknown Timeout Reconciliation** | Provider-backed idempotent replay within 24h | Potential duplicate send on client retry | Potential duplicate send on client retry |
| **Demo & Testing Limits** | `onboarding@resend.dev` (registered email only) | Requires domain verification | Requires domain verification |
| **Free Tier Quota** | 3,000 emails/month (100 emails/day) | 100 emails/day | 100 emails developer sandbox |

## 3. Resend Technical Findings & Demo Limitations

### A. Idempotent Replay & Reconciliation Mechanics
1. **Status Query by Email ID**: Resend provides GET `/emails/{id}` to fetch delivery details. However, if an outbound HTTP POST times out during Phase B before receiving a response, the system does NOT know the Resend `{id}`. Resend GET endpoint does NOT support querying by `operation_id` or custom header.
2. **Provider-Backed Idempotent Replay (Within 24 Hours)**: When in `DELIVERY_UNKNOWN` state following a Phase B timeout, the system executes reconciliation by re-transmitting the EXACT SAME payload with the EXACT SAME `Idempotency-Key` (which is `operation_id`). Within Resend's 24-hour retention window, Resend recognizes the key and returns the cached response (containing the original `{id}` and status) without delivering a second email. This is a **provider-backed idempotent reconciliation**, NOT a blind retry.
3. **Expired Retention Window (> 24 Hours)**: After 24 hours, Resend's idempotency key cache expires. Re-transmitting would risk creating a duplicate email. Therefore, automatic or automated replay is strictly PROHIBITED after 24 hours; the system retains `DELIVERY_UNKNOWN` state and requires HR manual resolution (`ADR-004`).

### B. Resend Demo & Environment Restrictions
1. **Unverified Sender Domain**: The default test sender `onboarding@resend.dev` can ONLY deliver emails to the single email address registered with the Resend account.
2. **Multi-Recipient / Mentor Demo**: Sending real emails to mentors or alternative candidate addresses requires verifying a custom domain via DNS (DKIM and SPF records).
3. **Simulation Addresses**: Resend provides magic test addresses `delivered@resend.dev` and `bounced@resend.dev` to simulate delivery and bounce events during integration testing.
4. **Quota Guard**: Free tier allows 3,000 emails/month (100 emails/day). The backend application must configure a client-side quota guard to prevent rate-limit errors.

## 4. Handoff to Architecture

- `ADR-002`, `ADR-003`, `ADR-004` updated with exact 3-Phase transaction boundary, provider-backed idempotent replay within 24h, and demo limitations.
- Downstream owner for `provider_adapter.py`: Backend.
