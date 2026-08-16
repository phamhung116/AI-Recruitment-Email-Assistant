# Recruitment Mail Guard UI Specification

Status: APPROVED  
Updated: 2026-08-17

## Visual System

Preserve the existing HiLab enterprise SaaS shell, responsive sidebar/topbar, typography, spacing, tables, drawers, dialogs, loading, empty, error and toast patterns. Use the approved HiLab primary `#fb2c36`, accent `#fac800`, neutral gray tokens, and unchanged semantic status colors. No marketing layout, gradients, decorative effects or visual redesign is included.

## MVP Navigation

- Dashboard: summary of candidates and real send operation states.
- Candidates: paginated searchable/filterable applications and Excel import preview/confirmation.
- Candidate Detail: candidate context, immutable draft generation/revision, deterministic safety result, explicit real-send confirmation, and correction entry point.
- Email Operations: operational list/detail for provider accepted, definitive failure, delivery unknown, retry, reconcile and manual resolution.
- Audit Logs: paginated immutable event timeline.

Fixed templates remain system-owned and are shown only as draft metadata/preview. Template CRUD, simulation queue, Gemini review, batch send, bulk status mutation and bulk delete are not part of the approved real-email MVP.

## Safety Interactions

- Real send always opens a confirmation dialog naming the candidate/application and warning that a real email will be delivered.
- Decision-critical content is read-only; only subject and editable content can produce a new revision.
- `DELIVERY_UNKNOWN` shows high-visibility guidance and blocks normal send.
- Reconcile explains the 24-hour same-idempotency replay path.
- Manual resolution requires choice, rationale and warning acknowledgement.
- Provider accepted is labelled as accepted by provider, never guaranteed delivered.

## Responsive And Accessibility

Desktop is primary; tablet and mobile remain usable. Tables retain horizontal scrolling. Dialogs/drawers must trap and restore focus correctly, controls have accessible labels, semantic colors retain text labels, and all routes include loading, empty and error states.
