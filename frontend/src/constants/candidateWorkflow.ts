import type { CandidateStatus } from "@/types/recruitment";

export const CANDIDATE_STATUSES = [
    "PENDING",
    "PASS_CV",
    "REJECT_CV",
    "INTERVIEW_CONFIRMED",
    "PASS_INTERVIEW",
    "REJECT_INTERVIEW",
    "OFFER_ACCEPTED",
] as const satisfies readonly CandidateStatus[];

export const INTERVIEW_STAGE = "INTERVIEW";

export function isCandidateStatus(value: string): value is CandidateStatus {
    return CANDIDATE_STATUSES.includes(value as CandidateStatus);
}
