import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CandidateDetailPage } from "@/features/candidates/CandidateDetailPage";
import type { Candidate } from "@/types/recruitment";

const apiMocks = vi.hoisted(() => ({
    generateDraft: vi.fn(),
    getCandidate: vi.fn(),
    getEmailHistory: vi.fn(),
    getTemplates: vi.fn(),
    updateCandidate: vi.fn(),
}));

vi.mock("@/services/recruitmentApi", () => ({
    recruitmentApi: apiMocks,
}));

const candidate: Candidate = {
    id: 3,
    full_name: "Nguyen Minh An",
    email: "an.nguyen@example.com",
    phone: "0901000001",
    position: "Frontend Developer",
    stage: "CV_SCREENING",
    status: "PASS_CV",
    interview_time: null,
    interviewer: null,
    note: "Strong React profile",
    created_at: "2026-08-06T10:00:00+07:00",
    updated_at: "2026-08-06T10:00:00+07:00",
};

describe("CandidateDetailPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        apiMocks.getCandidate.mockResolvedValue(candidate);
        apiMocks.getEmailHistory.mockResolvedValue([]);
        apiMocks.updateCandidate.mockResolvedValue(candidate);
    });

    it("uses a controlled status select and submits an empty datetime as null", async () => {
        const queryClient = new QueryClient({
            defaultOptions: {
                mutations: { retry: false },
                queries: { retry: false },
            },
        });
        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter initialEntries={["/candidates/3"]}>
                    <Routes>
                        <Route path="/candidates/:candidateId" element={<CandidateDetailPage />} />
                    </Routes>
                </MemoryRouter>
            </QueryClientProvider>,
        );

        await screen.findByRole("heading", { name: "Nguyen Minh An" });
        expect(screen.getByRole("combobox", { name: "Status" })).toBeInTheDocument();
        expect(screen.queryByRole("textbox", { name: "Status" })).not.toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: "Save Changes" }));

        await waitFor(() => expect(apiMocks.updateCandidate).toHaveBeenCalledWith(candidate.id, expect.objectContaining({
            status: "PASS_CV",
            interview_time: null,
        })));
    });
});
