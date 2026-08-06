import { describe, expect, it } from "vitest";

import { normalizeCandidateUpdatePayload } from "@/features/candidates/candidateForm";

describe("normalizeCandidateUpdatePayload", () => {
    it("converts an empty interview time to null for FastAPI", () => {
        expect(normalizeCandidateUpdatePayload({
            full_name: "Nguyen Minh An",
            interview_time: "",
        })).toEqual({
            full_name: "Nguyen Minh An",
            interview_time: null,
        });
    });

    it("preserves a populated ISO interview time", () => {
        const interviewTime = "2026-08-10T02:30:00.000Z";

        expect(normalizeCandidateUpdatePayload({ interview_time: interviewTime })).toEqual({
            interview_time: interviewTime,
        });
    });
});
