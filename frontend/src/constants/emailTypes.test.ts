import { describe, expect, it } from "vitest";

import { STATUS_EMAIL_TYPE_MAP } from "@/constants/emailTypes";

describe("STATUS_EMAIL_TYPE_MAP", () => {
    it.each([
        ["PASS_CV", "INTERVIEW_INVITATION"],
        ["REJECT_CV", "REJECTION_AFTER_CV"],
        ["INTERVIEW_CONFIRMED", "INTERVIEW_REMINDER"],
        ["PASS_INTERVIEW", "OFFER_EMAIL"],
        ["REJECT_INTERVIEW", "REJECTION_AFTER_INTERVIEW"],
        ["OFFER_ACCEPTED", "ONBOARDING_EMAIL"],
    ] as const)("maps %s to %s", (status, emailType) => {
        expect(STATUS_EMAIL_TYPE_MAP[status]).toBe(emailType);
    });

    it("does not allow an email type for a pending candidate", () => {
        expect(STATUS_EMAIL_TYPE_MAP.PENDING).toBeUndefined();
    });
});
