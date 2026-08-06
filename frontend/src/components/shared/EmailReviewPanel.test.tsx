import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EmailReviewPanel, ReviewStatusBadge } from "@/components/shared/EmailReviewPanel";
import type { AgentReviewResult, RiskCheckResult } from "@/types/recruitment";

const currentDraft = {
    body: "Hi Nguyen Minh An, your interview is at 10:24.",
    subject: "Interview invitation",
};

function completedReview(overrides: Partial<AgentReviewResult> = {}): AgentReviewResult {
    return {
        status: "completed",
        draft_subject: currentDraft.subject,
        draft_body: currentDraft.body,
        issues: [],
        uncertainty: { has_uncertainty: false, reason: null },
        review_summary: "The draft is consistent with the supplied candidate facts.",
        requires_human_review: false,
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
        ...overrides,
    };
}

function riskResult(agentReview = completedReview()): RiskCheckResult {
    return {
        passed: true,
        issues: [],
        checked_at: "2026-08-06T10:35:07+07:00",
        requires_human_review: agentReview.requires_human_review,
        agent_review: agentReview,
    };
}

describe("EmailReviewPanel", () => {
    it("shows a completed safe review with no HR checkpoint", () => {
        render(
            <EmailReviewPanel
                currentBody={currentDraft.body}
                currentSubject={currentDraft.subject}
                riskResult={riskResult()}
            />,
        );

        expect(screen.getByRole("heading", { name: "Ready for the next step" })).toBeInTheDocument();
        expect(screen.getByText("Completed")).toBeInTheDocument();
        expect(screen.getByText("Not required")).toBeInTheDocument();
        expect(screen.getByText("The draft is consistent with the supplied candidate facts.")).toBeInTheDocument();
    });

    it("keeps a deterministic blocker final and displays remediation", () => {
        const blockedResult: RiskCheckResult = {
            passed: false,
            issues: [{
                rule_id: "RECIPIENT_EMAIL_REQUIRED",
                severity: "blocker",
                message: "Candidate email is missing.",
                evidence: { candidate_id: 10 },
                remediation: "Add a verified recipient email before generating a draft.",
                is_blocking: true,
                source: "deterministic",
            }],
            requires_human_review: true,
        };

        render(
            <EmailReviewPanel
                currentBody={currentDraft.body}
                currentSubject={currentDraft.subject}
                riskResult={blockedResult}
            />,
        );

        expect(screen.getByRole("heading", { name: "Blocked by a safety rule" })).toBeInTheDocument();
        expect(screen.getByText("Candidate email is missing.")).toBeInTheDocument();
        expect(screen.getByText(/Add a verified recipient email/)).toBeInTheDocument();
        expect(screen.getByText("Blocked", { selector: "p" })).toBeInTheDocument();
    });

    it("shows uncertainty and lets HR copy advisory wording", async () => {
        const user = userEvent.setup();
        const onApplySuggestion = vi.fn();
        const suggestedSubject = "Interview invitation - Vietnam time";
        const suggestedBody = "Hi Nguyen Minh An, your interview is at 10:24 (GMT+7).";
        const review = completedReview({
            draft_subject: suggestedSubject,
            draft_body: suggestedBody,
            issues: [{
                rule_id: "AI_AMBIGUOUS_INFORMATION",
                severity: "warning",
                message: "The interview time omits its timezone.",
                evidence: "Candidate data contains +07:00 but the draft does not.",
                requires_human_review: true,
            }],
            uncertainty: {
                has_uncertainty: true,
                reason: "The recipient may interpret the interview time in another timezone.",
            },
            requires_human_review: true,
        });

        render(
            <EmailReviewPanel
                currentBody={currentDraft.body}
                currentSubject={currentDraft.subject}
                onApplySuggestion={onApplySuggestion}
                riskResult={riskResult(review)}
            />,
        );

        expect(screen.getByRole("heading", { name: "Waiting for HR review" })).toBeInTheDocument();
        expect(screen.getByText("Uncertainty detected")).toBeInTheDocument();
        expect(screen.getByText("Ambiguous Information")).toBeInTheDocument();
        await user.click(screen.getByRole("button", { name: "Use suggested wording" }));
        expect(onApplySuggestion).toHaveBeenCalledWith(suggestedSubject, suggestedBody);
    });

    it("marks edited content stale and hides the previous suggestion", () => {
        const review = completedReview({
            draft_subject: "Old AI suggestion",
            draft_body: "Old suggested body",
        });

        render(
            <EmailReviewPanel
                currentBody="Locally edited body"
                currentSubject="Locally edited subject"
                isStale
                onRequestReview={vi.fn()}
                riskResult={riskResult(review)}
            />,
        );

        expect(screen.getByRole("heading", { name: "Unsaved changes need review" })).toBeInTheDocument();
        expect(screen.getByText("Save to re-check")).toBeInTheDocument();
        expect(screen.queryByText("Old AI suggestion")).not.toBeInTheDocument();
    });

    it("surfaces provider unavailability as a human-review state", () => {
        const review = completedReview({
            status: "unavailable",
            review_summary: "Gemini semantic review is temporarily unavailable.",
            requires_human_review: true,
            semantic_review_available: false,
        });

        render(
            <>
                <EmailReviewPanel
                    currentBody={currentDraft.body}
                    currentSubject={currentDraft.subject}
                    riskResult={riskResult(review)}
                />
                <ReviewStatusBadge riskResult={riskResult(review)} />
            </>,
        );

        expect(screen.getByRole("heading", { name: "Human review required" })).toBeInTheDocument();
        expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
        expect(screen.getByText("AI unavailable")).toBeInTheDocument();
    });

    it("shows queue, draft, and review versions in technical details", async () => {
        const result: RiskCheckResult = {
            ...riskResult(),
            draft_version: 4,
            content_hash: "hash-v4",
            async_review: {
                status: "COMPLETED",
                draft_version: 4,
                review_version: 4,
                content_hash: "hash-v4",
            },
        };

        render(
            <EmailReviewPanel
                currentBody={currentDraft.body}
                currentSubject={currentDraft.subject}
                queueId={27}
                riskResult={result}
            />,
        );

        await userEvent.click(screen.getByText("Technical review details"));
        expect(screen.getByText("#27")).toBeInTheDocument();
        expect(screen.getByText("Draft version").nextElementSibling).toHaveTextContent("4");
        expect(screen.getByText("Review version").nextElementSibling).toHaveTextContent("4");
    });
});
