import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateDetailPage } from "@/features/candidates/CandidateDetailPage";
import type { Candidate, DraftRevision, SendOperation } from "@/types/recruitment";

const apiMocks = vi.hoisted(() => ({
    createDraft: vi.fn(),
    getCandidate: vi.fn(),
    getCandidateDrafts: vi.fn(),
    getSendOperations: vi.fn(),
    reviseDraft: vi.fn(),
    sendDraft: vi.fn(),
}));
vi.mock("@/services/recruitmentApi", () => ({ recruitmentApi: apiMocks }));

const candidate: Candidate = {
    id: 3, application_id: "APP-TEST-001", full_name: "Nguyen Minh An", email: "an@example.com",
    phone: null, position: "Frontend Developer", stage: "CV_SCREENING", status: "PASS_CV",
    status_updated_at: null, status_updated_by: null, interview_time: null, interviewer: null, note: null,
    created_at: "2026-08-06T03:00:00Z", updated_at: "2026-08-06T03:00:00Z",
};
const draft: DraftRevision = {
    id: "4a162a04-2449-4ea7-96b1-8277c5af5b29", candidate_id: 3, revision_number: 1,
    template_code: "INTERVIEW_INVITATION", stage: "CV_SCREENING", decision: "PASS_CV",
    to_email: "an@example.com", subject: "Interview invitation", decision_critical_content: "You passed CV screening.",
    editable_content: "Hello Nguyen Minh An", rendered_body: "You passed CV screening.\nHello Nguyen Minh An",
    status: "READY_TO_SEND", is_correction: false, correction_rationale: null, prior_operation_id: null,
    risk_check_result: { passed: true, issues: [] }, created_by: "demo_hr",
    created_at: "2026-08-06T03:05:00Z", updated_at: "2026-08-06T03:05:00Z",
};
const accepted: SendOperation = {
    id: "875e2f89-8f42-462d-9725-f095931dddaf", draft_revision_id: draft.id, operation_status: "PROVIDER_ACCEPTED",
    provider_name: "RESEND", provider_message_id: "email_123", final_outcome: "PROVIDER_ACCEPTED",
    failure_category: null, resolution_mode: "AUTOMATIC_SYNC", resolution_rationale: null, resolved_by: null,
    resolved_at: "2026-08-06T03:06:00Z", created_by: "demo_hr", created_at: "2026-08-06T03:06:00Z",
    updated_at: "2026-08-06T03:06:00Z", attempts: [],
};

describe("CandidateDetailPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        apiMocks.getCandidate.mockResolvedValue(candidate);
        apiMocks.getCandidateDrafts.mockResolvedValue({ items: [draft], total: 1, page: 1, page_size: 20, pages: 1 });
        apiMocks.getSendOperations.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100, pages: 1 });
        apiMocks.sendDraft.mockResolvedValue(accepted);
    });

    it("requires explicit confirmation before invoking a real send", async () => {
        const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
        render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/candidates/3"]}><Routes><Route element={<CandidateDetailPage />} path="/candidates/:candidateId" /></Routes></MemoryRouter></QueryClientProvider>);

        await screen.findByRole("heading", { name: "Nguyen Minh An" });
        expect(screen.getByText("You passed CV screening.")).toBeInTheDocument();
        await userEvent.click(screen.getByRole("button", { name: "Send Real Email" }));
        expect(apiMocks.sendDraft).not.toHaveBeenCalled();

        const dialog = await screen.findByRole("dialog", { name: "Send this email through Resend?" });
        await userEvent.click(within(dialog).getByRole("button", { name: "Send Real Email" }));
        await waitFor(() => expect(apiMocks.sendDraft).toHaveBeenCalledWith(draft.id));
    });
});
