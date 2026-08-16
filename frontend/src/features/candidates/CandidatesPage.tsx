import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, FileSpreadsheet, Upload, Users } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchFilterBar } from "@/components/shared/SearchFilterBar";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatDateTime, formatRelativeDateTime } from "@/lib/date";
import { recruitmentApi, type CandidateFilters } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { Candidate, ImportPreviewResult } from "@/types/recruitment";

const ALL = "ALL";
const STAGES = ["CV_SCREENING", "INTERVIEW"];
const STATUSES = ["PENDING", "PASS_CV", "REJECT_CV", "PASS_INTERVIEW", "REJECT_INTERVIEW"];
const SORT_KEYS: Record<string, string> = {
    name: "full_name",
    appliedAt: "created_at",
    updatedAt: "updated_at",
};

export function CandidatesPage() {
    const navigate = useNavigate();
    const [isImportOpen, setImportOpen] = useState(false);
    const [filters, setFilters] = useState<CandidateFilters>({ page: 1, page_size: 20, sort: "updated_at", direction: "desc" });
    const candidatesQuery = useQuery({
        queryKey: [...QUERY_KEYS.CANDIDATES, filters],
        queryFn: () => recruitmentApi.getCandidates(filters),
    });
    const items = candidatesQuery.data?.items ?? [];
    const columns: DataTableColumn<Candidate>[] = [
        { key: "name", header: "Name", sortable: true, render: (item) => <span className="font-medium text-slate-950">{item.full_name}</span> },
        { key: "application", header: "Application ID", render: (item) => item.application_id },
        { key: "email", header: "Email", render: (item) => item.email },
        { key: "position", header: "Position", render: (item) => item.position || "-" },
        { key: "stage", header: "Stage", render: (item) => item.stage },
        { key: "status", header: "Status", render: (item) => <StatusBadge value={item.status} /> },
        { key: "appliedAt", header: "Applied At", sortable: true, render: (item) => formatDateTime(item.created_at) },
        { key: "updatedAt", header: "Updated", sortable: true, render: (item) => formatRelativeDateTime(item.updated_at) },
    ];

    function updateFilters(next: Partial<CandidateFilters>) {
        setFilters((current) => ({ ...current, ...next, page: next.page ?? 1 }));
    }

    return (
        <div className="space-y-6">
            <PageHeader
                actions={<Button onClick={() => setImportOpen(true)} variant="secondary"><Upload className="h-4 w-4" />Import Excel</Button>}
                description="Review candidate applications before creating protected recruitment emails."
                title="Candidates"
            />
            <SearchFilterBar
                onSearchChange={(search) => updateFilters({ search })}
                searchPlaceholder="Search name or application ID..."
                searchValue={filters.search ?? ""}
            >
                <FilterSelect label="Stage" options={STAGES} value={filters.stage ?? ALL} onChange={(stage) => updateFilters({ stage: stage === ALL ? undefined : stage })} />
                <FilterSelect label="Status" options={STATUSES} value={filters.status ?? ALL} onChange={(status) => updateFilters({ status: status === ALL ? undefined : status })} />
            </SearchFilterBar>
            {candidatesQuery.error && <ErrorState message={candidatesQuery.error.message} />}
            {candidatesQuery.isLoading ? <LoadingSkeleton rows={8} /> : (
                <>
                    <DataTable
                        columns={columns}
                        data={items}
                        emptyState={<EmptyState actionLabel="Import Excel" description="Import validated candidate applications to begin." icon={Users} onAction={() => setImportOpen(true)} title="No candidates found" />}
                        getRowId={(item) => item.id}
                        onRowClick={(item) => navigate(`/candidates/${item.id}`)}
                        onSortChange={(key, direction) => updateFilters({ sort: SORT_KEYS[key], direction })}
                        sortBy={Object.entries(SORT_KEYS).find(([, value]) => value === filters.sort)?.[0]}
                        sortOrder={filters.direction}
                    />
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                        <span>{candidatesQuery.data?.total ?? 0} applications</span>
                        <div className="flex items-center gap-2">
                            <Button aria-label="Previous page" disabled={(filters.page ?? 1) <= 1} onClick={() => updateFilters({ page: (filters.page ?? 1) - 1 })} size="icon" variant="secondary"><ChevronLeft className="h-4 w-4" /></Button>
                            <span>Page {candidatesQuery.data?.page ?? 1} of {candidatesQuery.data?.pages ?? 1}</span>
                            <Button aria-label="Next page" disabled={(filters.page ?? 1) >= (candidatesQuery.data?.pages ?? 1)} onClick={() => updateFilters({ page: (filters.page ?? 1) + 1 })} size="icon" variant="secondary"><ChevronRight className="h-4 w-4" /></Button>
                        </div>
                    </div>
                </>
            )}
            <ImportCandidatesDialog isOpen={isImportOpen} onOpenChange={setImportOpen} />
        </div>
    );
}

