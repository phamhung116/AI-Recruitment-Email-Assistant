import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet, Plus, Upload, Users } from "lucide-react";
import type { DragEvent } from "react";
import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchFilterBar } from "@/components/shared/SearchFilterBar";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatDateTime } from "@/lib/date";
import { recruitmentApi, type CandidateFilters } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { Candidate, ImportResult } from "@/types/recruitment";

const ALL_VALUE = "ALL";

export function CandidatesPage() {
    const navigate = useNavigate();
    const [filters, setFilters] = useState<CandidateFilters>({});
    const [isImportOpen, setIsImportOpen] = useState(false);
    const candidatesQuery = useQuery({
        queryKey: [...QUERY_KEYS.CANDIDATES, filters],
        queryFn: () => recruitmentApi.getCandidates(filters),
    });
    const candidates = candidatesQuery.data || [];
    const filterOptions = useFilterOptions(candidates);

    const columns: DataTableColumn<Candidate>[] = [
        {
            key: "name",
            header: "Name",
            sortable: true,
            render: (candidate) => <span className="font-medium text-slate-950">{candidate.full_name}</span>,
        },
        {
            key: "email",
            header: "Email",
            render: (candidate) => candidate.email || "-",
        },
        {
            key: "position",
            header: "Position",
            render: (candidate) => candidate.position || "-",
        },
        {
            key: "stage",
            header: "Stage",
            render: (candidate) => candidate.stage || "-",
        },
        {
            key: "status",
            header: "Status",
            render: (candidate) => <StatusBadge value={candidate.status} />,
        },
        {
            key: "interviewTime",
            header: "Interview Time",
            render: (candidate) => formatDateTime(candidate.interview_time),
        },
        {
            key: "updatedAt",
            header: "Updated At",
            sortable: true,
            render: (candidate) => formatDateTime(candidate.updated_at),
        },
        {
            key: "actions",
            header: "Actions",
            render: (candidate) => (
                <Button onClick={() => navigate(`/candidates/${candidate.id}`)} size="sm" variant="secondary">
                    View
                </Button>
            ),
        },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                actions={(
                    <>
                        <Button onClick={() => setIsImportOpen(true)} variant="secondary">
                            <Upload className="h-4 w-4" />
                            Import Excel
                        </Button>
                        <Button>
                            <Plus className="h-4 w-4" />
                            Add Candidate
                        </Button>
                    </>
                )}
                description="Recruitment CRM view for candidate pipeline and email readiness."
                title="Candidates"
            />
            <SearchFilterBar
                onSearchChange={(search) => setFilters((current) => ({ ...current, search }))}
                searchPlaceholder="Search candidate name or email..."
                searchValue={filters.search || ""}
            >
                <FilterSelect
                    onChange={(position) => setFilters((current) => ({ ...current, position: normalizeFilterValue(position) }))}
                    options={filterOptions.positions}
                    placeholder="Position"
                    value={filters.position || ALL_VALUE}
                />
                <FilterSelect
                    onChange={(stage) => setFilters((current) => ({ ...current, stage: normalizeFilterValue(stage) }))}
                    options={filterOptions.stages}
                    placeholder="Stage"
                    value={filters.stage || ALL_VALUE}
                />
                <FilterSelect
                    onChange={(status) => setFilters((current) => ({ ...current, status: normalizeFilterValue(status) }))}
                    options={filterOptions.statuses}
                    placeholder="Status"
                    value={filters.status || ALL_VALUE}
                />
            </SearchFilterBar>
            {candidatesQuery.error && <ErrorState message={candidatesQuery.error.message} />}
            {candidatesQuery.isLoading ? (
                <LoadingSkeleton rows={8} />
            ) : (
                <DataTable
                    columns={columns}
                    data={candidates}
                    emptyState={(
                        <EmptyState
                            description="Import an Excel file or add candidates manually when the backend endpoint is available."
                            icon={Users}
                            onAction={() => setIsImportOpen(true)}
                            actionLabel="Import Excel"
                            title="No candidates found"
                        />
                    )}
                    onRowClick={(candidate) => navigate(`/candidates/${candidate.id}`)}
                />
            )}
            <ImportExcelModal
                isOpen={isImportOpen}
                onOpenChange={setIsImportOpen}
            />
        </div>
    );
}

