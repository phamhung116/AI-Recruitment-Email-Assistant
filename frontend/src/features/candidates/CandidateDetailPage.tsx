import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Mail, RefreshCw, Save, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatDateTime, formatRelativeDateTime } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { Candidate, DraftRevision } from "@/types/recruitment";

export function CandidateDetailPage() {
    const candidateId = Number(useParams().candidateId);
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null);
    const [isSendOpen, setSendOpen] = useState(false);
    const candidateQuery = useQuery({
        queryKey: [...QUERY_KEYS.CANDIDATES, candidateId],
        queryFn: () => recruitmentApi.getCandidate(candidateId),
        enabled: Number.isFinite(candidateId),
    });
    const draftsQuery = useQuery({
        queryKey: [...QUERY_KEYS.DRAFTS, candidateId],
        queryFn: () => recruitmentApi.getCandidateDrafts(candidateId),
        enabled: Number.isFinite(candidateId),
    });
    const operationsQuery = useQuery({
        queryKey: [...QUERY_KEYS.SEND_OPERATIONS, candidateQuery.data?.application_id],
        queryFn: () => recruitmentApi.getSendOperations({ application_id: candidateQuery.data!.application_id, page_size: 100 }),
        enabled: Boolean(candidateQuery.data?.application_id),
    });
    const candidate = candidateQuery.data;
    const drafts = draftsQuery.data?.items ?? [];
    const selectedDraft = drafts.find((draft) => draft.id === selectedDraftId) ?? drafts[0] ?? null;
    const selectedOperation = operationsQuery.data?.items.find((operation) => operation.draft_revision_id === selectedDraft?.id);

    useEffect(() => {
        if (!selectedDraftId && drafts[0]) setSelectedDraftId(drafts[0].id);
    }, [drafts, selectedDraftId]);

    async function refreshWorkflow() {
        await Promise.all([
            queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DRAFTS }),
            queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SEND_OPERATIONS }),
            queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CANDIDATES }),
        ]);
    }

    const generateMutation = useMutation({
        mutationFn: () => recruitmentApi.createDraft(candidate!.application_id),
        onSuccess: async (draft) => {
            showToast("Protected draft generated", "success");
            await refreshWorkflow();
            setSelectedDraftId(draft.id);
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const sendMutation = useMutation({
        mutationFn: () => recruitmentApi.sendDraft(selectedDraft!.id),
        onSuccess: async (operation) => {
            setSendOpen(false);
            showToast(operation.operation_status === "PROVIDER_ACCEPTED" ? "Email accepted by provider" : `Send result: ${operation.operation_status}`, operation.operation_status === "PROVIDER_ACCEPTED" ? "success" : "warning");
            await refreshWorkflow();
        },
        onError: (error) => showToast(error.message, "error"),
    });

    if (candidateQuery.isLoading || draftsQuery.isLoading) return <LoadingSkeleton rows={8} />;
    if (candidateQuery.error) return <ErrorState message={candidateQuery.error.message} />;
    if (!candidate) return <ErrorState message="Candidate not found." />;

    return (
        <div className="space-y-6">
            <PageHeader
                actions={<Button asChild variant="secondary"><Link to="/candidates"><ArrowLeft className="h-4 w-4" />Candidates</Link></Button>}
                description={`${candidate.application_id} · ${candidate.position || "Position not specified"}`}
                title={candidate.full_name}
            />
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.72fr)]">
                <div className="space-y-6">
                    <CandidateCard candidate={candidate} />
                    <Card>
                        <CardHeader><CardTitle>Draft Revisions</CardTitle><CardDescription>Decision-critical wording is protected by backend policy.</CardDescription></CardHeader>
                        <CardContent>
                            {drafts.length === 0 ? <EmptyState actionLabel="Generate Draft" description="Create a fixed-template draft and run deterministic safety checks." icon={Mail} onAction={() => generateMutation.mutate()} title="No draft revisions" /> : (
                                <div className="space-y-2">{drafts.map((draft) => <button className={`flex w-full items-center justify-between rounded-md border p-3 text-left ${selectedDraft?.id === draft.id ? "border-primary-200 bg-primary-50" : "border-border hover:bg-muted"}`} key={draft.id} onClick={() => setSelectedDraftId(draft.id)} type="button"><div><p className="font-medium">Revision {draft.revision_number} · {draft.template_code}</p><p className="mt-1 text-xs text-muted-foreground">{formatRelativeDateTime(draft.created_at)} by {draft.created_by}</p></div><StatusBadge value={draft.status} /></button>)}</div>
                            )}
                        </CardContent>
                    </Card>
                </div>
                <div className="space-y-6">
                    {selectedDraft ? <DraftInspector draft={selectedDraft} operationStatus={selectedOperation?.operation_status} onRevised={async (draft) => { await refreshWorkflow(); setSelectedDraftId(draft.id); }} /> : null}
                    <Card>
                        <CardHeader><CardTitle>Quick Actions</CardTitle><CardDescription>All provider actions are single-candidate and explicitly confirmed.</CardDescription></CardHeader>
                        <CardContent className="grid gap-2">
                            <Button disabled={generateMutation.isPending} onClick={() => generateMutation.mutate()} variant="secondary"><RefreshCw className="h-4 w-4" />Generate New Revision</Button>
                            <Button disabled={!selectedDraft || !["READY_TO_SEND", "CORRECTION_DRAFT"].includes(selectedDraft.status) || Boolean(selectedOperation) || sendMutation.isPending} onClick={() => setSendOpen(true)}><ShieldCheck className="h-4 w-4" />Send Real Email</Button>
                            {selectedOperation && <div className="rounded-md border border-border bg-muted/40 p-3 text-sm"><p className="font-medium">Provider operation</p><div className="mt-2"><StatusBadge value={selectedOperation.operation_status} /></div><p className="mt-2 text-xs text-muted-foreground">Provider accepted means request accepted, not guaranteed inbox delivery.</p></div>}
                        </CardContent>
                    </Card>
                </div>
            </div>
            <ConfirmDialog
                confirmLabel={sendMutation.isPending ? "Sending..." : "Send Real Email"}
                description={`This will send a real ${selectedDraft?.template_code ?? "recruitment"} email to ${candidate.email}. Verify recipient, subject, decision and body before continuing.`}
                isOpen={isSendOpen}
                onConfirm={() => selectedDraft && sendMutation.mutate()}
                onOpenChange={setSendOpen}
                title="Send this email through Resend?"
            />
        </div>
    );
}

