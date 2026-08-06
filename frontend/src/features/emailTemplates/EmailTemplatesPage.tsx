import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Grid2X2, List, Mail, Plus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { EMAIL_TYPES, TEMPLATE_PLACEHOLDERS } from "@/constants/emailTypes";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatRelativeDateTime } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { EmailTemplate } from "@/types/recruitment";

const templateSchema = z.object({
    name: z.string().min(1, "Template name is required"),
    email_type: z.string().min(1),
    subject: z.string().min(1, "Subject is required"),
    body: z.string().min(1, "Body is required"),
    required_placeholders: z.string(),
    is_sensitive: z.boolean(),
});

type TemplateFormValues = z.infer<typeof templateSchema>;
type ViewMode = "table" | "card";

const DEFAULT_TEMPLATE: TemplateFormValues = {
    name: "",
    email_type: "INTERVIEW_INVITATION",
    subject: "",
    body: "",
    required_placeholders: "candidate_name, position",
    is_sensitive: false,
};

export function EmailTemplatesPage() {
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [viewMode, setViewMode] = useState<ViewMode>("table");
    const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<EmailTemplate | null>(null);
    const [sortBy, setSortBy] = useState("updatedAt");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
    const templatesQuery = useQuery({
        queryKey: QUERY_KEYS.EMAIL_TEMPLATES,
        queryFn: recruitmentApi.getTemplates,
    });
    const form = useForm<TemplateFormValues>({
        resolver: zodResolver(templateSchema),
        defaultValues: DEFAULT_TEMPLATE,
    });
    const watchedValues = form.watch();
    const saveMutation = useMutation({
        mutationFn: (values: TemplateFormValues) => {
            const payload = toTemplatePayload(values);
            return editingTemplate
                ? recruitmentApi.updateTemplate(editingTemplate.id, payload)
                : recruitmentApi.createTemplate(payload);
        },
        onSuccess: async () => {
            showToast("Template saved", "success");
            setEditingTemplate(null);
            form.reset(DEFAULT_TEMPLATE);
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_TEMPLATES });
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const deleteMutation = useMutation({
        mutationFn: (templateId: number) => recruitmentApi.deleteTemplate(templateId),
        onSuccess: async () => {
            showToast("Template deleted", "success");
            setDeleteTarget(null);
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EMAIL_TEMPLATES });
        },
        onError: (error) => showToast(error.message, "error"),
    });

    useEffect(() => {
        if (!editingTemplate) {
            return;
        }

        form.reset({
            name: editingTemplate.name,
            email_type: editingTemplate.email_type,
            subject: editingTemplate.subject,
            body: editingTemplate.body,
            required_placeholders: editingTemplate.required_placeholders.join(", "),
            is_sensitive: editingTemplate.is_sensitive,
        });
    }, [editingTemplate, form]);

    const sortedTemplates = useMemo(() => sortTemplates(templatesQuery.data || [], sortBy, sortOrder), [sortBy, sortOrder, templatesQuery.data]);

    const columns: DataTableColumn<EmailTemplate>[] = [
        {
            key: "name",
            header: "Name",
            sortable: true,
            render: (template) => <span className="font-medium text-slate-950">{template.name}</span>,
        },
        {
            key: "type",
            header: "Email Type",
            render: (template) => template.email_type,
        },
        {
            key: "sensitive",
            header: "Sensitive",
            sortable: true,
            render: (template) => template.is_sensitive ? <StatusBadge sensitive value="SENSITIVE" /> : "No",
        },
        {
            key: "updatedAt",
            header: "Updated At",
            sortable: true,
            render: (template) => formatRelativeDateTime(template.updated_at),
        },
        {
            key: "actions",
            header: "Actions",
            render: (template) => (
                <div className="flex flex-wrap gap-2">
                    <Button onClick={() => setEditingTemplate(template)} size="sm" variant="secondary">Edit</Button>
                    <Button onClick={() => duplicateTemplate(template)} size="sm" variant="outline">
                        <Copy className="h-3.5 w-3.5" />
                    </Button>
                    <Button onClick={() => setDeleteTarget(template)} size="sm" variant="outline">
                        <Trash2 className="h-3.5 w-3.5 text-red-600" />
                    </Button>
                </div>
            ),
        },
    ];

    function duplicateTemplate(template: EmailTemplate) {
        setEditingTemplate(null);
        form.reset({
            name: `${template.name} Copy`,
            email_type: template.email_type,
            subject: template.subject,
            body: template.body,
            required_placeholders: template.required_placeholders.join(", "),
            is_sensitive: template.is_sensitive,
        });
    }

    function insertPlaceholder(placeholder: string) {
        form.setValue("body", `${form.getValues("body")} ${placeholder}`.trim());
    }

    return (
        <div className="space-y-6">
            <PageHeader
                actions={(
                    <>
                        <Button onClick={() => setViewMode("table")} size="icon" variant={viewMode === "table" ? "default" : "secondary"}>
                            <List className="h-4 w-4" />
                        </Button>
                        <Button onClick={() => setViewMode("card")} size="icon" variant={viewMode === "card" ? "default" : "secondary"}>
                            <Grid2X2 className="h-4 w-4" />
                        </Button>
                        <Button onClick={() => { setEditingTemplate(null); form.reset(DEFAULT_TEMPLATE); }}>
                            <Plus className="h-4 w-4" />
                            Create
                        </Button>
                    </>
                )}
                description="Manage reusable recruitment email templates with live preview."
                title="Email Templates"
            />
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_460px]">
                <div>
                    {templatesQuery.error && <ErrorState message={templatesQuery.error.message} />}
                    {templatesQuery.isLoading ? (
                        <LoadingSkeleton rows={8} />
                    ) : viewMode === "table" ? (
                        <DataTable
                            columns={columns}
                            data={sortedTemplates}
                            emptyState={<EmptyState description="Create your first recruitment email template." icon={Mail} title="No templates yet" />}
                            onSortChange={(key, order) => {
                                setSortBy(key);
                                setSortOrder(order);
                            }}
                            sortBy={sortBy}
                            sortOrder={sortOrder}
                        />
                    ) : (
                        <TemplateCardGrid
                            onDelete={setDeleteTarget}
                            onEdit={setEditingTemplate}
                            templates={sortedTemplates}
                        />
                    )}
                </div>
                <Card>
                    <CardHeader>
                        <CardTitle>Template Editor</CardTitle>
                        <CardDescription>Split-screen editor with immediate preview.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form className="space-y-5" onSubmit={form.handleSubmit((values) => saveMutation.mutate(values))}>
                            <div className="grid gap-4 sm:grid-cols-2">
                                <FormInput control={form.control} label="Template Name" name="name" />
                                <Controller
                                    control={form.control}
                                    name="email_type"
                                    render={({ field }) => (
                                        <div className="space-y-2">
                                            <Label>Email Type</Label>
                                            <Select onValueChange={field.onChange} value={field.value}>
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
                                />
                            </div>
                            <Controller
                                control={form.control}
                                name="is_sensitive"
                                render={({ field }) => (
                                    <div className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                                        <div>
                                            <Label>Sensitive Template</Label>
                                            <p className="text-xs text-slate-500">Requires HR approval before queue send.</p>
                                        </div>
                                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                                    </div>
                                )}
                            />
                            <FormInput control={form.control} label="Subject" name="subject" />
                            <FormInput control={form.control} label="Required Placeholders" name="required_placeholders" />
                            <Controller
                                control={form.control}
                                name="body"
                                render={({ field }) => (
                                    <div className="space-y-2">
                                        <Label>Body</Label>
                                        <Textarea className="min-h-52" {...field} />
                                    </div>
                                )}
                            />
                            <div>
                                <p className="mb-2 text-sm font-medium text-slate-700">Placeholder Helper</p>
                                <div className="flex flex-wrap gap-2">
                                    {TEMPLATE_PLACEHOLDERS.map((placeholder) => (
                                        <Button key={placeholder} onClick={() => insertPlaceholder(placeholder)} size="sm" variant="secondary">
                                            {placeholder}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                            <Card className="bg-slate-50 shadow-none">
                                <CardHeader>
                                    <CardTitle>Live Preview</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <p className="font-medium text-slate-950">{renderPreview(watchedValues.subject)}</p>
                                    <p className="whitespace-pre-wrap text-sm text-slate-600">{renderPreview(watchedValues.body)}</p>
                                </CardContent>
                            </Card>
                            <Button className="w-full" disabled={saveMutation.isPending} type="submit">
                                Save Template
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
            <ConfirmDialog
                confirmLabel="Delete"
                description="This action cannot be undone. Existing queue drafts will not be modified."
                isDestructive
                isOpen={Boolean(deleteTarget)}
                onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
                onOpenChange={(isOpen) => !isOpen && setDeleteTarget(null)}
                title="Delete template?"
            />
        </div>
    );
}

function sortTemplates(templates: EmailTemplate[], sortBy: string, sortOrder: "asc" | "desc") {
    const sorted = [...templates].sort((first, second) => getTemplateSortValue(first, sortBy).localeCompare(getTemplateSortValue(second, sortBy)));

    return sortOrder === "asc" ? sorted : sorted.reverse();
}

function getTemplateSortValue(template: EmailTemplate, sortBy: string) {
    if (sortBy === "name") {
        return template.name;
    }

    if (sortBy === "type") {
        return template.email_type;
    }

    if (sortBy === "sensitive") {
        return String(template.is_sensitive);
    }

    if (sortBy === "updatedAt") {
        return template.updated_at;
    }

    return "";
}

function FormInput({ control, label, name }: { control: ReturnType<typeof useForm<TemplateFormValues>>["control"]; label: string; name: keyof TemplateFormValues }) {
    return (
        <Controller
            control={control}
            name={name}
            render={({ field, fieldState }) => (
                <div className="space-y-2">
                    <Label>{label}</Label>
                    <Input {...field} value={String(field.value || "")} />
                    {fieldState.error && <p className="text-xs text-red-600">{fieldState.error.message}</p>}
                </div>
            )}
        />
    );
}

function TemplateCardGrid({ onDelete, onEdit, templates }: { onDelete: (template: EmailTemplate) => void; onEdit: (template: EmailTemplate) => void; templates: EmailTemplate[] }) {
    if (templates.length === 0) {
        return <EmptyState description="Create your first recruitment email template." icon={Mail} title="No templates yet" />;
    }

    return (
        <div className="grid gap-4 md:grid-cols-2">
            {templates.map((template) => (
                <Card key={template.id}>
                    <CardHeader>
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <CardTitle>{template.name}</CardTitle>
                                <CardDescription>{template.email_type}</CardDescription>
                            </div>
                            {template.is_sensitive && <StatusBadge sensitive value="SENSITIVE" />}
                        </div>
                    </CardHeader>
                    <CardContent>
                        <p className="line-clamp-3 text-sm text-slate-600">{template.body}</p>
                        <div className="mt-4 flex gap-2">
                            <Button onClick={() => onEdit(template)} size="sm" variant="secondary">Edit</Button>
                            <Button onClick={() => onDelete(template)} size="sm" variant="outline">Delete</Button>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}

function toTemplatePayload(values: TemplateFormValues) {
    return {
        name: values.name,
        email_type: values.email_type,
        subject: values.subject,
        body: values.body,
        required_placeholders: values.required_placeholders.split(",").map((item) => item.trim()).filter(Boolean),
        is_sensitive: values.is_sensitive,
    };
}

function renderPreview(value: string) {
    return value
        .replaceAll("{{candidate_name}}", "Nguyen Minh An")
        .replaceAll("{{position}}", "Frontend Developer")
        .replaceAll("{{interview_time}}", "2026-08-06 09:00")
        .replaceAll("{{interviewer}}", "Linh Tran")
        .replaceAll("{{company_name}}", "HiLab");
}
