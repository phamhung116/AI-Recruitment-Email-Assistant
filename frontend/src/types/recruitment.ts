export type CandidateStatus =
    | "PENDING"
    | "PASS_CV"
    | "REJECT_CV"
    | "INTERVIEW_CONFIRMED"
    | "PASS_INTERVIEW"
    | "REJECT_INTERVIEW"
    | "OFFER_ACCEPTED";

export type EmailType =
    | "APPLICATION_RECEIVED"
    | "INTERVIEW_INVITATION"
    | "INTERVIEW_REMINDER"
    | "REJECTION_AFTER_CV"
    | "REJECTION_AFTER_INTERVIEW"
    | "OFFER_EMAIL"
    | "ONBOARDING_EMAIL"
    | "RESCHEDULE_RESPONSE"
    | "NEXT_ROUND_EMAIL";

export type QueueStatus =
    | "DRAFT"
    | "PENDING_APPROVAL"
    | "APPROVED"
    | "SENT"
    | "FAILED"
    | "CANCELLED";

export interface Candidate {
    id: number;
    full_name: string;
    email: string | null;
    phone: string | null;
    position: string | null;
    stage: string | null;
    status: CandidateStatus | string;
    status_updated_at: string | null;
    status_updated_by: string | null;
    interview_time: string | null;
    interviewer: string | null;
    note: string | null;
    created_at: string;
    updated_at: string;
}

export interface PaginatedResponse<TItem> {
    items: TItem[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
}

export interface EmailTemplate {
    id: number;
    name: string;
    email_type: EmailType | string;
    subject: string;
    body: string;
    required_placeholders: string[];
    is_sensitive: boolean;
    created_at: string;
    updated_at: string;
}

export interface EmailQueueItem {
    id: number;
    candidate_id: number;
    email_type: EmailType | string;
    to_email: string;
    subject: string;
    body: string;
    status: QueueStatus | string;
    requires_hr_approval: boolean;
    risk_check_result: Record<string, unknown>;
    created_by: string | null;
    approved_by: string | null;
    sent_at: string | null;
    created_at: string;
    updated_at: string;
    candidate?: Candidate | null;
}

export interface EmailHistoryItem {
    id: number;
    candidate_id: number;
    email_type: EmailType | string;
    to_email: string;
    subject: string;
    body: string;
    sent_by: string | null;
    sent_at: string;
    candidate?: Candidate | null;
}

export interface AuditLogItem {
    id: number;
    action: string;
    entity_type: string | null;
    entity_id: number | null;
    actor: string | null;
    metadata_json: Record<string, unknown>;
    created_at: string;
}

export interface DashboardStats {
    total_candidates: number;
    pending_emails: number;
    sent_emails: number;
    failed_emails: number;
}

export interface ImportResult {
    imported: number;
    skipped: number;
    errors: string[];
}

export interface ImportPreviewRow {
    row_number: number;
    is_valid: boolean;
    reason: string | null;
    candidate: Partial<Candidate>;
}

export interface ImportPreviewResult {
    total_rows: number;
    valid_rows: number;
    invalid_rows: number;
    rows: ImportPreviewRow[];
}
