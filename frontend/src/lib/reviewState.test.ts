import { describe, expect, it } from "vitest";

import { getAsyncReviewStatus, isCurrentReviewCompleted, isReviewInProgress } from "@/lib/reviewState";
import type { AsyncReviewStatus, RiskCheckResult } from "@/types/recruitment";

function riskWithStatus(status: AsyncReviewStatus): RiskCheckResult {
    return {
        draft_version: 3,
        content_hash: "hash-v3",
        async_review: {
            status,
            draft_version: 3,
            review_version: status === "COMPLETED" ? 3 : undefined,
            content_hash: "hash-v3",
        },
    };
}

describe("async review state", () => {
    it.each(["QUEUED", "REVIEWING", "COMPLETED", "UNAVAILABLE", "FAILED", "STALE"] as const)(
        "recognizes %s",
        (status) => expect(getAsyncReviewStatus(riskWithStatus(status))).toBe(status),
    );

    it("polls only queued and reviewing states", () => {
        expect(isReviewInProgress(riskWithStatus("QUEUED"))).toBe(true);
        expect(isReviewInProgress(riskWithStatus("REVIEWING"))).toBe(true);
        expect(isReviewInProgress(riskWithStatus("COMPLETED"))).toBe(false);
    });

    it("requires a completed review for the exact draft version", () => {
        expect(isCurrentReviewCompleted(riskWithStatus("COMPLETED"))).toBe(true);
        expect(isCurrentReviewCompleted({
            ...riskWithStatus("COMPLETED"),
            draft_version: 4,
        })).toBe(false);
        expect(isCurrentReviewCompleted(riskWithStatus("STALE"))).toBe(false);
    });
});
