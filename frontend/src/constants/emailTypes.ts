import type { EmailType } from "@/types/recruitment";

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
