import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ChevronLeft, ChevronRight, Eye, Inbox, RefreshCw, RotateCcw } from "lucide-react";
import { useState } from "react";

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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatDateTime, formatRelativeDateTime } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { SendOperation } from "@/types/recruitment";

const ALL = "ALL";
const OPERATION_STATUSES = ["SENDING_UNCONFIRMED", "PROVIDER_ACCEPTED", "DEFINITIVE_FAILURE", "DELIVERY_UNKNOWN", "FAILED_TERMINAL"];

export function EmailQueuePage() {
    const [page, setPage] = useState(1);
    const [status, setStatus] = useState(ALL);
    const [applicationId, setApplicationId] = useState("");
    const [selected, setSelected] = useState<SendOperation | null>(null);
    const operationsQuery = useQuery({
        queryKey: [...QUERY_KEYS.SEND_OPERATIONS, page, status, applicationId],
        queryFn: () => recruitmentApi.getSendOperations({ page, page_size: 20, status: status === ALL ? undefined : status, application_id: applicationId || undefined }),
    });
    const columns: DataTableColumn<SendOperation>[] = [
        { key: "operation", header: "Operation", render: (item) => <code className="text-xs">{item.id.slice(0, 8)}</code> },
        { key: "status", header: "Status", render: (item) => <StatusBadge value={item.operation_status} /> },
        { key: "provider", header: "Provider", render: (item) => item.provider_name },
        { key: "attempts", header: "Attempts", render: (item) => item.attempts.length },
        { key: "created", header: "Created", render: (item) => formatRelativeDateTime(item.created_at) },
        { key: "actor", header: "Created By", render: (item) => item.created_by },
        { key: "open", header: "", render: (item) => <Button aria-label="Open operation" onClick={(event) => { event.stopPropagation(); setSelected(item); }} size="icon" variant="ghost"><Eye className="h-4 w-4" /></Button> },
    ];
    return <div className="space-y-6"><PageHeader description="Track every real provider operation, attempt, failure and reconciliation." title="Email Operations" /><SearchFilterBar onSearchChange={(value) => { setApplicationId(value); setPage(1); }} searchPlaceholder="Filter by application ID..." searchValue={applicationId}><Select onValueChange={(value) => { setStatus(value); setPage(1); }} value={status}><SelectTrigger className="w-full sm:w-56"><SelectValue placeholder="Status" /></SelectTrigger><SelectContent><SelectItem value={ALL}>All statuses</SelectItem>{OPERATION_STATUSES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></SearchFilterBar>{operationsQuery.error && <ErrorState message={operationsQuery.error.message} />}{operationsQuery.isLoading ? <LoadingSkeleton rows={8} /> : <><DataTable columns={columns} data={operationsQuery.data?.items ?? []} emptyState={<EmptyState description="Generate and send a protected draft from a candidate profile." icon={Inbox} title="No send operations" />} getRowId={(item) => item.id} onRowClick={setSelected} /><div className="flex items-center justify-between text-sm text-muted-foreground"><span>{operationsQuery.data?.total ?? 0} operations</span><div className="flex items-center gap-2"><Button aria-label="Previous page" disabled={page <= 1} onClick={() => setPage(page - 1)} size="icon" variant="secondary"><ChevronLeft className="h-4 w-4" /></Button><span>Page {operationsQuery.data?.page ?? 1} of {operationsQuery.data?.pages ?? 1}</span><Button aria-label="Next page" disabled={page >= (operationsQuery.data?.pages ?? 1)} onClick={() => setPage(page + 1)} size="icon" variant="secondary"><ChevronRight className="h-4 w-4" /></Button></div></div></>}<OperationDrawer item={selected} onClose={() => setSelected(null)} onUpdated={setSelected} /></div>;
}

function OperationDrawer({ item, onClose, onUpdated }: { item: SendOperation | null; onClose: () => void; onUpdated: (item: SendOperation) => void }) {
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [action, setAction] = useState<"retry" | "reconcile" | null>(null);
    const [isResolveOpen, setResolveOpen] = useState(false);
    const draftQuery = useQuery({ queryKey: [...QUERY_KEYS.DRAFTS, item?.draft_revision_id], queryFn: () => recruitmentApi.getDraft(item!.draft_revision_id), enabled: Boolean(item) });
    const candidateQuery = useQuery({ queryKey: [...QUERY_KEYS.CANDIDATES, draftQuery.data?.candidate_id], queryFn: () => recruitmentApi.getCandidate(draftQuery.data!.candidate_id), enabled: Boolean(draftQuery.data) });
    const actionMutation = useMutation({
        mutationFn: () => action === "retry" ? recruitmentApi.retrySendOperation(item!.id) : recruitmentApi.reconcileSendOperation(item!.id),
        onSuccess: async (operation) => { showToast(`Operation updated: ${operation.operation_status}`, operation.operation_status === "PROVIDER_ACCEPTED" ? "success" : "warning"); setAction(null); onUpdated(operation); await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEND_OPERATIONS }); },
        onError: (error) => showToast(error.message, "error"),
    });
    const draft = draftQuery.data;
    const candidate = candidateQuery.data;
    return <><SideDrawer isOpen={Boolean(item)} onClose={onClose} title="Send operation detail">{item && <div className="space-y-5"><Card><CardHeader><div className="flex items-start justify-between gap-3"><div><CardTitle>{candidate?.full_name ?? "Candidate"}</CardTitle><CardDescription>{candidate?.application_id ?? "Loading application..."}</CardDescription></div><StatusBadge value={item.operation_status} /></div></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2"><Info label="Provider" value={item.provider_name} /><Info label="Created" value={formatDateTime(item.created_at)} /><Info label="Provider message ID" value={item.provider_message_id ?? "Not available"} /><Info label="Resolution" value={item.resolution_mode ?? "Not resolved"} /></CardContent></Card>{item.operation_status === "DELIVERY_UNKNOWN" && <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"><div className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><div><p className="font-semibold">Delivery status is unknown</p><p className="mt-1">Do not create another send. Reconcile within 24 hours using the same idempotency key, or verify provider logs and resolve manually.</p></div></div></div>}{draftQuery.isLoading ? <LoadingSkeleton rows={4} /> : draft && <Card><CardHeader><CardTitle>Email Snapshot</CardTitle><CardDescription>{draft.template_code} · Revision {draft.revision_number}</CardDescription></CardHeader><CardContent className="space-y-3"><Info label="Recipient" value={draft.to_email} /><Info label="Subject" value={draft.subject} /><div className="whitespace-pre-wrap rounded-md border border-border bg-muted/40 p-3 text-sm leading-6">{draft.rendered_body}</div></CardContent></Card>}<Card><CardHeader><CardTitle>Provider Attempts</CardTitle></CardHeader><CardContent className="space-y-2">{item.attempts.map((attempt) => <div className="flex items-center justify-between rounded-md border border-border p-3 text-sm" key={attempt.id}><div><p className="font-medium">Attempt {attempt.attempt_number}</p><p className="text-xs text-muted-foreground">{attempt.error_message ?? `${attempt.latency_ms ?? 0} ms`}</p></div><StatusBadge value={attempt.attempt_status} /></div>)}</CardContent></Card><div className="flex flex-wrap gap-2">{item.operation_status === "DEFINITIVE_FAILURE" && ["TRANSIENT_RETRYABLE", "QUOTA_EXCEEDED"].includes(item.failure_category ?? "") && <Button onClick={() => setAction("retry")}><RotateCcw className="h-4 w-4" />Retry Same Operation</Button>}{item.operation_status === "DELIVERY_UNKNOWN" && <><Button onClick={() => setAction("reconcile")}><RefreshCw className="h-4 w-4" />Reconcile with Provider</Button><Button onClick={() => setResolveOpen(true)} variant="secondary">Manual Resolution</Button></>}</div></div>}</SideDrawer><ConfirmDialog confirmLabel={action === "retry" ? "Retry Real Email" : "Reconcile"} description={action === "retry" ? "This makes another provider attempt under the same logical operation. Confirm after reviewing the failure category." : "This replays the exact payload with the same idempotency key. It is only permitted inside Resend's 24-hour window."} isOpen={Boolean(action)} onConfirm={() => actionMutation.mutate()} onOpenChange={(open) => !open && setAction(null)} title={action === "retry" ? "Retry this operation?" : "Reconcile delivery status?"} /><ResolutionDialog isOpen={isResolveOpen} onClose={() => setResolveOpen(false)} operation={item} onResolved={(operation) => { onUpdated(operation); setResolveOpen(false); }} /></>;
}

