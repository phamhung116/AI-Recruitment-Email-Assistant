import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, FlaskConical, Inbox, Save, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { EmailReviewPanel, ReviewStatusBadge } from "@/components/shared/EmailReviewPanel";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchFilterBar } from "@/components/shared/SearchFilterBar";
import { SideDrawer } from "@/components/shared/SideDrawer";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { EMAIL_TYPES } from "@/constants/emailTypes";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatDateTime } from "@/lib/date";
import { isCurrentReviewCompleted, isReviewInProgress } from "@/lib/reviewState";
import { recruitmentApi } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { EmailQueueItem } from "@/types/recruitment";

const QUEUE_STATUSES = ["DRAFT", "PENDING_APPROVAL", "APPROVED", "SENT", "FAILED", "CANCELLED"];
const ALL_VALUE = "ALL";

type QueueAction = "approve" | "simulate" | "cancel";

const ACTION_COPY: Record<QueueAction, { confirmLabel: string; description: string; success: string; title: string }> = {
    approve: {
        confirmLabel: "Approve draft",
        description: "Confirm that an HR reviewer has checked the final wording and safety findings.",
        success: "Draft approved",
        title: "Approve this email draft?",
    },
    simulate: {
        confirmLabel: "Run simulation",
        description: "This records a simulated send in history. No real email will be delivered.",
        success: "Send simulation recorded",
        title: "Simulate sending this email?",
    },
    cancel: {
        confirmLabel: "Cancel draft",
        description: "This closes the queue item. The action cannot be undone from this demo UI.",
        success: "Draft cancelled",
        title: "Cancel this email draft?",
    },
};

