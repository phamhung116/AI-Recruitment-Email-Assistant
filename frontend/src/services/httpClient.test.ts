import { describe, expect, it } from "vitest";

import { getErrorMessage } from "@/services/httpClient";

describe("getErrorMessage", () => {
    it("shows field-specific FastAPI validation errors", () => {
        expect(getErrorMessage([
            {
                type: "datetime_from_date_parsing",
                loc: ["body", "interview_time"],
                msg: "Input should be a valid datetime or date",
                input: "",
            },
        ])).toBe("interview_time: Input should be a valid datetime or date");
    });

    it("shows all validation errors without the FastAPI transport prefix", () => {
        expect(getErrorMessage([
            { loc: ["body", "interviewer"], msg: "Field required" },
            { loc: ["body", "status"], msg: "Input should be a valid string" },
        ])).toBe("interviewer: Field required; status: Input should be a valid string");
    });

    it("keeps structured workflow messages and remediation", () => {
        expect(getErrorMessage({
            issues: [{ message: "Interview time is missing.", remediation: "Add a verified time." }],
        })).toBe("Interview time is missing. Add a verified time.");
    });
});
