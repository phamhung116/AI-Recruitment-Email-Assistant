import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useLayoutEffect, useRef } from "react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface DataTableColumn<TData> {
    key: string;
    header: string;
    className?: string;
    render: (row: TData) => ReactNode;
    sortable?: boolean;
}

interface DataTableProps<TData> {
    columns: DataTableColumn<TData>[];
    data: TData[];
    enableSelection?: boolean;
    emptyState: ReactNode;
    getRowId?: (row: TData) => number | string;
    onRowClick?: (row: TData) => void;
    onSelectionChange?: (selectedIds: Array<number | string>) => void;
    onSortChange?: (key: string, order: "asc" | "desc") => void;
    selectedRowIds?: Array<number | string>;
    sortBy?: string;
    sortOrder?: "asc" | "desc";
}

export function DataTable<TData>({
    columns,
    data,
    enableSelection = false,
    emptyState,
    getRowId,
    onRowClick,
    onSelectionChange,
    onSortChange,
    selectedRowIds = [],
    sortBy,
    sortOrder = "asc",
}: DataTableProps<TData>) {
    const scrollContainerRef = useRef<HTMLDivElement | null>(null);
    const scrollLeftRef = useRef(0);

    useLayoutEffect(() => {
        if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollLeft = scrollLeftRef.current;
        }
    });

    if (data.length === 0) {
        return <>{emptyState}</>;
    }

    const rowIds = data.map((row, index) => getRowId?.(row) ?? index);
    const selectedSet = new Set(selectedRowIds);
    const allRowsSelected = enableSelection && rowIds.length > 0 && rowIds.every((rowId) => selectedSet.has(rowId));

    function handleSort(column: DataTableColumn<TData>) {
        if (!column.sortable || !onSortChange) {
            return;
        }

        const nextOrder = sortBy === column.key && sortOrder === "asc" ? "desc" : "asc";
        onSortChange(column.key, nextOrder);
    }

    function toggleAllRows(isChecked: boolean) {
        onSelectionChange?.(isChecked ? rowIds : []);
    }

    function toggleRow(rowId: number | string, isChecked: boolean) {
        const nextSelected = new Set(selectedRowIds);

        if (isChecked) {
            nextSelected.add(rowId);
        } else {
            nextSelected.delete(rowId);
        }

        onSelectionChange?.(Array.from(nextSelected));
    }

    return (
        <div className="overflow-hidden rounded-lg border border-border bg-card">
            <div
                className="max-h-[640px] overflow-auto"
                onScroll={(event) => {
                    scrollLeftRef.current = event.currentTarget.scrollLeft;
                }}
                ref={scrollContainerRef}
            >
                <table className="min-w-max w-full border-collapse text-sm">
                    <thead className="sticky top-0 z-10 bg-muted/95 backdrop-blur">
                        <tr>
                            {enableSelection && (
                                <th className="w-12 border-b border-border px-4 py-3">
                                    <input
                                        aria-label="Select all rows"
                                        checked={allRowsSelected}
                                        className="h-4 w-4 rounded border-slate-300 text-primary-500 focus:ring-primary-500"
                                        onChange={(event) => toggleAllRows(event.target.checked)}
                                        type="checkbox"
                                    />
                                </th>
                            )}
                            {columns.map((column) => (
                                <th
                                    className={cn("whitespace-nowrap border-b border-border px-4 py-3 text-left text-xs font-semibold uppercase text-muted-foreground", column.className)}
                                    key={column.key}
                                >
                                    <span className="inline-flex items-center gap-1">
                                        {column.header}
                                        {column.sortable && (
                                            <Button
                                                className="h-6 w-6 text-muted-foreground"
                                                onClick={() => handleSort(column)}
                                                size="icon"
                                                variant="ghost"
                                            >
                                                {sortBy === column.key ? (
                                                    sortOrder === "asc" ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />
                                                ) : (
                                                    <ArrowUpDown className="h-3.5 w-3.5" />
                                                )}
                                            </Button>
                                        )}
                                    </span>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row, rowIndex) => {
                            const rowId = rowIds[rowIndex];

                            return (
                                <tr
                                    className={cn("border-b border-border/70 transition-colors hover:bg-muted/70", onRowClick && "cursor-pointer")}
                                    key={rowId}
                                    onClick={() => onRowClick?.(row)}
                                >
                                    {enableSelection && (
                                        <td className="px-4 py-3 align-middle">
                                            <input
                                                aria-label="Select row"
                                                checked={selectedSet.has(rowId)}
                                                className="h-4 w-4 rounded border-slate-300 text-primary-500 focus:ring-primary-500"
                                                onChange={(event) => toggleRow(rowId, event.target.checked)}
                                                onClick={(event) => event.stopPropagation()}
                                                type="checkbox"
                                            />
                                        </td>
                                    )}
                                    {columns.map((column) => (
                                        <td className={cn("whitespace-nowrap px-4 py-3 align-middle text-card-foreground/80", column.className)} key={column.key}>
                                            {column.render(row)}
                                        </td>
                                    ))}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
