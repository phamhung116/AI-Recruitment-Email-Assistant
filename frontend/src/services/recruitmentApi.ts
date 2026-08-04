import type {
    AuditLogItem,
    Candidate,
    DashboardStats,
    EmailHistoryItem,
    EmailQueueItem,
    EmailTemplate,
    ImportResult,
} from "@/types/recruitment";

import { httpClient } from "./httpClient";

export interface CandidateFilters {
    search?: string;
    position?: string;
    stage?: string;
    status?: string;
}

export interface QueueFilters {
    status?: string;
    emailType?: string;
}

export const recruitmentApi = {
    getDashboardStats: async () => {
        const response = await httpClient.get<DashboardStats>("/dashboard");
        return response.data;
    },
    getCandidates: async (params: CandidateFilters = {}) => {
        const response = await httpClient.get<Candidate[]>("/candidates", { params });
        return response.data;
    },
    getCandidate: async (candidateId: number) => {
        const response = await httpClient.get<Candidate>(`/candidates/${candidateId}`);
        return response.data;
    },
    updateCandidate: async (candidateId: number, payload: Partial<Candidate>) => {
        const response = await httpClient.patch<Candidate>(`/candidates/${candidateId}`, payload);
        return response.data;
    },
    importCandidates: async (file: File, onUploadProgress?: (progress: number) => void) => {
        const formData = new FormData();
        formData.append("file", file);

        const response = await httpClient.post<ImportResult>("/candidates/import", formData, {
            onUploadProgress: (event) => {
                if (!event.total || !onUploadProgress) {
                    return;
                }

                onUploadProgress(Math.round((event.loaded * 100) / event.total));
            },
        });

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
    getEmailHistory: async (candidateId?: number) => {
        const response = await httpClient.get<EmailHistoryItem[]>("/email-history", {
            params: candidateId ? { candidate_id: candidateId } : undefined,
        });
        return response.data;
    },
    getAuditLogs: async () => {
        const response = await httpClient.get<AuditLogItem[]>("/audit-logs");
        return response.data;
    },
};
