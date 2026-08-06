import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateQuickActions } from "@/features/candidates/CandidateQuickActions";
import { useUiStore } from "@/stores/uiStore";
import type { Candidate } from "@/types/recruitment";

const apiMocks = vi.hoisted(() => ({
    updateCandidate: vi.fn(),
}));

vi.mock("@/services/recruitmentApi", () => ({
    recruitmentApi: apiMocks,
}));

const candidate: Candidate = {
    id: 3,
    full_name: "Nguyen Minh An",
    email: "an.nguyen@example.com",
    phone: null,
    position: "Frontend Developer",
    stage: "CV_SCREENING",
    status: "PASS_CV",
    status_updated_at: null,
    status_updated_by: null,
    interview_time: null,
    interviewer: null,
    note: null,
    created_at: "2026-08-06T10:00:00+07:00",
    updated_at: "2026-08-06T10:00:00+07:00",
};

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

describe("CandidateQuickActions", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useUiStore.setState({ toast: null });
    });

    it("updates status through an explicit dialog mutation", async () => {
        apiMocks.updateCandidate.mockResolvedValue({ ...candidate, status: "PASS_INTERVIEW" });
        renderWithQueryClient(<CandidateQuickActions candidate={candidate} onGenerateDraft={vi.fn()} />);

        await userEvent.click(screen.getByRole("button", { name: "Update Status" }));
        const dialog = await screen.findByRole("dialog", { name: "Update Candidate Status" });
        await userEvent.click(within(dialog).getByLabelText("Status"));
        await userEvent.click(screen.getByRole("option", { name: "PASS_INTERVIEW" }));
        await userEvent.click(within(dialog).getByRole("button", { name: "Update Status" }));

        await waitFor(() => expect(apiMocks.updateCandidate).toHaveBeenCalledWith(candidate.id, {
            status: "PASS_INTERVIEW",
        }));
        expect(useUiStore.getState().toast?.message).toBe("Candidate status updated");
    });

    it("schedules an interview with interviewer, time, and INTERVIEW stage", async () => {
        const localInterviewTime = "2026-08-10T09:30";
        const expectedInterviewTime = new Date(localInterviewTime).toISOString();
        apiMocks.updateCandidate.mockResolvedValue({
            ...candidate,
            stage: "INTERVIEW",
            interviewer: "Linh Tran",
            interview_time: expectedInterviewTime,
        });
        renderWithQueryClient(<CandidateQuickActions candidate={candidate} onGenerateDraft={vi.fn()} />);

        await userEvent.click(screen.getByRole("button", { name: "Schedule Interview" }));
        const dialog = await screen.findByRole("dialog", { name: "Schedule Interview" });
        await userEvent.type(within(dialog).getByLabelText("Interviewer"), "Linh Tran");
        fireEvent.change(within(dialog).getByLabelText("Interview Time"), {
            target: { value: localInterviewTime },
        });
        await userEvent.click(within(dialog).getByRole("button", { name: "Schedule Interview" }));

        await waitFor(() => expect(apiMocks.updateCandidate).toHaveBeenCalledWith(candidate.id, {
            interviewer: "Linh Tran",
            interview_time: expectedInterviewTime,
            stage: "INTERVIEW",
        }));
        expect(useUiStore.getState().toast?.message).toBe("Interview scheduled");
    });
});
