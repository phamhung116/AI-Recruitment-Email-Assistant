import type { AsyncReviewMetadata, AsyncReviewStatus, RiskCheckResult } from "@/types/recruitment";

const REVIEW_STATUSES = new Set<AsyncReviewStatus>([
    "QUEUED",
    "REVIEWING",
    "COMPLETED",
    "UNAVAILABLE",
    "FAILED",
    "STALE",
]);

export function getAsyncReviewMetadata(riskResult: RiskCheckResult): AsyncReviewMetadata | null {
    const metadata = riskResult.async_review;
    if (!metadata || !REVIEW_STATUSES.has(metadata.status) || !Number.isInteger(metadata.draft_version)) {
        return null;
    }
    return metadata;
}

export function getAsyncReviewStatus(riskResult: RiskCheckResult): AsyncReviewStatus | null {
    return getAsyncReviewMetadata(riskResult)?.status ?? null;
}

export function isReviewInProgress(riskResult: RiskCheckResult): boolean {
    const status = getAsyncReviewStatus(riskResult);
    return status === "QUEUED" || status === "REVIEWING";
}

export function isCurrentReviewCompleted(riskResult: RiskCheckResult): boolean {
    const metadata = getAsyncReviewMetadata(riskResult);
    const draftVersion = riskResult.draft_version;
    if (!metadata || metadata.status !== "COMPLETED" || !Number.isInteger(draftVersion)) {
        return false;
    }
    if (metadata.draft_version !== draftVersion || metadata.review_version !== draftVersion) {
        return false;
    }
    return !riskResult.content_hash || !metadata.content_hash || riskResult.content_hash === metadata.content_hash;
}
