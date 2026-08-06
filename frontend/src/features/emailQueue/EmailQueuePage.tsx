import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Inbox, Send } from "lucide-react";
import { useMemo, useState } from "react";

import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
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
import { formatRelativeDateTime } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { EmailQueueItem } from "@/types/recruitment";

const QUEUE_STATUSES = ["DRAFT", "PENDING_APPROVAL", "APPROVED", "SENT", "FAILED", "CANCELLED"];
const ALL_VALUE = "ALL";

type QueueAction = "approve" | "send" | "cancel";

export function EmailQueuePage() {
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [search, setSearch] = useState("");
    const [statusFilter, setStatusFilter] = useState(ALL_VALUE);
    const [emailTypeFilter, setEmailTypeFilter] = useState(ALL_VALUE);
    const [selectedItem, setSelectedItem] = useState<EmailQueueItem | null>(null);
    const [pendingAction, setPendingAction] = useState<QueueAction | null>(null);
    const [sortBy, setSortBy] = useState("createdAt");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
    const queueQuery = useQuery({
        queryKey: QUERY_KEYS.EMAIL_QUEUE,
        queryFn: recruitmentApi.getEmailQueue,
    });
    const updateMutation = useMutation({
        mutationFn: (item: EmailQueueItem) => recruitmentApi.updateEmailQueue(item.id, {
            subject: item.subject,
            body: item.body,
        }),
        onSuccess: async () => {
            showToast("Email draft updated", "success");
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_QUEUE });
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const actionMutation = useMutation({
        mutationFn: ({ action, itemId }: { action: QueueAction; itemId: number }) => {
            if (action === "approve") {
                return recruitmentApi.approveEmailQueueItem(itemId);
            }

            if (action === "send") {
                return recruitmentApi.sendEmailQueueItem(itemId);
            }

            return recruitmentApi.cancelEmailQueueItem(itemId);
        },
        onSuccess: async (_, variables) => {
            showToast(`Email ${variables.action} action completed`, "success");
            setPendingAction(null);
            setSelectedItem(null);
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_QUEUE });
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_HISTORY });
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DASHBOARD });
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const filteredItems = useMemo(() => {
        const items = (queueQuery.data || []).filter((item) => {
            const matchesSearch = !search || `${item.candidate?.full_name || ""} ${item.to_email}`.toLowerCase().includes(search.toLowerCase());
            const matchesStatus = statusFilter === ALL_VALUE || item.status === statusFilter;
            const matchesEmailType = emailTypeFilter === ALL_VALUE || item.email_type === emailTypeFilter;

            return matchesSearch && matchesStatus && matchesEmailType;
        });

        return sortItems(items, sortBy, sortOrder);
    }, [emailTypeFilter, queueQuery.data, search, sortBy, sortOrder, statusFilter]);

    const columns: DataTableColumn<EmailQueueItem>[] = [
        {
            key: "candidate",
            header: "Candidate",
            sortable: true,
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
            header: "Requires Approval",
            render: (item) => item.requires_hr_approval ? <StatusBadge sensitive value="SENSITIVE" /> : "No",
        },
        {
            key: "createdAt",
            header: "Created At",
            sortable: true,
            render: (item) => formatRelativeDateTime(item.created_at),
        },
        {
            key: "actions",
            header: "Actions",
            render: (item) => (
                <div className="flex flex-wrap gap-2">
                    <Button onClick={() => setSelectedItem(item)} size="sm" variant="secondary">Preview</Button>
                    <Button onClick={() => { setSelectedItem(item); setPendingAction("approve"); }} size="sm" variant="outline">Approve</Button>
                    <Button onClick={() => { setSelectedItem(item); setPendingAction("send"); }} size="sm" variant="outline">Send</Button>
                    <Button onClick={() => { setSelectedItem(item); setPendingAction("cancel"); }} size="sm" variant="outline">Cancel</Button>
                </div>
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
                <Input className="min-w-44" placeholder="Date range" />
            </SearchFilterBar>
            {queueQuery.error && <ErrorState message={queueQuery.error.message} />}
            {queueQuery.isLoading ? (
                <LoadingSkeleton rows={8} />
            ) : (
                <DataTable
                    columns={columns}
                    data={filteredItems}
                    emptyState={<EmptyState description="Generate an email draft from a candidate profile to populate the queue." icon={Inbox} title="No queue items found" />}
                    onSortChange={(key, order) => {
                        setSortBy(key);
                        setSortOrder(order);
                    }}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                />
            )}
            <EmailPreviewDrawer
                item={selectedItem}
                onAction={(action) => setPendingAction(action)}
                onChange={setSelectedItem}
                onClose={() => setSelectedItem(null)}
                onSave={() => selectedItem && updateMutation.mutate(selectedItem)}
            />
            <ConfirmDialog
                confirmLabel={pendingAction ? pendingAction.charAt(0).toUpperCase() + pendingAction.slice(1) : "Confirm"}
                description="Please confirm this queue operation. The backend will enforce approval, duplicate, and status rules."
                isDestructive={pendingAction === "cancel"}
                isOpen={Boolean(pendingAction && selectedItem)}
                onConfirm={() => selectedItem && pendingAction && actionMutation.mutate({ action: pendingAction, itemId: selectedItem.id })}
                onOpenChange={(isOpen) => !isOpen && setPendingAction(null)}
                title={`${pendingAction || "Confirm"} email?`}
            />
        </div>
    );
}

function sortItems(items: EmailQueueItem[], sortBy: string, sortOrder: "asc" | "desc") {
    const sorted = [...items].sort((first, second) => {
        const firstValue = getSortValue(first, sortBy);
        const secondValue = getSortValue(second, sortBy);

        return firstValue.localeCompare(secondValue);
    });

    return sortOrder === "asc" ? sorted : sorted.reverse();
}

function getSortValue(item: EmailQueueItem, sortBy: string) {
    if (sortBy === "candidate") {
        return item.candidate?.full_name || "";
    }

    if (sortBy === "type") {
        return item.email_type;
    }

    if (sortBy === "status") {
        return item.status;
    }

    if (sortBy === "createdAt") {
        return item.created_at;
    }

    return "";
}

function EmailPreviewDrawer({ item, onAction, onChange, onClose, onSave }: { item: EmailQueueItem | null; onAction: (action: QueueAction) => void; onChange: (item: EmailQueueItem) => void; onClose: () => void; onSave: () => void }) {
    return (
        <SideDrawer isOpen={Boolean(item)} onClose={onClose} title="Email Preview">
            {item && (
                <div className="space-y-5">
                    <Card>
                        <CardHeader>
                            <CardTitle>Candidate Information</CardTitle>
                        </CardHeader>
                        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
                            <Info label="Name" value={item.candidate?.full_name || "-"} />
                            <Info label="Recipient" value={item.to_email} />
                            <Info label="Position" value={item.candidate?.position || "-"} />
                            <Info label="Status" value={item.candidate?.status || "-"} />
                        </CardContent>
                    </Card>
                    <div className="space-y-2">
                        <Label>Subject</Label>
                        <Input value={item.subject} onChange={(event) => onChange({ ...item, subject: event.target.value })} />
                    </div>
                    <div className="space-y-2">
                        <Label>Body</Label>
                        <Textarea className="min-h-72" value={item.body} onChange={(event) => onChange({ ...item, body: event.target.value })} />
                    </div>
                    <Card>
                        <CardHeader>
                            <CardTitle>Risk Check Result</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <pre className="overflow-auto rounded-md bg-slate-950 p-4 text-xs text-slate-100">
                                {JSON.stringify(item.risk_check_result, null, 2)}
                            </pre>
                            <div className="mt-4">
                                {item.requires_hr_approval ? <StatusBadge sensitive value="SENSITIVE" /> : <StatusBadge value="APPROVED" />}
                            </div>
                        </CardContent>
                    </Card>
                    <div className="flex flex-wrap gap-2">
                        <Button onClick={onSave}>Save</Button>
                        <Button onClick={() => onAction("approve")} variant="secondary">Approve</Button>
                        <Button onClick={() => onAction("send")} variant="secondary">
                            <Send className="h-4 w-4" />
                            Send
                        </Button>
                        <Button onClick={() => onAction("cancel")} variant="destructive">Cancel</Button>
                    </div>
                </div>
            )}
        </SideDrawer>
    );
}

function Info({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
            <p className="mt-1 text-slate-900">{value}</p>
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
