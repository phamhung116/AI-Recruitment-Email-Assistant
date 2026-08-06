import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, MailPlus, Save, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { z } from "zod";

import { ActivityTimeline } from "@/components/shared/ActivityTimeline";
import { EmailReviewPanel } from "@/components/shared/EmailReviewPanel";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CANDIDATE_STATUSES, isCandidateStatus } from "@/constants/candidateWorkflow";
import { STATUS_EMAIL_TYPE_MAP } from "@/constants/emailTypes";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { CandidateQuickActions } from "@/features/candidates/CandidateQuickActions";
import { CandidateStatusSelect } from "@/features/candidates/CandidateStatusSelect";
import { normalizeCandidateUpdatePayload } from "@/features/candidates/candidateForm";
import { toDateTimeInputValue } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { Candidate, CandidateStatus, EmailQueueItem } from "@/types/recruitment";

const candidateSchema = z.object({
    full_name: z.string().min(1, "Candidate name is required"),
    email: z.string().email("Invalid email").or(z.literal("")).nullable(),
    phone: z.string().nullable(),
    position: z.string().nullable(),
    stage: z.string().nullable(),
    status: z.enum(CANDIDATE_STATUSES, "Select a supported candidate status"),
    interview_time: z.string().nullable(),
    interviewer: z.string().nullable(),
    note: z.string().nullable(),
});

type CandidateFormValues = z.infer<typeof candidateSchema>;

export function CandidateDetailPage() {
    const params = useParams();
    const candidateId = Number(params.candidateId);
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [isGenerateOpen, setIsGenerateOpen] = useState(false);

    const candidateQuery = useQuery({
        queryKey: [...QUERY_KEYS.CANDIDATES, candidateId],
        queryFn: () => recruitmentApi.getCandidate(candidateId),
        enabled: Number.isFinite(candidateId),
    });
    const historyQuery = useQuery({
        queryKey: [...QUERY_KEYS.EMAIL_HISTORY, candidateId],
        queryFn: () => recruitmentApi.getEmailHistory(candidateId),
        enabled: Number.isFinite(candidateId),
    });
    const form = useForm<CandidateFormValues>({
        resolver: zodResolver(candidateSchema),
        defaultValues: toFormValues(candidateQuery.data),
    });
    const updateMutation = useMutation({
        mutationFn: (payload: CandidateFormValues) => recruitmentApi.updateCandidate(
            candidateId,
            normalizeCandidateUpdatePayload(payload),
        ),
        onSuccess: async () => {
            showToast("Candidate updated", "success");
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CANDIDATES });
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DASHBOARD });
        },
        onError: (error) => showToast(error.message, "error"),
    });

    useEffect(() => {
        form.reset(toFormValues(candidateQuery.data));
    }, [candidateQuery.data, form]);

    if (candidateQuery.isLoading) {
        return <LoadingSkeleton rows={8} />;
    }

    if (candidateQuery.error) {
        return <ErrorState message={candidateQuery.error.message} />;
    }

    const candidate = candidateQuery.data;

    if (!candidate) {
        return <ErrorState message="Candidate not found." />;
    }

    return (
        <div className="space-y-6">
            <PageHeader
                actions={(
                    <Button onClick={() => setIsGenerateOpen(true)}>
                        <MailPlus className="h-4 w-4" />
                        Generate Email Draft
                    </Button>
                )}
                description="Review profile, update recruitment status, and manage email touchpoints."
                title={candidate.full_name}
            />
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Candidate Information</CardTitle>
                            <CardDescription>Core recruiting data synchronized with the backend API.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form className="grid gap-4 md:grid-cols-2" onSubmit={form.handleSubmit((values) => updateMutation.mutate(values))}>
                                <FormInput control={form.control} label="Name" name="full_name" />
                                <FormInput control={form.control} label="Email" name="email" />
                                <FormInput control={form.control} label="Phone" name="phone" />
                                <FormInput control={form.control} label="Position" name="position" />
                                <FormInput control={form.control} label="Stage" name="stage" />
                                <Controller
                                    control={form.control}
                                    name="status"
                                    render={({ field, fieldState }) => (
                                        <div>
                                            <CandidateStatusSelect
                                                id="candidate-status"
                                                onChange={field.onChange}
                                                value={field.value}
                                            />
                                            {fieldState.error && <p className="mt-2 text-xs text-red-600">{fieldState.error.message}</p>}
                                        </div>
                                    )}
                                />
                                <FormInput control={form.control} label="Interviewer" name="interviewer" />
                                <FormInput control={form.control} label="Interview Time" name="interview_time" type="datetime-local" />
                                <div className="md:col-span-2">
                                    <Controller
                                        control={form.control}
                                        name="note"
                                        render={({ field }) => (
                                            <div className="space-y-2">
                                                <Label htmlFor="candidate-notes">Notes</Label>
                                                <Textarea
                                                    className="min-h-44"
                                                    id="candidate-notes"
                                                    placeholder="Add context, follow-up notes, and recruiter observations..."
                                                    {...field}
                                                    value={field.value || ""}
                                                />
                                                <p className="text-xs text-slate-500">Autosave UI placeholder. Click Save to persist in this MVP.</p>
                                            </div>
                                        )}
                                    />
                                </div>
                                <div className="md:col-span-2">
                                    <Button disabled={updateMutation.isPending} type="submit">
                                        <Save className="h-4 w-4" />
                                        Save Changes
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>
                </div>
                <div className="space-y-6">
                    <CandidateQuickActions
                        candidate={candidate}
                        onGenerateDraft={() => setIsGenerateOpen(true)}
                    />
                    <Card>
                        <CardHeader>
                            <CardTitle>Email History Timeline</CardTitle>
                            <CardDescription>Messages sent to this candidate.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ActivityTimeline
                                items={(historyQuery.data || []).map((item) => ({
                                    title: item.email_type,
                                    description: item.subject,
                                    status: "SENT",
                                    time: item.sent_at,
                                }))}
                            />
                        </CardContent>
                    </Card>
                </div>
            </div>
            <GenerateEmailDialog
                candidate={candidate}
                isOpen={isGenerateOpen}
                onOpenChange={setIsGenerateOpen}
            />
        </div>
    );
}

