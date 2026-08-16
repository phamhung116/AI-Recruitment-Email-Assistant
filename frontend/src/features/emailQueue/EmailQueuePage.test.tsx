import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EmailQueuePage } from "@/features/emailQueue/EmailQueuePage";
import type { Candidate, DraftRevision, SendOperation } from "@/types/recruitment";

const apiMocks = vi.hoisted(() => ({
    getCandidate: vi.fn(), getDraft: vi.fn(), getSendOperations: vi.fn(),
    reconcileSendOperation: vi.fn(), resolveSendOperation: vi.fn(), retrySendOperation: vi.fn(),
}));
vi.mock("@/services/recruitmentApi", () => ({ recruitmentApi: apiMocks }));

const operation: SendOperation = {
    id: "875e2f89-8f42-462d-9725-f095931dddaf", draft_revision_id: "4a162a04-2449-4ea7-96b1-8277c5af5b29",
    operation_status: "DELIVERY_UNKNOWN", provider_name: "RESEND", provider_message_id: null,
    final_outcome: "DELIVERY_UNKNOWN", failure_category: null, resolution_mode: null, resolution_rationale: null,
    resolved_by: null, resolved_at: null, created_by: "demo_hr", created_at: "2026-08-06T03:00:00Z",
    updated_at: "2026-08-06T03:00:00Z", attempts: [{ id: "f9c79bc7-e589-43b9-a48b-505079371614", attempt_number: 1, attempt_status: "UNCONFIRMED_TIMEOUT", http_status_code: null, provider_message_id: null, error_code: "PROVIDER_RESPONSE_UNKNOWN", error_message: "Verify provider status before retrying.", latency_ms: 10000, initiated_at: "2026-08-06T03:00:00Z", completed_at: "2026-08-06T03:00:10Z" }],
};
const draft = { id: operation.draft_revision_id, candidate_id: 3, revision_number: 1, template_code: "INTERVIEW_INVITATION", stage: "CV_SCREENING", decision: "PASS_CV", to_email: "an@example.com", subject: "Interview", decision_critical_content: "Passed CV.", editable_content: "Hello", rendered_body: "Passed CV. Hello", status: "FINALIZED", is_correction: false, correction_rationale: null, prior_operation_id: null, risk_check_result: { passed: true }, created_by: "demo_hr", created_at: operation.created_at, updated_at: operation.updated_at } satisfies DraftRevision;
const candidate = { id: 3, application_id: "APP-TEST-003", full_name: "Nguyen Minh An", email: "an@example.com", phone: null, position: "Engineer", stage: "CV_SCREENING", status: "PASS_CV", status_updated_at: null, status_updated_by: null, interview_time: null, interviewer: null, note: null, created_at: operation.created_at, updated_at: operation.updated_at } satisfies Candidate;

describe("EmailQueuePage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        apiMocks.getSendOperations.mockResolvedValue({ items: [operation], total: 1, page: 1, page_size: 20, pages: 1 });
        apiMocks.getDraft.mockResolvedValue(draft);
        apiMocks.getCandidate.mockResolvedValue(candidate);
        apiMocks.reconcileSendOperation.mockResolvedValue({ ...operation, operation_status: "PROVIDER_ACCEPTED" });
    });

    it("warns on delivery unknown and confirms same-operation reconciliation", async () => {
        const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
        render(<QueryClientProvider client={client}><EmailQueuePage /></QueryClientProvider>);
        await screen.findByText("DELIVERY_UNKNOWN");
        await userEvent.click(screen.getByRole("button", { name: "Open operation" }));
        const drawer = await screen.findByRole("dialog", { name: "Send operation detail" });
        expect(within(drawer).getByText("Do not create another send.", { exact: false })).toBeInTheDocument();
        await userEvent.click(within(drawer).getByRole("button", { name: "Reconcile with Provider" }));
        const confirm = await screen.findByRole("dialog", { name: "Reconcile delivery status?" });
        await userEvent.click(within(confirm).getByRole("button", { name: "Reconcile" }));
        await waitFor(() => expect(apiMocks.reconcileSendOperation).toHaveBeenCalledWith(operation.id));
    });
});
