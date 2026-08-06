import type { CandidateUpdatePayload } from "@/types/recruitment";

export function normalizeCandidateUpdatePayload(payload: CandidateUpdatePayload): CandidateUpdatePayload {
    if (!("interview_time" in payload)) {
        return payload;
    }

    return {
        ...payload,
        interview_time: payload.interview_time?.trim() || null,
    };
}