export function EmailQueuePage() {
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [search, setSearch] = useState("");
    const [statusFilter, setStatusFilter] = useState(ALL_VALUE);
    const [emailTypeFilter, setEmailTypeFilter] = useState(ALL_VALUE);
    const [selectedItem, setSelectedItem] = useState<EmailQueueItem | null>(null);
    const [isDraftDirty, setIsDraftDirty] = useState(false);
    const [pendingAction, setPendingAction] = useState<QueueAction | null>(null);
    const queueQuery = useQuery({
        queryKey: QUERY_KEYS.EMAIL_QUEUE,
        queryFn: recruitmentApi.getEmailQueue,
    });
    const selectedDraftVersion = selectedItem?.risk_check_result.draft_version ?? 0;
    const selectedItemQuery = useQuery({
        queryKey: [...QUERY_KEYS.EMAIL_QUEUE, "detail", selectedItem?.id, selectedDraftVersion],
        queryFn: () => recruitmentApi.getEmailQueueItem(selectedItem!.id),
        enabled: Boolean(
            selectedItem
            && !isDraftDirty
            && isReviewInProgress(selectedItem.risk_check_result),
        ),
        refetchInterval: (query) => {
            const latestItem = query.state.data;
            const riskResult = latestItem?.risk_check_result ?? selectedItem?.risk_check_result;
            return riskResult && isReviewInProgress(riskResult) ? 1_000 : false;
        },
    });

    useEffect(() => {
        const refreshedItem = selectedItemQuery.data;
        if (!refreshedItem || isDraftDirty) return;

        setSelectedItem((currentItem) => (
            currentItem?.id === refreshedItem.id ? refreshedItem : currentItem
        ));
        queryClient.setQueryData<EmailQueueItem[]>(QUERY_KEYS.EMAIL_QUEUE, (items) => (
            items?.map((item) => item.id === refreshedItem.id ? refreshedItem : item)
        ));
    }, [isDraftDirty, queryClient, selectedItemQuery.data]);

    const updateMutation = useMutation({
        mutationFn: (item: EmailQueueItem) => recruitmentApi.updateEmailQueue(item.id, {
            subject: item.subject,
            body: item.body,
        }),
        onSuccess: async (item) => {
            setSelectedItem(item);
            setIsDraftDirty(false);
            showToast("Draft saved – review queued", "success");
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_QUEUE });
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const actionMutation = useMutation({
        mutationFn: ({ action, itemId }: { action: QueueAction; itemId: number }) => {
            if (action === "approve") {
                return recruitmentApi.approveEmailQueueItem(itemId);
            }

            if (action === "simulate") {
                return recruitmentApi.sendEmailQueueItem(itemId);
            }

            return recruitmentApi.cancelEmailQueueItem(itemId);
        },
        onSuccess: async (_, variables) => {
            showToast(ACTION_COPY[variables.action].success, "success");
            setPendingAction(null);
            setSelectedItem(null);
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_QUEUE });
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_HISTORY });
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DASHBOARD });
        },
        onError: (error) => showToast(error.message, "error"),
    });
    function openItem(item: EmailQueueItem) {
        setSelectedItem(item);
        setIsDraftDirty(false);
    }
    const filteredItems = useMemo(() => {
        return (queueQuery.data || []).filter((item) => {
            const matchesSearch = !search || `${item.candidate?.full_name || ""} ${item.to_email}`.toLowerCase().includes(search.toLowerCase());
            const matchesStatus = statusFilter === ALL_VALUE || item.status === statusFilter;
            const matchesEmailType = emailTypeFilter === ALL_VALUE || item.email_type === emailTypeFilter;

            return matchesSearch && matchesStatus && matchesEmailType;
        });
    }, [emailTypeFilter, queueQuery.data, search, statusFilter]);

    const columns: DataTableColumn<EmailQueueItem>[] = [
        {
            key: "candidate",
            header: "Candidate",
            render: (item) => item.candidate?.full_name || `Candidate #${item.candidate_id}`,
        },
        {
            key: "type",
            header: "Email Type",
            render: (item) => item.email_type,
        },
        {
            key: "status",
            header: "Status",
            render: (item) => <StatusBadge value={item.status} />,
        },
        {
            key: "approval",
            header: "Safety review",
            render: (item) => <ReviewStatusBadge riskResult={item.risk_check_result} />,
        },
        {
            key: "createdAt",
            header: "Created At",
            render: (item) => formatDateTime(item.created_at),
        },
        {
            key: "actions",
            header: "Actions",
            render: (item) => (
                <Button onClick={() => openItem(item)} size="sm" variant="secondary">
                    <Eye className="h-3.5 w-3.5" />
                    Open review
                </Button>
            ),
        },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                description="Operational dashboard for draft, approval, and send simulation workflow."
                title="Email Queue"
            />
            <SearchFilterBar
                onSearchChange={setSearch}
                searchPlaceholder="Search candidate or recipient..."
                searchValue={search}
            >
                <FilterSelect onChange={setStatusFilter} options={QUEUE_STATUSES} placeholder="Status" value={statusFilter} />
                <FilterSelect onChange={setEmailTypeFilter} options={EMAIL_TYPES} placeholder="Email Type" value={emailTypeFilter} />
            </SearchFilterBar>
            {queueQuery.error && <ErrorState message={queueQuery.error.message} />}
            {queueQuery.isLoading ? (
                <LoadingSkeleton rows={8} />
            ) : (
                <DataTable
                    columns={columns}
                    data={filteredItems}
                    emptyState={<EmptyState description="Generate an email draft from a candidate profile to populate the queue." icon={Inbox} title="No queue items found" />}
                />
            )}
            <EmailPreviewDrawer
                item={selectedItem}
                isDirty={isDraftDirty}
                isSaving={updateMutation.isPending}
                onAction={(action) => setPendingAction(action)}
                onChange={(item) => {
                    setSelectedItem(item);
                    setIsDraftDirty(true);
                }}
                onClose={() => {
                    setSelectedItem(null);
                    setIsDraftDirty(false);
                }}
                onSave={() => selectedItem && updateMutation.mutate(selectedItem)}
            />
            <ConfirmDialog
                confirmLabel={pendingAction ? ACTION_COPY[pendingAction].confirmLabel : "Confirm"}
                description={pendingAction ? ACTION_COPY[pendingAction].description : "Confirm this queue operation."}
                isDestructive={pendingAction === "cancel"}
                isOpen={Boolean(pendingAction && selectedItem)}
                onConfirm={() => selectedItem && pendingAction && actionMutation.mutate({ action: pendingAction, itemId: selectedItem.id })}
                onOpenChange={(isOpen) => !isOpen && setPendingAction(null)}
                title={pendingAction ? ACTION_COPY[pendingAction].title : "Confirm operation?"}
            />
        </div>
    );
}