function FormInput({ control, label, name, type = "text" }: { control: ReturnType<typeof useForm<CandidateFormValues>>["control"]; label: string; name: keyof CandidateFormValues; type?: string }) {
    const inputId = `candidate-${name}`;

    return (
        <Controller
            control={control}
            name={name}
            render={({ field, fieldState }) => (
                <div className="space-y-2">
                    <Label htmlFor={inputId}>{label}</Label>
                    <Input
                        id={inputId}
                        type={type}
                        {...field}
                        value={type === "datetime-local" ? toDateTimeInputValue(field.value) : field.value || ""}
                        onChange={(event) => field.onChange(type === "datetime-local" && event.target.value ? new Date(event.target.value).toISOString() : event.target.value)}
                    />
                    {fieldState.error && <p className="text-xs text-red-600">{fieldState.error.message}</p>}
                </div>
            )}
        />
    );
}

function GenerateEmailDialog({ candidate, isOpen, onOpenChange }: { candidate: Candidate; isOpen: boolean; onOpenChange: (isOpen: boolean) => void }) {
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [step, setStep] = useState(1);
    const [draft, setDraft] = useState<EmailQueueItem | null>(null);
    const selectedEmailType = STATUS_EMAIL_TYPE_MAP[candidate.status as CandidateStatus];
    const templatesQuery = useQuery({
        enabled: isOpen,
        queryKey: QUERY_KEYS.EMAIL_TEMPLATES,
        queryFn: recruitmentApi.getTemplates,
    });
    const mutation = useMutation({
        mutationFn: () => recruitmentApi.generateDraft(candidate.id, selectedEmailType),
        onSuccess: async (item) => {
            setDraft(item);
            setStep(3);
            showToast("Email draft generated", "success");
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_QUEUE });
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const selectedTemplate = useMemo(() => {
        return (templatesQuery.data || []).find((template) => template.email_type === selectedEmailType);
    }, [selectedEmailType, templatesQuery.data]);

    function handleContinue() {
        if (step === 1) {
            if (!selectedEmailType) {
                showToast("This candidate status does not allow an email draft yet", "warning");
                return;
            }
            setStep(2);
            return;
        }

        mutation.mutate();
    }

    function handleOpenChange(nextIsOpen: boolean) {
        if (!nextIsOpen) {
            setStep(1);
            setDraft(null);
        }
        onOpenChange(nextIsOpen);
    }

    return (
        <Dialog onOpenChange={handleOpenChange} open={isOpen}>
            <DialogContent className="max-h-[calc(100vh-2rem)] max-w-3xl overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Generate Email Draft</DialogTitle>
                    <DialogDescription>Three-step workflow for safe AI-assisted email drafting.</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4">
                    <StepIndicator step={step} />
                    {step === 1 && (
                        <div className="space-y-3">
                            <p className="text-sm text-muted-foreground">The backend policy maps candidate status to one allowed email type. AI cannot change this decision.</p>
                            <div className="grid items-center gap-3 rounded-lg border border-border bg-muted/40 p-4 sm:grid-cols-[1fr_auto_1fr]">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Candidate status</p>
                                    <div className="mt-2"><StatusBadge value={candidate.status} /></div>
                                </div>
                                <ArrowRight className="hidden h-5 w-5 text-muted-foreground sm:block" />
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Allowed email</p>
                                    <p className="mt-2 text-sm font-semibold text-card-foreground">{selectedEmailType || "No email allowed"}</p>
                                </div>
                            </div>
                            {!selectedEmailType && (
                                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                                    HR must record a supported recruitment decision before generating an outcome email.
                                </div>
                            )}
                        </div>
                    )}
                    {step === 2 && (
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-sm font-medium text-card-foreground">
                                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                                Verified template selected by backend policy
                            </div>
                            {templatesQuery.isLoading && <LoadingSkeleton rows={3} />}
                            {templatesQuery.error && <ErrorState message={templatesQuery.error.message} />}
                            {selectedTemplate && (
                                <div className="rounded-lg border border-border bg-muted/40 p-4 text-sm">
                                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{selectedTemplate.name}</p>
                                    <p className="mt-2 font-medium text-card-foreground">{selectedTemplate.subject}</p>
                                    <p className="mt-2 whitespace-pre-wrap leading-6 text-muted-foreground">{selectedTemplate.body}</p>
                                </div>
                            )}
                            {!templatesQuery.isLoading && !templatesQuery.error && !selectedTemplate && (
                                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">No verified template exists for {selectedEmailType}. Draft generation is unavailable.</div>
                            )}
                        </div>
                    )}
                    {step === 3 && draft && (
                        <div className="space-y-4">
                            <div className="rounded-lg border border-border bg-card p-4">
                                <div>
                                    <p className="text-xs font-medium uppercase text-muted-foreground">Subject</p>
                                    <p className="mt-1 font-medium text-card-foreground">{draft.subject}</p>
                                </div>
                                <div className="mt-4">
                                    <p className="text-xs font-medium uppercase text-muted-foreground">Email body</p>
                                    <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-card-foreground/80">{draft.body}</p>
                                </div>
                            </div>
                            <EmailReviewPanel currentBody={draft.body} currentSubject={draft.subject} riskResult={draft.risk_check_result} />
                            <p className="text-xs text-muted-foreground">The draft has already been added to Email Queue. Open it there to edit, review, approve, or simulate sending.</p>
                        </div>
                    )}
                </div>
                <DialogFooter>
                    <Button onClick={() => handleOpenChange(false)} variant="secondary">Close</Button>
                    {step > 1 && step < 3 && <Button onClick={() => setStep(step - 1)} variant="secondary">Back</Button>}
                    {step < 3 && <Button disabled={mutation.isPending || !selectedEmailType || (step === 2 && !selectedTemplate)} onClick={handleContinue}>{mutation.isPending ? "Generating..." : "Continue"}</Button>}
                    {step === 3 && <Button onClick={() => handleOpenChange(false)}>Done</Button>}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function StepIndicator({ step }: { step: number }) {
    return (
        <div className="grid grid-cols-3 gap-2">
            {["Policy mapping", "Verified template", "Safety review"].map((label, index) => (
                <div className={`rounded-md border px-3 py-2 text-sm ${step === index + 1 ? "border-primary-200 bg-primary-50 text-primary-900" : "border-slate-200 bg-slate-50 text-slate-500"}`} key={label}>
                    {index + 1}. {label}
                </div>
            ))}
        </div>
    );
}

function toFormValues(candidate?: Candidate): CandidateFormValues {
    return {
        full_name: candidate?.full_name || "",
        email: candidate?.email || "",
        phone: candidate?.phone || "",
        position: candidate?.position || "",
        stage: candidate?.stage || "",
        status: candidate && isCandidateStatus(candidate.status) ? candidate.status : "PENDING",
        interview_time: candidate?.interview_time || "",
        interviewer: candidate?.interviewer || "",
        note: candidate?.note || "",
    };
}