function ResolutionDialog({ isOpen, onClose, onResolved, operation }: { isOpen: boolean; onClose: () => void; onResolved: (item: SendOperation) => void; operation: SendOperation | null }) {
    const showToast = useUiStore((state) => state.showToast);
    const queryClient = useQueryClient();
    const [resolution, setResolution] = useState<"PROVIDER_ACCEPTED" | "PROVIDER_NOT_RECEIVED">("PROVIDER_ACCEPTED");
    const [rationale, setRationale] = useState("");
    const [acknowledged, setAcknowledged] = useState(false);
    const mutation = useMutation({ mutationFn: () => recruitmentApi.resolveSendOperation(operation!.id, { resolution, rationale, warning_acknowledged: acknowledged }), onSuccess: async (item) => { showToast("Delivery uncertainty resolved", "success"); onResolved(item); await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEND_OPERATIONS }); }, onError: (error) => showToast(error.message, "error") });
    return <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}><DialogContent className="max-w-lg"><DialogHeader><DialogTitle>Manual Delivery Resolution</DialogTitle><DialogDescription>Use only after verifying Resend logs or another authoritative delivery record.</DialogDescription></DialogHeader><div className="space-y-4"><div className="space-y-2"><Label>Verified outcome</Label><Select onValueChange={(value) => setResolution(value as typeof resolution)} value={resolution}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="PROVIDER_ACCEPTED">Provider Accepted</SelectItem><SelectItem value="PROVIDER_NOT_RECEIVED">Provider Did Not Receive</SelectItem></SelectContent></Select></div><div className="space-y-2"><Label htmlFor="resolution-rationale">Verification rationale</Label><Textarea id="resolution-rationale" onChange={(event) => setRationale(event.target.value)} placeholder="Describe where and how the status was verified..." value={rationale} /></div><label className="flex items-start gap-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-950"><input checked={acknowledged} className="mt-1" onChange={(event) => setAcknowledged(event.target.checked)} type="checkbox" /><span>I understand that an incorrect resolution can cause a duplicate email or incorrect communicated outcome.</span></label></div><DialogFooter><Button onClick={onClose} variant="secondary">Cancel</Button><Button disabled={!acknowledged || rationale.trim().length < 5 || mutation.isPending} onClick={() => mutation.mutate()}>Confirm Resolution</Button></DialogFooter></DialogContent></Dialog>;
}

function Info({ label, value }: { label: string; value: string }) {
    return <div><p className="text-xs font-medium uppercase text-muted-foreground">{label}</p><p className="mt-1 break-words text-sm font-medium text-card-foreground">{value}</p></div>;
}