function CandidateCard({ candidate }: { candidate: Candidate }) {
    return <Card><CardHeader><div className="flex items-start justify-between gap-4"><div><CardTitle>Candidate Information</CardTitle><CardDescription>Source application data is read-only in this delivery workflow.</CardDescription></div><StatusBadge value={candidate.status} /></div></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2"><Info label="Email" value={candidate.email || "-"} /><Info label="Phone" value={candidate.phone || "-"} /><Info label="Position" value={candidate.position || "-"} /><Info label="Stage" value={candidate.stage || "-"} /><Info label="Applied" value={formatDateTime(candidate.created_at)} /><Info label="Communicated outcome" value={candidate.communicated_decision || "Not communicated"} /></CardContent></Card>;
}

function DraftInspector({ draft, onRevised, operationStatus }: { draft: DraftRevision; onRevised: (draft: DraftRevision) => void; operationStatus?: string }) {
    const showToast = useUiStore((state) => state.showToast);
    const [subject, setSubject] = useState(draft.subject);
    const [editableContent, setEditableContent] = useState(draft.editable_content);
    useEffect(() => { setSubject(draft.subject); setEditableContent(draft.editable_content); }, [draft]);
    const isEditable = ["READY_TO_SEND", "DRAFT_PENDING_CHECK", "BLOCKED_DETERMINISTIC"].includes(draft.status) && !operationStatus;
    const isDirty = subject !== draft.subject || editableContent !== draft.editable_content;
    const reviseMutation = useMutation({
        mutationFn: () => recruitmentApi.reviseDraft(draft.id, { subject, editable_content: editableContent }),
        onSuccess: (revision) => { showToast("New draft revision saved", "success"); onRevised(revision); },
        onError: (error) => showToast(error.message, "error"),
    });
    const issues = useMemo(() => Array.isArray(draft.risk_check_result.issues) ? draft.risk_check_result.issues : [], [draft.risk_check_result.issues]);
    return <Card><CardHeader><div className="flex items-start justify-between gap-3"><div><CardTitle>Email Preview</CardTitle><CardDescription>{draft.template_code} · Revision {draft.revision_number}</CardDescription></div><StatusBadge value={draft.status} /></div></CardHeader><CardContent className="space-y-4"><div className="space-y-2"><Label htmlFor="draft-subject">Subject</Label><Input disabled={!isEditable} id="draft-subject" onChange={(event) => setSubject(event.target.value)} value={subject} /></div><div className="space-y-2"><Label>Protected decision content</Label><div className="rounded-md border border-border bg-muted/60 p-3 text-sm leading-6">{draft.decision_critical_content}</div></div><div className="space-y-2"><Label htmlFor="draft-editable">Editable greeting and notes</Label><Textarea className="min-h-44" disabled={!isEditable} id="draft-editable" onChange={(event) => setEditableContent(event.target.value)} value={editableContent} /></div>{issues.length > 0 && <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{issues.map((issue, index) => <p key={index}>{issue.message}</p>)}</div>}<Button disabled={!isDirty || reviseMutation.isPending} onClick={() => reviseMutation.mutate()} variant="secondary"><Save className="h-4 w-4" />Save as New Revision</Button></CardContent></Card>;
}

function Info({ label, value }: { label: string; value: string }) {
    return <div><p className="text-xs font-medium uppercase text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium text-card-foreground">{value}</p></div>;
}
