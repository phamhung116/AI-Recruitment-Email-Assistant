import type {
    AgentReviewResult,
    AuditEvent,
    Candidate,
    CandidateUpdatePayload,
    DashboardStats,
    EmailHistoryItem,
    EmailQueueItem,
    EmailTemplate,
    DraftRevision,
    ImportPreviewResult,
    ImportResult,
    PaginatedResponse,
    SendOperation,
} from "@/types/recruitment";

import { httpClient } from "./httpClient";

export interface CandidateFilters {
    search?: string;
    position?: string;
    stage?: string;
    status?: string;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: "asc" | "desc";
    sort?: string;
    direction?: "asc" | "desc";
}

export interface QueueFilters {
    status?: string;
    emailType?: string;
}

export interface CandidateFilterOptions {
    positions: string[];
    stages: string[];
    statuses: string[];
}

export const recruitmentApi = {
    getDashboardStats: async () => {
        const [candidates, operations] = await Promise.all([
            httpClient.get<PaginatedResponse<Candidate>>("/api/v1/candidates", { params: { page_size: 1 } }),
            httpClient.get<PaginatedResponse<SendOperation>>("/api/v1/send-operations", { params: { page_size: 100 } }),
        ]);
        return {
            total_candidates: candidates.data.total,
            pending_emails: operations.data.items.filter((item) => item.operation_status === "SENDING_UNCONFIRMED" || item.operation_status === "DELIVERY_UNKNOWN").length,
            sent_emails: operations.data.items.filter((item) => item.operation_status === "PROVIDER_ACCEPTED").length,
            failed_emails: operations.data.items.filter((item) => item.operation_status === "DEFINITIVE_FAILURE" || item.operation_status === "FAILED_TERMINAL").length,
        } satisfies DashboardStats;
    },
    getCandidates: async (params: CandidateFilters = {}) => {
        const response = await httpClient.get<PaginatedResponse<Candidate>>("/api/v1/candidates", {
            params: {
                ...params,
                sort: params.sort ?? params.sort_by,
                direction: params.direction ?? params.sort_order,
                sort_by: undefined,
                sort_order: undefined,
            },
        });
        return response.data;
    },
    getCandidate: async (candidateId: number) => {
        const response = await httpClient.get<Candidate>(`/api/v1/candidates/${candidateId}`);
        return response.data;
    },
    getCandidateFilterOptions: async () => {
        const response = await httpClient.get<CandidateFilterOptions>("/candidates/filter-options");
        return response.data;
    },
    updateCandidate: async (candidateId: number, payload: CandidateUpdatePayload) => {
        const response = await httpClient.patch<Candidate>(`/candidates/${candidateId}`, payload);
        return response.data;
    },
    updateCandidateStatus: async (candidateId: number, status: string, actor = "Hieu") => {
        const response = await httpClient.patch<Candidate>(`/candidates/${candidateId}/status`, { status, actor });
        return response.data;
    },
    bulkUpdateCandidateStatus: async (candidateIds: number[], status: string, actor = "Hieu") => {
        const response = await httpClient.post<{ affected: number }>("/candidates/bulk/status", {
            candidate_ids: candidateIds,
            status,
            actor,
        });
        return response.data;
    },
    bulkDeleteCandidates: async (candidateIds: number[], actor = "Hieu") => {
        const response = await httpClient.post<{ affected: number }>("/candidates/bulk/delete", {
            candidate_ids: candidateIds,
            actor,
        });
        return response.data;
    },
    importCandidates: async (file: File, onUploadProgress?: (progress: number) => void) => {
        const formData = new FormData();
        formData.append("file", file);

        const response = await httpClient.post<ImportResult>("/api/v1/candidates/import", formData, {
            onUploadProgress: (event) => {
                if (!event.total || !onUploadProgress) {
                    return;
                }

                onUploadProgress(Math.round((event.loaded * 100) / event.total));
            },
        });

        return response.data;
    },
    previewCandidateImport: async (file: File) => {
        const formData = new FormData();
        formData.append("file", file);

        const response = await httpClient.post<ImportPreviewResult>("/api/v1/candidates/import/preview", formData);
        return response.data;
    },
    getTemplates: async () => {
        const response = await httpClient.get<EmailTemplate[]>("/email-templates");
        return response.data;
    },
    createTemplate: async (payload: Omit<EmailTemplate, "id" | "created_at" | "updated_at">) => {
        const response = await httpClient.post<EmailTemplate>("/email-templates", payload);
        return response.data;
    },
    updateTemplate: async (templateId: number, payload: Partial<EmailTemplate>) => {
        const response = await httpClient.patch<EmailTemplate>(`/email-templates/${templateId}`, payload);
        return response.data;
    },
    deleteTemplate: async (templateId: number) => {
        const response = await httpClient.delete<{ deleted: boolean }>(`/email-templates/${templateId}`);
        return response.data;
    },
    generateDraft: async (candidateId: number, emailType?: string) => {
        const response = await httpClient.post<EmailQueueItem>("/email-drafts/generate", {
            candidate_id: candidateId,
            email_type: emailType,
        });
        return response.data;
    },
    getEmailQueue: async () => {
        const response = await httpClient.get<EmailQueueItem[]>("/email-queue");
        return response.data;
    },
    getEmailQueueItem: async (queueId: number) => {
        const response = await httpClient.get<EmailQueueItem>(`/email-queue/${queueId}`);
        return response.data;
    },
    updateEmailQueue: async (queueId: number, payload: Partial<EmailQueueItem>) => {
        const response = await httpClient.patch<EmailQueueItem>(`/email-queue/${queueId}`, payload);
        return response.data;
    },
    approveEmailQueueItem: async (queueId: number) => {
        const response = await httpClient.post<EmailQueueItem>(`/email-queue/${queueId}/approve`);
        return response.data;
    },
    sendEmailQueueItem: async (queueId: number) => {
        const response = await httpClient.post<EmailQueueItem>(`/email-queue/${queueId}/send`);
        return response.data;
    },
    cancelEmailQueueItem: async (queueId: number) => {
        const response = await httpClient.post<EmailQueueItem>(`/email-queue/${queueId}/cancel`);
        return response.data;
    },
    reviewEmailDraft: async (queueId: number, actor = "demo_hr") => {
        const response = await httpClient.post<AgentReviewResult>("/api/v1/agent/review-draft", {
            queue_id: queueId,
            actor,
        });
        return response.data;
    },
    getEmailHistory: async (candidateId?: number) => {
        const response = await httpClient.get<EmailHistoryItem[]>("/email-history", {
            params: candidateId ? { candidate_id: candidateId } : undefined,
        });
        return response.data;
    },
    getAuditLogs: async () => {
        const response = await httpClient.get<PaginatedResponse<AuditEvent>>("/api/v1/audit-logs");
        return response.data;
    },
    createDraft: async (applicationId: string, actor = "demo_hr") => {
        const response = await httpClient.post<DraftRevision>("/api/v1/drafts", {
            application_id: applicationId,
            actor,
        });
        return response.data;
    },
    reviseDraft: async (draftId: string, payload: { subject?: string; editable_content?: string; actor?: string }) => {
        const response = await httpClient.patch<DraftRevision>(`/api/v1/drafts/${draftId}`, {
            ...payload,
            actor: payload.actor ?? "demo_hr",
        });
        return response.data;
    },
    getDraft: async (draftId: string) => {
        const response = await httpClient.get<DraftRevision>(`/api/v1/drafts/${draftId}`);
        return response.data;
    },
    getCandidateDrafts: async (candidateId: number) => {
        const response = await httpClient.get<PaginatedResponse<DraftRevision>>(`/api/v1/candidates/${candidateId}/drafts`);
        return response.data;
    },
    sendDraft: async (draftId: string, actor = "demo_hr") => {
        const response = await httpClient.post<SendOperation>(`/api/v1/drafts/${draftId}/send`, {
            actor,
            confirmation_acknowledged: true,
        });
        return response.data;
    },
    getSendOperations: async (params: { page?: number; page_size?: number; status?: string; application_id?: string } = {}) => {
        const response = await httpClient.get<PaginatedResponse<SendOperation>>("/api/v1/send-operations", { params });
        return response.data;
    },
    getSendOperation: async (operationId: string) => {
        const response = await httpClient.get<SendOperation>(`/api/v1/send-operations/${operationId}`);
        return response.data;
    },
    retrySendOperation: async (operationId: string, actor = "demo_hr") => {
        const response = await httpClient.post<SendOperation>(`/api/v1/send-operations/${operationId}/retry`, {
            actor,
            confirmation_acknowledged: true,
        });
        return response.data;
    },
    reconcileSendOperation: async (operationId: string, actor = "demo_hr") => {
        const response = await httpClient.post<SendOperation>(`/api/v1/send-operations/${operationId}/reconcile`, {
            actor,
            confirmation_acknowledged: true,
        });
        return response.data;
    },
    resolveSendOperation: async (operationId: string, payload: { resolution: "PROVIDER_ACCEPTED" | "PROVIDER_NOT_RECEIVED"; rationale: string; warning_acknowledged: boolean; actor?: string }) => {
        const response = await httpClient.post<SendOperation>(`/api/v1/send-operations/${operationId}/resolve`, {
            ...payload,
            actor: payload.actor ?? "demo_hr",
        });
        return response.data;
    },
};
