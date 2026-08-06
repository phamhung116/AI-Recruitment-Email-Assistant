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
    interview_time: string | null;
    interviewer: string | null;
    note: string | null;
    created_at: string;
    updated_at: string;
}

export interface CandidateUpdatePayload {
    full_name?: string;
    email?: string | null;
    phone?: string | null;
    position?: string | null;
    stage?: string | null;
    status?: CandidateStatus | string;
    interview_time?: string | null;
    interviewer?: string | null;
    note?: string | null;
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
    risk_check_result: RiskCheckResult;
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

export type AgentReviewStatus =
    | "completed"
    | "deterministic_blocked"
    | "disabled"
    | "unavailable";

export interface AgentSemanticIssue {
    rule_id: string;
    severity: "info" | "warning" | "error" | "blocker";
    message: string;
    evidence: string;
    requires_human_review: boolean;
}

export interface DeterministicValidationIssue {
    rule_id: string;
    severity: "info" | "warning" | "error" | "blocker";
    message: string;
    evidence: Record<string, unknown>;
    remediation: string;
    is_blocking: boolean;
    source: "deterministic" | "agent";
}

export interface AgentReviewResult {
    status: AgentReviewStatus;
    draft_subject: string;
    draft_body: string;
    issues: AgentSemanticIssue[];
    uncertainty: {
        has_uncertainty: boolean;
        reason: string | null;
    };
    review_summary: string;
    requires_human_review: boolean;
    semantic_review_available: boolean;
    model_metadata: {
        provider: string;
        model: string;
        prompt_version: string;
        skill_name: string;
        skill_version: string;
        attempts: number;
    };
    trace: Array<{
        step: string;
        status: string;
        detail: string;
    }>;
}

export interface RiskCheckResult {
    passed?: boolean;
    issues?: DeterministicValidationIssue[];
    errors?: string[];
    checked_at?: string;
    requires_human_review?: boolean;
    agent_review?: AgentReviewResult;
    draft_version?: number;
    content_hash?: string;
    async_review?: AsyncReviewMetadata;
    [key: string]: unknown;
}

export type AsyncReviewStatus =
    | "QUEUED"
    | "REVIEWING"
    | "COMPLETED"
    | "UNAVAILABLE"
    | "FAILED"
    | "STALE";

export interface AsyncReviewMetadata {
    status: AsyncReviewStatus;
    draft_version: number;
    review_version?: number;
    content_hash?: string;
    updated_at?: string | null;
    completed_at?: string;
    failure_reason?: string;
}
