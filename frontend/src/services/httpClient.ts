import axios from "axios";

export const httpClient = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
    timeout: 20000,
});

httpClient.interceptors.response.use(
    (response) => response,
    (error) => {
        const detail = error.response?.data?.detail;
        const message = getErrorMessage(detail);

        return Promise.reject(new Error(message));
    },
);

export function getErrorMessage(detail: unknown): string {
    if (typeof detail === "string") {
        return detail;
    }
    if (Array.isArray(detail)) {
        const validationMessages = detail
            .map(formatFastApiValidationIssue)
            .filter((message): message is string => Boolean(message));

        return validationMessages.length > 0
            ? validationMessages.join("; ")
            : "The submitted data is invalid.";
    }
    if (!detail || typeof detail !== "object") {
        return "Unable to complete the request. Please try again.";
    }

    const structuredDetail = detail as {
        errors?: unknown;
        issues?: Array<{ message?: unknown; remediation?: unknown }>;
    };
    const firstIssue = Array.isArray(structuredDetail.issues) ? structuredDetail.issues[0] : undefined;
    if (typeof firstIssue?.message === "string") {
        return typeof firstIssue.remediation === "string"
            ? `${firstIssue.message} ${firstIssue.remediation}`
            : firstIssue.message;
    }
    if (Array.isArray(structuredDetail.errors) && typeof structuredDetail.errors[0] === "string") {
        return structuredDetail.errors[0];
    }

    return "The backend rejected this operation. Review the draft safety findings and try again.";
}

function formatFastApiValidationIssue(issue: unknown): string | null {
    if (!issue || typeof issue !== "object") {
        return null;
    }

    const validationIssue = issue as { loc?: unknown; msg?: unknown };
    if (typeof validationIssue.msg !== "string") {
        return null;
    }

    const fieldPath = Array.isArray(validationIssue.loc)
        ? validationIssue.loc
            .filter((segment) => !["body", "path", "query"].includes(String(segment)))
            .map(String)
            .join(".")
        : "";

    return fieldPath ? `${fieldPath}: ${validationIssue.msg}` : validationIssue.msg;
}
