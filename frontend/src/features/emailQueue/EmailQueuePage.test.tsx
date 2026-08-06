import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EmailQueuePage } from "@/features/emailQueue/EmailQueuePage";
import { useUiStore } from "@/stores/uiStore";
import type { AgentReviewResult, EmailQueueItem, RiskCheckResult } from "@/types/recruitment";

const apiMocks = vi.hoisted(() => ({
    approveEmailQueueItem: vi.fn(),
    cancelEmailQueueItem: vi.fn(),
    getEmailQueue: vi.fn(),
    getEmailQueueItem: vi.fn(),
    sendEmailQueueItem: vi.fn(),
    updateEmailQueue: vi.fn(),
}));

vi.mock("@/services/recruitmentApi", () => ({
    recruitmentApi: apiMocks,
}));

function completedReview(requiresHumanReview: boolean): AgentReviewResult {
    return {
        status: "completed",
        draft_subject: "Interview invitation",
        draft_body: "Hi Nguyen Minh An, your interview is at 10:24 (GMT+7).",
        issues: [],
        uncertainty: { has_uncertainty: false, reason: null },
        review_summary: "The draft matches the supplied candidate facts.",
        requires_human_review: requiresHumanReview,
        semantic_review_available: true,
        model_metadata: {
            provider: "gemini",
            model: "gemini-2.5-flash",
            prompt_version: "semantic_review.v1",
            skill_name: "recruitment-email-review",
            skill_version: "1.0.0",
            attempts: 1,
        },
        trace: [],
    };
}

function queueItem(overrides: Partial<EmailQueueItem> = {}): EmailQueueItem {
    const requiresHumanReview = overrides.requires_hr_approval ?? false;
    const review = completedReview(requiresHumanReview);
    const risk: RiskCheckResult = {
        passed: true,
        issues: [],
        requires_human_review: requiresHumanReview,
        agent_review: review,
        draft_version: 1,
        content_hash: "hash-v1",
        async_review: {
            status: "COMPLETED",
            draft_version: 1,
            review_version: 1,
            content_hash: "hash-v1",
        },
    };

    return {
        id: 7,
        candidate_id: 3,
        email_type: "INTERVIEW_INVITATION",
        to_email: "an.nguyen@example.com",
        subject: review.draft_subject,
        body: review.draft_body,
        status: "DRAFT",
        requires_hr_approval: false,
        risk_check_result: risk,
        created_by: "demo_hr",
        approved_by: null,
        sent_at: null,
        created_at: "2026-08-06T10:00:00+07:00",
        updated_at: "2026-08-06T10:00:00+07:00",
        candidate: {
            id: 3,
            full_name: "Nguyen Minh An",
            email: "an.nguyen@example.com",
            phone: null,
            position: "Frontend Developer",
            stage: "CV_SCREENING",
            status: "PASS_CV",
            status_updated_at: null,
            status_updated_by: null,
            interview_time: "2026-08-08T10:24:00+07:00",
            interviewer: "Linh Tran",
            note: null,
            created_at: "2026-08-06T10:00:00+07:00",
            updated_at: "2026-08-06T10:00:00+07:00",
        },
        ...overrides,
    };
}

function renderWithQueryClient(children: ReactNode) {
    const queryClient = new QueryClient({
        defaultOptions: {
            mutations: { retry: false },
            queries: { retry: false },
        },
    });

    return render(
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>,
    );
}

async function openReview() {
    await screen.findByText("Nguyen Minh An");
    await userEvent.click(screen.getByRole("button", { name: "Open review" }));
    return screen.findByRole("dialog", { name: "Review email draft" });
}

