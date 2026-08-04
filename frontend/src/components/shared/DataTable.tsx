import { ArrowUpDown } from "lucide-react";
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
    emptyState: ReactNode;
    onRowClick?: (row: TData) => void;
}

export function DataTable<TData>({ columns, data, emptyState, onRowClick }: DataTableProps<TData>) {
    if (data.length === 0) {
        return <>{emptyState}</>;
    }

    return (
        <div className="overflow-hidden rounded-lg border border-border bg-card">
            <div className="max-h-[640px] overflow-auto">
                <table className="w-full border-collapse text-sm">
                    <thead className="sticky top-0 z-10 bg-muted/95 backdrop-blur">
                        <tr>
                            {columns.map((column) => (
                                <th
                                    className={cn("border-b border-border px-4 py-3 text-left text-xs font-semibold uppercase text-muted-foreground", column.className)}
                                    key={column.key}
                                >
                                    <span className="inline-flex items-center gap-1">
                                        {column.header}
                                        {column.sortable && (
                                            <Button
                                                className="h-6 w-6 text-muted-foreground"
                                                size="icon"
                                                variant="ghost"
                                            >
                                                <ArrowUpDown className="h-3.5 w-3.5" />
                                            </Button>
                                        )}
                                    </span>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row, rowIndex) => (
                            <tr
                                className={cn("border-b border-border/70 transition-colors hover:bg-muted/70", onRowClick && "cursor-pointer")}
                                key={rowIndex}
                                onClick={() => onRowClick?.(row)}
                            >
                                {columns.map((column) => (
                                    <td className={cn("px-4 py-3 align-middle text-card-foreground/80", column.className)} key={column.key}>
                                        {column.render(row)}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
