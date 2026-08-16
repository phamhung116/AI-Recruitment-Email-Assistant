# Team1 Frontend Route Map

## Routes

| Route | Page/View | Components | Data Source | Auth/Permission | UI Spec Source | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/` | Dashboard | KPI cards, status charts, recent activity | candidates, operations, audit v1 | internal/local | dashboard | completed |
| `/candidates` | Candidates | filters, import review, data table, pagination | candidates v1 | internal/local | candidates | completed |
| `/candidates/:candidateId` | Candidate and drafts | profile, revision editor, send confirmation | candidate/drafts/operations v1 | explicit confirmation | candidate detail | completed |
| `/email-operations` | Email Operations | filters, operation table, detail drawer, recovery actions | send operations v1 | governed actions | operations | completed |
| `/audit-logs` | Audit Logs | filters, audit table | audit logs v1 | internal/local | audit | completed |

## Navigation

| From | To | Trigger | Guard/Condition | Notes |
| --- | --- | --- | --- | --- |
| Global sidebar | any top-level route | menu item | none | collapsible desktop and mobile drawer |
| Dashboard | candidates/operations | KPI or activity link | none | preserves enterprise shell |
| Candidates | candidate detail | row click | candidate ID exists | row controls stop propagation where needed |
| Candidate detail | real send | confirm dialog | draft is sendable and confirmation checked | no API call before confirmation |
| Email Operations | operation recovery | drawer action | status-specific eligibility | retry, reconcile and manual resolution are separate |

## State Ownership

| State | Owner | Persistence | Source | Notes |
| --- | --- | --- | --- | --- |
| Server resources | TanStack Query | query cache | canonical `/api/v1` API | invalidated after mutations |
| HTTP configuration | Axios client | process lifetime | `VITE_API_BASE_URL` | standardized error envelope |
| Sidebar/UI preferences | Zustand/layout state | browser session | frontend | no business state stored here |
| Forms and validation | React Hook Form + Zod | component lifetime | UI and API schemas | validates before mutation |
| Import file/review | Candidates page/dialog | component lifetime | local file and preview API | import only after review |
| Confirmation/recovery input | dialog/drawer | component lifetime | HR input | rationale and acknowledgement are explicit |
