import type { CandidateStatus, EmailType } from "@/types/recruitment";

export const EMAIL_TYPES: EmailType[] = [
    "APPLICATION_RECEIVED",
    "INTERVIEW_INVITATION",
    "INTERVIEW_REMINDER",
    "REJECTION_AFTER_CV",
    "REJECTION_AFTER_INTERVIEW",
    "OFFER_EMAIL",
    "ONBOARDING_EMAIL",
    "RESCHEDULE_RESPONSE",
    "NEXT_ROUND_EMAIL",
];

export const TEMPLATE_PLACEHOLDERS = [
    "{{candidate_name}}",
    "{{position}}",
    "{{interview_time}}",
    "{{interviewer}}",
    "{{company_name}}",
] as const;

export const STATUS_EMAIL_TYPE_MAP: Partial<Record<CandidateStatus, EmailType>> = {
    PASS_CV: "INTERVIEW_INVITATION",
    REJECT_CV: "REJECTION_AFTER_CV",
    INTERVIEW_CONFIRMED: "INTERVIEW_REMINDER",
    PASS_INTERVIEW: "OFFER_EMAIL",
    REJECT_INTERVIEW: "REJECTION_AFTER_INTERVIEW",
    OFFER_ACCEPTED: "ONBOARDING_EMAIL",
};
