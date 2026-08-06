import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronLeft, ChevronRight, FileSpreadsheet, Upload, Users } from "lucide-react";
import type { DragEvent } from "react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
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
import { CANDIDATE_STATUSES } from "@/constants/candidateStatuses";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatDateTime, formatRelativeDateTime, formatRelativeDateTimeWithActor } from "@/lib/date";
import { cn } from "@/lib/utils";
import { recruitmentApi, type CandidateFilters } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { Candidate, ImportPreviewResult, ImportResult } from "@/types/recruitment";

const ALL_VALUE = "ALL";
const PAGE_SIZE_OPTIONS = [10, 20, 50];
const SORT_KEY_MAP: Record<string, string> = {
    name: "full_name",
    appliedAt: "created_at",
    statusChanged: "status_updated_at",
    updatedAt: "updated_at",
};

type BulkAction = "CHANGE_STATUS" | "DELETE";

export function CandidatesPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [filters, setFilters] = useState<CandidateFilters>({
        page: 1,
        page_size: 10,
        sort_by: "updated_at",
        sort_order: "desc",
    });
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [bulkAction, setBulkAction] = useState<BulkAction | "">("");
    const [bulkStatus, setBulkStatus] = useState<string>("PASS_CV");
    const [isConfirmOpen, setIsConfirmOpen] = useState(false);
    const [isImportOpen, setIsImportOpen] = useState(false);
    const candidatesQuery = useQuery({
        queryKey: [...QUERY_KEYS.CANDIDATES, filters],
        queryFn: () => recruitmentApi.getCandidates(filters),
    });
    const filterOptionsQuery = useQuery({
        queryKey: [...QUERY_KEYS.CANDIDATES, "filter-options"],
        queryFn: recruitmentApi.getCandidateFilterOptions,
    });
    const candidates = candidatesQuery.data?.items || [];
    const filterOptions = filterOptionsQuery.data || { positions: [], stages: [], statuses: [] };
    const currentPage = candidatesQuery.data?.page || filters.page || 1;
    const totalPages = candidatesQuery.data?.pages || 1;

    const statusMutation = useMutation({
        mutationFn: ({ candidateId, status }: { candidateId: number; status: string }) => recruitmentApi.updateCandidateStatus(candidateId, status),
        onSuccess: async () => {
            showToast("Candidate status updated", "success");
            await invalidateCandidateQueries(queryClient);
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const bulkMutation = useMutation({
        mutationFn: () => {
            if (bulkAction === "CHANGE_STATUS") {
                return recruitmentApi.bulkUpdateCandidateStatus(selectedIds, bulkStatus);
            }

            return recruitmentApi.bulkDeleteCandidates(selectedIds);
        },
        onSuccess: async (result) => {
            showToast(`Bulk action completed for ${result.affected} candidate(s)`, "success");
            setSelectedIds([]);
            setBulkAction("");
            setIsConfirmOpen(false);
            await invalidateCandidateQueries(queryClient);
        },
        onError: (error) => showToast(error.message, "error"),
    });

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
            render: (candidate) => (
                <StatusSelect
                    candidate={candidate}
                    disabled={statusMutation.isPending}
                    onChange={(status) => statusMutation.mutate({ candidateId: candidate.id, status })}
                />
            ),
        },
        {
            key: "statusChanged",
            header: "Status Changed",
            sortable: true,
            render: (candidate) => formatRelativeDateTimeWithActor(candidate.status_updated_at, candidate.status_updated_by),
        },
        {
            key: "appliedAt",
            header: "Applied At",
            sortable: true,
            render: (candidate) => formatDateTime(candidate.created_at),
        },
        {
            key: "updatedAt",
            header: "Updated At",
            sortable: true,
            render: (candidate) => formatRelativeDateTime(candidate.updated_at),
        },
    ];

    function updateFilters(nextFilters: Partial<CandidateFilters>) {
        setFilters((current) => ({ ...current, ...nextFilters, page: nextFilters.page || 1 }));
        setSelectedIds([]);
    }

    function handleSortChange(key: string, order: "asc" | "desc") {
        updateFilters({
            sort_by: SORT_KEY_MAP[key] || key,
            sort_order: order,
        });
    }

    function openBulkConfirm() {
        if (!bulkAction) {
            showToast("Please choose a bulk action first.", "warning");
            return;
        }

        setIsConfirmOpen(true);
    }

    return (
        <div className="space-y-6">
            <PageHeader
                actions={(
                    <Button onClick={() => setIsImportOpen(true)} variant="secondary">
                        <Upload className="h-4 w-4" />
                        Import Excel
                    </Button>
                )}
                description="Recruitment CRM view for candidate pipeline and email readiness."
                title="Candidates"
            />
            <SearchFilterBar
                onSearchChange={(search) => updateFilters({ search })}
                searchPlaceholder="Search candidate name or email..."
                searchValue={filters.search || ""}
            >
                <FilterSelect
                    onChange={(position) => updateFilters({ position: normalizeFilterValue(position) })}
                    options={filterOptions.positions}
                    placeholder="Position"
                    value={filters.position || ALL_VALUE}
                />
                <FilterSelect
                    onChange={(stage) => updateFilters({ stage: normalizeFilterValue(stage) })}
                    options={filterOptions.stages}
                    placeholder="Stage"
                    value={filters.stage || ALL_VALUE}
                />
                <FilterSelect
                    onChange={(status) => updateFilters({ status: normalizeFilterValue(status) })}
                    options={filterOptions.statuses.length > 0 ? filterOptions.statuses : CANDIDATE_STATUSES}
                    placeholder="Status"
                    value={filters.status || ALL_VALUE}
                />
            </SearchFilterBar>
            {selectedIds.length > 0 && (
                <div className="flex flex-col gap-3 rounded-lg border border-primary-100 bg-primary-50/70 p-3 md:flex-row md:items-center md:justify-between">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                        <Select onValueChange={(value) => setBulkAction(value as BulkAction)} value={bulkAction}>
                            <SelectTrigger className="min-w-44 bg-white">
                                <SelectValue placeholder="Choose action" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="CHANGE_STATUS">Change status</SelectItem>
                                <SelectItem value="DELETE">Delete</SelectItem>
                            </SelectContent>
                        </Select>
                        {bulkAction === "CHANGE_STATUS" && (
                            <Select onValueChange={setBulkStatus} value={bulkStatus}>
                                <SelectTrigger className="min-w-48 bg-white">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {CANDIDATE_STATUSES.map((status) => (
                                        <SelectItem key={status} value={status}>{status}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        )}
                        <Button onClick={openBulkConfirm} disabled={bulkMutation.isPending}>Confirm</Button>
                    </div>
                    <p className="text-sm font-medium text-slate-900 md:text-right">{selectedIds.length} candidate(s) selected</p>
                </div>
            )}
            {candidatesQuery.error && <ErrorState message={candidatesQuery.error.message} />}
            {candidatesQuery.isLoading ? (
                <LoadingSkeleton rows={8} />
            ) : (
                <>
                    <DataTable
                        columns={columns}
                        data={candidates}
                        enableSelection
                        emptyState={(
                            <EmptyState
                                description="Import an Excel file to populate the candidate pipeline."
                                icon={Users}
                                onAction={() => setIsImportOpen(true)}
                                actionLabel="Import Excel"
                                title="No candidates found"
                            />
                        )}
                        getRowId={(candidate) => candidate.id}
                        onRowClick={(candidate) => navigate(`/candidates/${candidate.id}`)}
                        onSelectionChange={(ids) => setSelectedIds(ids.map(Number))}
                        onSortChange={handleSortChange}
                        selectedRowIds={selectedIds}
                        sortBy={Object.keys(SORT_KEY_MAP).find((key) => SORT_KEY_MAP[key] === filters.sort_by)}
                        sortOrder={filters.sort_order}
                    />
                    <Pagination
                        currentPage={currentPage}
                        onPageChange={(page) => {
                            setSelectedIds([]);
                            setFilters((current) => ({ ...current, page }));
                        }}
                        onPageSizeChange={(pageSize) => {
                            setSelectedIds([]);
                            setFilters((current) => ({ ...current, page: 1, page_size: pageSize }));
                        }}
                        pageSize={filters.page_size || 10}
                        totalItems={candidatesQuery.data?.total || 0}
                        totalPages={totalPages}
                    />
                </>
            )}
            <ImportExcelModal
                isOpen={isImportOpen}
                onOpenChange={setIsImportOpen}
            />
            <ConfirmDialog
                confirmLabel={bulkAction === "DELETE" ? "Delete" : "Confirm"}
                description={bulkAction === "DELETE"
                    ? `Delete ${selectedIds.length} candidate(s)? Related queue and history records will also be removed.`
                    : `Change status of ${selectedIds.length} candidate(s) to ${bulkStatus}?`}
                isDestructive={bulkAction === "DELETE"}
                isOpen={isConfirmOpen}
                onConfirm={() => bulkMutation.mutate()}
                onOpenChange={setIsConfirmOpen}
                title="Confirm bulk action?"
            />
        </div>
    );
}

function StatusSelect({ candidate, disabled, onChange }: { candidate: Candidate; disabled: boolean; onChange: (status: string) => void }) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        function handlePointerDown(event: PointerEvent) {
            if (!containerRef.current?.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }

        document.addEventListener("pointerdown", handlePointerDown);

        return () => document.removeEventListener("pointerdown", handlePointerDown);
    }, [isOpen]);

    function handleStatusChange(status: string) {
        setIsOpen(false);

        if (status !== candidate.status) {
            onChange(status);
        }
    }

    return (
        <div
            className="relative inline-flex"
            onClick={(event) => event.stopPropagation()}
            onPointerDown={(event) => event.stopPropagation()}
            ref={containerRef}
        >
            <button
                className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-primary-100"
                disabled={disabled}
                onClick={() => setIsOpen((current) => !current)}
                type="button"
            >
                <StatusBadge
                    endAdornment={<ChevronDown className="ml-1 h-3.5 w-3.5 opacity-70" />}
                    value={candidate.status}
                />
            </button>
            {isOpen && (
                <div className="absolute left-0 top-full z-50 mt-2 min-w-56 rounded-md border border-border bg-card p-1 shadow-lg">
                    {CANDIDATE_STATUSES.map((status) => (
                        <button
                            className="flex w-full items-center rounded-sm px-2 py-2 text-left transition-colors hover:bg-muted"
                            key={status}
                            onClick={() => handleStatusChange(status)}
                            type="button"
                        >
                            <StatusBadge value={status} />
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

function Pagination({
    currentPage,
    onPageChange,
    onPageSizeChange,
    pageSize,
    totalItems,
    totalPages,
}: {
    currentPage: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
    pageSize: number;
    totalItems: number;
    totalPages: number;
}) {
    return (
        <div className="flex flex-col gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
            <p>
                Page <span className="font-medium text-slate-950">{currentPage}</span> of{" "}
                <span className="font-medium text-slate-950">{totalPages}</span> · {totalItems} candidates
            </p>
            <div className="flex items-center gap-2">
                <Select onValueChange={(value) => onPageSizeChange(Number(value))} value={String(pageSize)}>
                    <SelectTrigger className="w-28">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {PAGE_SIZE_OPTIONS.map((option) => (
                            <SelectItem key={option} value={String(option)}>{option} / page</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <Button disabled={currentPage <= 1} onClick={() => onPageChange(currentPage - 1)} size="icon" variant="secondary">
                    <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button disabled={currentPage >= totalPages} onClick={() => onPageChange(currentPage + 1)} size="icon" variant="secondary">
                    <ChevronRight className="h-4 w-4" />
                </Button>
            </div>
        </div>
    );
}

function ImportExcelModal({ isOpen, onOpenChange }: { isOpen: boolean; onOpenChange: (isOpen: boolean) => void }) {
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [progress, setProgress] = useState(0);
    const [preview, setPreview] = useState<ImportPreviewResult | null>(null);
    const [result, setResult] = useState<ImportResult | null>(null);
    const previewMutation = useMutation({
        mutationFn: (selectedFile: File) => recruitmentApi.previewCandidateImport(selectedFile),
        onSuccess: (previewResult) => {
            setPreview(previewResult);
            setResult(null);
            showToast(
                `Preview completed: ${previewResult.valid_rows} OK, ${previewResult.invalid_rows} failed`,
                previewResult.invalid_rows > 0 ? "warning" : "success",
            );
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const importMutation = useMutation({
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
        setPreview(null);
        setResult(null);
        setProgress(0);
    }

    return (
        <Dialog onOpenChange={onOpenChange} open={isOpen}>
            <DialogContent className="max-h-[calc(100vh-2rem)] max-w-6xl overflow-hidden p-0">
                <div className="flex max-h-[calc(100vh-2rem)] min-h-0 flex-col">
                    <div className="shrink-0 border-b border-border p-6 pb-4">
                        <DialogHeader>
                            <DialogTitle>Import Candidates</DialogTitle>
                            <DialogDescription>Upload an Excel file, review valid and failed rows, then confirm the import.</DialogDescription>
                        </DialogHeader>
                    </div>
                    <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-6">
                        <div
                            className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-center transition-colors hover:bg-slate-100"
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
                        {previewMutation.isPending && <LoadingSkeleton rows={3} />}
                        {preview && <ImportPreviewTable preview={preview} />}
                        {importMutation.isPending && <Progress value={progress} />}
                        {result && (
                            <div className="grid grid-cols-3 gap-3 rounded-lg border border-slate-200 p-3 text-center text-sm">
                                <Metric label="Total Rows" value={result.imported + result.skipped} />
                                <Metric label="Imported Rows" value={result.imported} />
                                <Metric label="Failed Rows" value={result.skipped} />
                            </div>
                        )}
                    </div>
                    <DialogFooter className="shrink-0 border-t border-border bg-card p-4">
                        <Button onClick={() => onOpenChange(false)} variant="secondary">Close</Button>
                        <Button disabled={!file || previewMutation.isPending} onClick={() => file && previewMutation.mutate(file)} variant="secondary">
                            Preview Rows
                        </Button>
                        <Button disabled={!file || !preview || preview.valid_rows === 0 || importMutation.isPending} onClick={() => file && importMutation.mutate(file)}>
                            Confirm Import
                        </Button>
                    </DialogFooter>
                </div>
            </DialogContent>
        </Dialog>
    );
}

function Metric({ label, value }: { label: string; value: number }) {
    return (
        <div className="p-3">
            <p className="text-xl font-semibold text-slate-950">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
        </div>
    );
}

function ImportPreviewTable({ preview }: { preview: ImportPreviewResult }) {
    return (
        <div className="space-y-3">
            <div className="grid grid-cols-3 overflow-hidden rounded-lg border border-slate-200 text-center text-sm">
                <Metric label="Total Rows" value={preview.total_rows} />
                <Metric label="OK Rows" value={preview.valid_rows} />
                <Metric label="Failed Rows" value={preview.invalid_rows} />
            </div>
            <div className="overflow-hidden rounded-lg border border-border">
                <div className="max-h-[44vh] overflow-auto">
                    <table className="min-w-[980px] w-full border-collapse text-sm">
                    <thead className="sticky top-0 z-10 bg-muted">
                        <tr>
                            <th className="w-16 border-b border-border px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Row</th>
                            <th className="w-24 border-b border-border px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Result</th>
                            <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Candidate</th>
                            <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Email</th>
                            <th className="border-b border-border px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Position</th>
                            <th className="w-44 border-b border-border px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Status</th>
                            <th className="w-[320px] border-b border-border px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground">Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        {preview.rows.map((row) => (
                            <tr className={cn("border-b border-border/70", row.is_valid ? "bg-white" : "bg-red-50/35")} key={row.row_number}>
                                <td className="px-3 py-2 text-slate-600">{row.row_number}</td>
                                <td className="px-3 py-2">
                                    <span className={cn("rounded-full px-2 py-1 text-xs font-medium", row.is_valid ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700")}>
                                        {row.is_valid ? "OK" : "Failed"}
                                    </span>
                                </td>
                                <td className="px-3 py-2 font-medium text-slate-900">{row.candidate.full_name || "-"}</td>
                                <td className="px-3 py-2 text-slate-600">{row.candidate.email || "-"}</td>
                                <td className="px-3 py-2 text-slate-600">{row.candidate.position || "-"}</td>
                                <td className="px-3 py-2">
                                    <StatusBadge value={String(row.candidate.status || "PENDING")} />
                                </td>
                                <td className="whitespace-normal px-3 py-2 text-slate-600">{row.reason || "-"}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                </div>
            </div>
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

function normalizeFilterValue(value: string) {
    return value === ALL_VALUE ? undefined : value;
}

async function invalidateCandidateQueries(queryClient: ReturnType<typeof useQueryClient>) {
    await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CANDIDATES });
    await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DASHBOARD });
    await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.AUDIT_LOGS });
}