function ImportExcelModal({ isOpen, onOpenChange }: { isOpen: boolean; onOpenChange: (isOpen: boolean) => void }) {
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [progress, setProgress] = useState(0);
    const [result, setResult] = useState<ImportResult | null>(null);
    const mutation = useMutation({
        mutationFn: (selectedFile: File) => recruitmentApi.importCandidates(selectedFile, setProgress),
        onSuccess: async (importResult) => {
            setResult(importResult);
            showToast(`Imported ${importResult.imported} candidates`, "success");
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CANDIDATES });
            await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DASHBOARD });
        },
        onError: (error) => showToast(error.message, "error"),
    });

    function handleDrop(event: DragEvent<HTMLDivElement>) {
        event.preventDefault();
        const droppedFile = event.dataTransfer.files[0];
        validateAndSetFile(droppedFile);
    }

    function validateAndSetFile(selectedFile?: File) {
        if (!selectedFile) {
            return;
        }

        if (!selectedFile.name.endsWith(".xlsx")) {
            showToast("Please choose a .xlsx file.", "warning");
            return;
        }

        setFile(selectedFile);
        setResult(null);
        setProgress(0);
    }

    return (
        <Dialog onOpenChange={onOpenChange} open={isOpen}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Import Candidates</DialogTitle>
                    <DialogDescription>Upload an Excel file with candidate fields. The backend will validate and persist rows.</DialogDescription>
                </DialogHeader>
                <div
                    className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center transition-colors hover:bg-slate-100"
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={handleDrop}
                >
                    <FileSpreadsheet className="mb-3 h-8 w-8 text-primary-500" />
                    <p className="text-sm font-medium text-slate-900">{file?.name || "Drag and drop .xlsx file here"}</p>
                    <p className="mt-1 text-xs text-slate-500">or choose a file from your computer</p>
                    <Button className="mt-4" onClick={() => fileInputRef.current?.click()} variant="secondary">
                        Choose Excel File
                    </Button>
                    <Input
                        accept=".xlsx"
                        className="hidden"
                        ref={fileInputRef}
                        onChange={(event) => validateAndSetFile(event.target.files?.[0])}
                        type="file"
                    />
                </div>
                {mutation.isPending && <Progress value={progress} />}
                {result && (
                    <div className="grid grid-cols-3 gap-3 rounded-lg border border-slate-200 p-3 text-center text-sm">
                        <Metric label="Total Rows" value={result.imported + result.skipped} />
                        <Metric label="Imported Rows" value={result.imported} />
                        <Metric label="Failed Rows" value={result.skipped} />
                    </div>
                )}
                <DialogFooter>
                    <Button onClick={() => onOpenChange(false)} variant="secondary">Close</Button>
                    <Button disabled={!file || mutation.isPending} onClick={() => file && mutation.mutate(file)}>
                        Upload File
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function Metric({ label, value }: { label: string; value: number }) {
    return (
        <div>
            <p className="text-xl font-semibold text-slate-950">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
        </div>
    );
}

function FilterSelect({ onChange, options, placeholder, value }: { onChange: (value: string) => void; options: string[]; placeholder: string; value: string }) {
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

function normalizeFilterValue(value: string) {
    return value === ALL_VALUE ? undefined : value;
}

function useFilterOptions(candidates: Candidate[]) {
    return useMemo(() => ({
        positions: uniqueCandidateValues(candidates, "position"),
        stages: uniqueCandidateValues(candidates, "stage"),
        statuses: uniqueCandidateValues(candidates, "status"),
    }), [candidates]);
}

function uniqueCandidateValues(candidates: Candidate[], key: keyof Candidate) {
    return Array.from(new Set(candidates.map((candidate) => candidate[key]).filter(Boolean) as string[]));
}
