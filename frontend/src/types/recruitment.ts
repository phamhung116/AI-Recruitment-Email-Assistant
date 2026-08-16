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
    application_id: string;
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
    communicated_decision?: string | null;
    communicated_stage?: string | null;
    communicated_at?: string | null;
}

export type DraftStatus =
    | "DRAFT_PENDING_CHECK"
    | "READY_TO_SEND"
    | "BLOCKED_DETERMINISTIC"
    | "FROZEN_IN_FLIGHT"
    | "SUPERSEDED"
    | "CORRECTION_DRAFT"
    | "DISCARDED"
    | "FINALIZED";

export type OperationStatus =
    | "SENDING_UNCONFIRMED"
    | "PROVIDER_ACCEPTED"
    | "DEFINITIVE_FAILURE"
    | "DELIVERY_UNKNOWN"
    | "FAILED_TERMINAL";

export interface DraftRevision {
    id: string;
    candidate_id: number;
    revision_number: number;
    template_code: string;
    stage: string;
    decision: string;
    to_email: string;
    subject: string;
    decision_critical_content: string;
    editable_content: string;
    rendered_body: string;
    status: DraftStatus;
    is_correction: boolean;
    correction_rationale: string | null;
    prior_operation_id: string | null;
    risk_check_result: RiskCheckResult;
    created_by: string;
    created_at: string;
    updated_at: string;
}

export interface ProviderAttempt {
    id: string;
    attempt_number: number;
    attempt_status: string;
    http_status_code: number | null;
    provider_message_id: string | null;
    error_code: string | null;
    error_message: string | null;
    latency_ms: number | null;
    initiated_at: string;
    completed_at: string | null;
}

export interface SendOperation {
    id: string;
    draft_revision_id: string;
    operation_status: OperationStatus;
    provider_name: string;
    provider_message_id: string | null;
    final_outcome: string | null;
    failure_category: string | null;
    resolution_mode: string | null;
    resolution_rationale: string | null;
    resolved_by: string | null;
    resolved_at: string | null;
    created_by: string;
    created_at: string;
    updated_at: string;
    attempts: ProviderAttempt[];
}

export interface AuditEvent {
    id: number;
    event_name: string;
    entity_type: string;
    entity_id: string;
    application_id: string | null;
    actor: string;
    action_outcome: string;
    payload_json: Record<string, unknown>;
    created_at: string;
}

export interface PaginatedResponse<TItem> {
    items: TItem[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
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
        loop_steps?: number;
        tool_calls?: number;
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