function EmailPreviewDrawer({ item, isDirty, isSaving, onAction, onChange, onClose, onSave }: { item: EmailQueueItem | null; isDirty: boolean; isSaving: boolean; onAction: (action: QueueAction) => void; onChange: (item: EmailQueueItem) => void; onClose: () => void; onSave: () => void }) {
    const isEditable = Boolean(item && ["DRAFT", "PENDING_APPROVAL", "APPROVED"].includes(item.status));
    const canApprove = Boolean(item && ["DRAFT", "PENDING_APPROVAL"].includes(item.status));
    const canSimulate = Boolean(item && (item.status === "APPROVED" || (item.status === "DRAFT" && !item.requires_hr_approval)));
    const canCancel = Boolean(item && ["DRAFT", "PENDING_APPROVAL", "APPROVED", "FAILED"].includes(item.status));
    const isReviewReady = Boolean(item && isCurrentReviewCompleted(item.risk_check_result));

    return (
        <SideDrawer isOpen={Boolean(item)} onClose={onClose} title="Review email draft">
            {item && (
                <div className="space-y-5">
                    <Card className="shadow-none">
                        <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
                            <div>
                                <CardTitle>Candidate context</CardTitle>
                                <p className="mt-1 text-xs text-muted-foreground">Verify the recipient and workflow state before taking action.</p>
                            </div>
                            <StatusBadge value={item.status} />
                        </CardHeader>
                        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
                            <Info label="Name" value={item.candidate?.full_name || "-"} />
                            <Info label="Recipient" value={item.to_email} />
                            <Info label="Position" value={item.candidate?.position || "-"} />
                            <Info label="Status" value={item.candidate?.status || "-"} />
                        </CardContent>
                    </Card>
                    <div className="space-y-2">
                        <Label htmlFor="email-subject">Subject</Label>
                        <Input disabled={!isEditable} id="email-subject" value={item.subject} onChange={(event) => onChange({ ...item, subject: event.target.value })} />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="email-body">Body</Label>
                        <Textarea className="min-h-64 leading-6" disabled={!isEditable} id="email-body" value={item.body} onChange={(event) => onChange({ ...item, body: event.target.value })} />
                        {isDirty && <p className="text-xs font-medium text-amber-700">Unsaved changes. Save the draft before approval or another Gemini review.</p>}
                    </div>
                    <EmailReviewPanel
                        currentBody={item.body}
                        currentSubject={item.subject}
                        isStale={isDirty}
                        onApplySuggestion={isEditable ? (subject, body) => onChange({ ...item, subject, body }) : undefined}
                        queueId={item.id}
                        riskResult={item.risk_check_result}
                    />
                    <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center gap-2 border-t border-border bg-card/95 px-4 py-4 backdrop-blur sm:-mx-6 sm:px-6">
                        {isEditable && (
                            <Button disabled={!isDirty || isSaving} onClick={onSave}>
                                <Save className="h-4 w-4" />
                                {isSaving ? "Saving..." : "Save draft"}
                            </Button>
                        )}
                        {canApprove && <Button disabled={isDirty || !isReviewReady || isSaving} onClick={() => onAction("approve")} variant="secondary"><ShieldCheck className="h-4 w-4" />Approve</Button>}
                        {canSimulate && (
                            <Button disabled={isDirty || !isReviewReady || isSaving} onClick={() => onAction("simulate")} variant="outline">
                                <FlaskConical className="h-4 w-4" />
                                Simulate send
                            </Button>
                        )}
                        {canCancel && <Button onClick={() => onAction("cancel")} variant="destructive"><XCircle className="h-4 w-4" />Cancel</Button>}
                        {(canApprove || canSimulate) && !isReviewReady && !isDirty && (
                            <p className="basis-full text-xs font-medium text-amber-700" role="status">
                                Approve and Simulate send unlock after the current draft version completes review.
                            </p>
                        )}
                        {!isEditable && !canCancel && <p className="text-sm text-muted-foreground">This queue item is closed and available for review only.</p>}
                    </div>
                </div>
            )}
        </SideDrawer>
    );
}

function Info({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
            <p className="mt-1 text-card-foreground">{value}</p>
        </div>
    );
}

function FilterSelect({ onChange, options, placeholder, value }: { onChange: (value: string) => void; options: readonly string[]; placeholder: string; value: string }) {
    return (
        <Select onValueChange={onChange} value={value}>
            <SelectTrigger className="min-w-40">
                <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
                <SelectItem value={ALL_VALUE}>{placeholder}</SelectItem>
                {options.map((option) => (
                    <SelectItem key={option} value={option}>{option}</SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