function FilterSelect({ label, onChange, options, value }: { label: string; onChange: (value: string) => void; options: string[]; value: string }) {
    return <Select onValueChange={onChange} value={value}><SelectTrigger className="w-full sm:w-48"><SelectValue placeholder={label} /></SelectTrigger><SelectContent><SelectItem value={ALL}>All {label.toLowerCase()}s</SelectItem>{options.map((option) => <SelectItem key={option} value={option}>{option}</SelectItem>)}</SelectContent></Select>;
}

function ImportCandidatesDialog({ isOpen, onOpenChange }: { isOpen: boolean; onOpenChange: (open: boolean) => void }) {
    const inputRef = useRef<HTMLInputElement>(null);
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<ImportPreviewResult | null>(null);
    const previewMutation = useMutation({
        mutationFn: recruitmentApi.previewCandidateImport,
        onSuccess: setPreview,
        onError: (error) => showToast(error.message, "error"),
    });
    const importMutation = useMutation({
        mutationFn: (selectedFile: File) => recruitmentApi.importCandidates(selectedFile),
        onSuccess: async (result) => {
            showToast(`Imported ${result.imported} candidate(s)`, "success");
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CANDIDATES });
            close();
        },
        onError: (error) => showToast(error.message, "error"),
    });

    function chooseFile(selected?: File) {
        if (!selected) return;
        if (!selected.name.toLowerCase().endsWith(".xlsx")) {
            showToast("Please choose an .xlsx Excel file", "warning");
            return;
        }
        setFile(selected);
        setPreview(null);
    }
    function close() {
        setFile(null);
        setPreview(null);
        previewMutation.reset();
        importMutation.reset();
        onOpenChange(false);
    }

    return (
        <Dialog open={isOpen} onOpenChange={(open) => open ? onOpenChange(true) : close()}>
            <DialogContent className="max-h-[90vh] max-w-5xl overflow-y-auto">
                <DialogHeader><DialogTitle>Import Candidates</DialogTitle><DialogDescription>Choose an Excel file, review every row, then confirm persistence.</DialogDescription></DialogHeader>
                <button className="flex min-h-40 w-full flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-muted/40 p-6 text-center hover:bg-primary-50" onClick={() => inputRef.current?.click()} type="button">
                    <FileSpreadsheet className="h-8 w-8 text-primary-500" />
                    <span className="font-medium text-card-foreground">{file?.name ?? "Choose .xlsx file"}</span>
                    <span className="text-sm text-muted-foreground">The file is validated before any row is saved.</span>
                </button>
                <Input accept=".xlsx" className="hidden" onChange={(event) => chooseFile(event.target.files?.[0])} ref={inputRef} type="file" />
                {previewMutation.error && <ErrorState message={previewMutation.error.message} />}
                {preview && <ImportPreview preview={preview} />}
                <DialogFooter>
                    <Button onClick={close} variant="secondary">Close</Button>
                    {!preview && <Button disabled={!file || previewMutation.isPending} onClick={() => file && previewMutation.mutate(file)}>{previewMutation.isPending ? "Validating..." : "Preview Rows"}</Button>}
                    {preview && <Button disabled={preview.valid_rows === 0 || importMutation.isPending || !file} onClick={() => file && importMutation.mutate(file)}>{importMutation.isPending ? "Importing..." : `Import ${preview.valid_rows} valid row(s)`}</Button>}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function ImportPreview({ preview }: { preview: ImportPreviewResult }) {
    return <div className="space-y-3"><div className="grid grid-cols-3 gap-3"><Metric label="Total" value={preview.total_rows} /><Metric label="Valid" value={preview.valid_rows} /><Metric label="Invalid" value={preview.invalid_rows} /></div><div className="max-h-80 overflow-auto rounded-lg border border-border"><table className="min-w-[820px] w-full text-sm"><thead className="sticky top-0 bg-muted"><tr>{["Row", "Result", "Candidate", "Application", "Status", "Reason"].map((header) => <th className="border-b px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground" key={header}>{header}</th>)}</tr></thead><tbody>{preview.rows.map((row) => <tr className="border-b" key={row.row_number}><td className="px-3 py-2">{row.row_number}</td><td className="px-3 py-2"><StatusBadge value={row.is_valid ? "VALID" : "FAILED"} /></td><td className="px-3 py-2 font-medium">{String(row.candidate.full_name ?? "-")}</td><td className="px-3 py-2">{String(row.candidate.application_id ?? "-")}</td><td className="px-3 py-2"><StatusBadge value={String(row.candidate.status ?? "PENDING")} /></td><td className="max-w-md whitespace-normal px-3 py-2 text-muted-foreground">{row.reason ?? "Ready to import"}</td></tr>)}</tbody></table></div></div>;
}

function Metric({ label, value }: { label: string; value: number }) {
    return <div className="rounded-lg border border-border bg-card p-3 text-center"><p className="text-xl font-semibold">{value}</p><p className="text-xs text-muted-foreground">{label}</p></div>;
}