describe("EmailQueuePage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useUiStore.setState({ toast: null });
    });

    it("invalidates the displayed review and disables approval after HR edits the draft", async () => {
        const item = queueItem({
            email_type: "REJECTION_AFTER_CV",
            requires_hr_approval: true,
            status: "PENDING_APPROVAL",
        });
        apiMocks.getEmailQueue.mockResolvedValue([item]);

        renderWithQueryClient(<EmailQueuePage />);
        const drawer = await openReview();
        const subjectInput = within(drawer).getByLabelText("Subject");
        const approveButton = within(drawer).getByRole("button", { name: "Approve" });

        expect(approveButton).toBeEnabled();
        expect(within(drawer).queryByRole("button", { name: "Simulate send" })).not.toBeInTheDocument();

        await userEvent.clear(subjectInput);
        await userEvent.type(subjectInput, "Updated rejection subject");

        expect(within(drawer).getByText(/Unsaved changes\. Save the draft/)).toBeInTheDocument();
        expect(within(drawer).getByRole("heading", { name: "Unsaved changes need review" })).toBeInTheDocument();
        expect(approveButton).toBeDisabled();
        expect(within(drawer).getByRole("button", { name: "Save draft" })).toBeEnabled();
        expect(within(drawer).queryByRole("button", { name: "Refresh review" })).not.toBeInTheDocument();
    });

    it("saves edited content before workflow actions become available again", async () => {
        const item = queueItem();
        const savedItem = queueItem({
            subject: "Updated interview subject",
            risk_check_result: {
                passed: true,
                issues: [],
                draft_version: 2,
                content_hash: "hash-v2",
                async_review: {
                    status: "QUEUED",
                    draft_version: 2,
                    content_hash: "hash-v2",
                },
            },
        });
        apiMocks.getEmailQueue.mockResolvedValue([item]);
        apiMocks.updateEmailQueue.mockResolvedValue(savedItem);

        renderWithQueryClient(<EmailQueuePage />);
        const drawer = await openReview();
        const subjectInput = within(drawer).getByLabelText("Subject");

        await userEvent.clear(subjectInput);
        await userEvent.type(subjectInput, savedItem.subject);
        await userEvent.click(within(drawer).getByRole("button", { name: "Save draft" }));

        await waitFor(() => {
            expect(apiMocks.updateEmailQueue).toHaveBeenCalledWith(item.id, {
                subject: savedItem.subject,
                body: item.body,
            });
        });
        await waitFor(() => expect(within(drawer).getByRole("heading", { name: "Draft saved – review queued" })).toBeInTheDocument());
        expect(within(drawer).getByRole("button", { name: "Approve" })).toBeDisabled();
        expect(within(drawer).getByRole("button", { name: "Simulate send" })).toBeDisabled();
        expect(useUiStore.getState().toast?.message).toBe("Draft saved – review queued");
    });

    it("requires explicit confirmation and records only a send simulation", async () => {
        const item = queueItem();
        apiMocks.getEmailQueue.mockResolvedValue([item]);
        apiMocks.sendEmailQueueItem.mockResolvedValue(queueItem({ status: "SENT" }));

        renderWithQueryClient(<EmailQueuePage />);
        const drawer = await openReview();

        await userEvent.click(within(drawer).getByRole("button", { name: "Simulate send" }));
        const confirmation = await screen.findByRole("dialog", { name: "Simulate sending this email?" });
        expect(within(confirmation).getByText(/No real email will be delivered/)).toBeInTheDocument();

        await userEvent.click(within(confirmation).getByRole("button", { name: "Run simulation" }));
        await waitFor(() => expect(apiMocks.sendEmailQueueItem).toHaveBeenCalledWith(item.id));
    });

    it("keeps sent items read-only", async () => {
        const item = queueItem({
            status: "SENT",
            sent_at: "2026-08-06T12:00:00+07:00",
        });
        apiMocks.getEmailQueue.mockResolvedValue([item]);

        renderWithQueryClient(<EmailQueuePage />);
        const drawer = await openReview();

        expect(within(drawer).getByLabelText("Subject")).toBeDisabled();
        expect(within(drawer).getByLabelText("Body")).toBeDisabled();
        expect(within(drawer).queryByRole("button", { name: "Save draft" })).not.toBeInTheDocument();
        expect(within(drawer).queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
        expect(within(drawer).queryByRole("button", { name: "Simulate send" })).not.toBeInTheDocument();
        expect(within(drawer).queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
        expect(within(drawer).getByText(/closed and available for review only/)).toBeInTheDocument();
    });

    it("polls a queued draft and unlocks actions only after the matching review completes", async () => {
        const item = queueItem({
            risk_check_result: {
                passed: true,
                issues: [],
                draft_version: 2,
                content_hash: "hash-v2",
                async_review: {
                    status: "QUEUED",
                    draft_version: 2,
                    content_hash: "hash-v2",
                },
            },
        });
        const refreshedItem = queueItem({
            updated_at: "2026-08-06T11:00:00+07:00",
            risk_check_result: {
                passed: true,
                issues: [],
                agent_review: completedReview(false),
                draft_version: 2,
                content_hash: "hash-v2",
                async_review: {
                    status: "COMPLETED",
                    draft_version: 2,
                    review_version: 2,
                    content_hash: "hash-v2",
                },
            },
        });
        let resolvePoll!: (item: EmailQueueItem) => void;
        const pollResponse = new Promise<EmailQueueItem>((resolve) => {
            resolvePoll = resolve;
        });
        apiMocks.getEmailQueue.mockResolvedValue([item]);
        apiMocks.getEmailQueueItem.mockReturnValue(pollResponse);

        renderWithQueryClient(<EmailQueuePage />);
        const drawer = await openReview();

        expect(within(drawer).getByRole("button", { name: "Approve" })).toBeDisabled();
        expect(within(drawer).getByRole("button", { name: "Simulate send" })).toBeDisabled();
        await waitFor(() => expect(apiMocks.getEmailQueueItem).toHaveBeenCalledWith(item.id));
        resolvePoll(refreshedItem);
        await waitFor(() => expect(within(drawer).getByRole("button", { name: "Approve" })).toBeEnabled());
        expect(within(drawer).getByRole("button", { name: "Simulate send" })).toBeEnabled();
    });
});
