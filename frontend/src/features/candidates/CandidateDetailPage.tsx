import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, MailPlus, Save, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { z } from "zod";

import { ActivityTimeline } from "@/components/shared/ActivityTimeline";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { EMAIL_TYPES } from "@/constants/emailTypes";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { toDateTimeInputValue } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { Candidate, EmailQueueItem, EmailTemplate } from "@/types/recruitment";

const candidateSchema = z.object({
    full_name: z.string().min(1, "Candidate name is required"),
    email: z.string().email("Invalid email").or(z.literal("")).nullable(),
    phone: z.string().nullable(),
    position: z.string().nullable(),
    stage: z.string().nullable(),
    status: z.string().min(1),
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
        mutationFn: (payload: CandidateFormValues) => recruitmentApi.updateCandidate(candidateId, payload),
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
                                <FormInput control={form.control} label="Status" name="status" />
                                <FormInput control={form.control} label="Interviewer" name="interviewer" />
                                <FormInput control={form.control} label="Interview Time" name="interview_time" type="datetime-local" />
                                <div className="md:col-span-2">
                                    <Controller
                                        control={form.control}
                                        name="note"
                                        render={({ field }) => (
                                            <div className="space-y-2">
                                                <Label>Candidate Notes</Label>
                                                <Textarea
                                                    className="min-h-44"
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
                    <Card>
                        <CardHeader>
                            <CardTitle>Quick Actions</CardTitle>
                            <CardDescription>Common HR operations for this candidate.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <Button className="w-full justify-start" onClick={() => setIsGenerateOpen(true)}>
                                <MailPlus className="h-4 w-4" />
                                Generate Email Draft
                            </Button>
                            <Button className="w-full justify-start" variant="secondary">
                                <UserRound className="h-4 w-4" />
                                Update Status
                            </Button>
                            <Button className="w-full justify-start" variant="secondary">
                                <CalendarClock className="h-4 w-4" />
                                Schedule Interview
                            </Button>
                            <div className="rounded-lg border border-slate-200 p-3">
                                <p className="text-xs font-medium uppercase text-slate-500">Current Status</p>
                                <div className="mt-2">
                                    <StatusBadge value={candidate.status} />
                                </div>
                            </div>
                        </CardContent>
                    </Card>
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
    return (
        <Controller
            control={control}
            name={name}
            render={({ field, fieldState }) => (
                <div className="space-y-2">
                    <Label>{label}</Label>
                    <Input
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
    const [selectedEmailType, setSelectedEmailType] = useState<string>("INTERVIEW_INVITATION");
    const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
    const [draft, setDraft] = useState<EmailQueueItem | null>(null);
    const templatesQuery = useQuery({
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
        return (templatesQuery.data || []).find((template) => String(template.id) === selectedTemplateId);
    }, [selectedTemplateId, templatesQuery.data]);

    function handleContinue() {
        if (step === 1) {
            setStep(2);
            return;
        }

        mutation.mutate();
    }

    return (
        <Dialog onOpenChange={onOpenChange} open={isOpen}>
            <DialogContent className="max-w-3xl">
                <DialogHeader>
                    <DialogTitle>Generate Email Draft</DialogTitle>
                    <DialogDescription>Three-step workflow for safe AI-assisted email drafting.</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4">
                    <StepIndicator step={step} />
                    {step === 1 && (
                        <div className="space-y-2">
                            <Label>Email Type</Label>
                            <Select onValueChange={setSelectedEmailType} value={selectedEmailType}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {EMAIL_TYPES.map((emailType) => (
                                        <SelectItem key={emailType} value={emailType}>{emailType}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    {step === 2 && (
                        <div className="space-y-3">
                            <Label>Template</Label>
                            <Select onValueChange={setSelectedTemplateId} value={selectedTemplateId}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select template" />
                                </SelectTrigger>
                                <SelectContent>
                                    {(templatesQuery.data || []).map((template: EmailTemplate) => (
                                        <SelectItem key={template.id} value={String(template.id)}>{template.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {selectedTemplate && (
                                <div className="rounded-lg border border-primary-100 bg-primary-50/60 p-4 text-sm">
                                    <p className="font-medium text-slate-900">{selectedTemplate.subject}</p>
                                    <p className="mt-2 whitespace-pre-wrap text-slate-600">{selectedTemplate.body}</p>
                                </div>
                            )}
                        </div>
                    )}
                    {step === 3 && draft && (
                        <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
                            <div>
                                <p className="text-xs font-medium uppercase text-slate-500">Subject</p>
                                <p className="mt-1 font-medium text-slate-950">{draft.subject}</p>
                            </div>
                            <div>
                                <p className="text-xs font-medium uppercase text-slate-500">Email Body</p>
                                <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{draft.body}</p>
                            </div>
                        </div>
                    )}
                </div>
                <DialogFooter>
                    <Button onClick={() => onOpenChange(false)} variant="secondary">Close</Button>
                    {step > 1 && step < 3 && <Button onClick={() => setStep(step - 1)} variant="secondary">Back</Button>}
                    {step < 3 && <Button disabled={mutation.isPending || (step === 2 && !selectedTemplateId)} onClick={handleContinue}>Continue</Button>}
                    {step === 3 && <Button onClick={() => onOpenChange(false)}>Queue Email</Button>}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function StepIndicator({ step }: { step: number }) {
    return (
        <div className="grid grid-cols-3 gap-2">
            {["Email Type", "Template", "Preview"].map((label, index) => (
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
        status: candidate?.status || "PENDING",
        interview_time: candidate?.interview_time || "",
        interviewer: candidate?.interviewer || "",
        note: candidate?.note || "",
    };
}
