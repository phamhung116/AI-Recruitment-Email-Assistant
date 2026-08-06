import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { useMemo, useState } from "react";

import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchFilterBar } from "@/components/shared/SearchFilterBar";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatRelativeDateTime } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import type { AuditLogItem } from "@/types/recruitment";

export function AuditLogsPage() {
    const [search, setSearch] = useState("");
    const auditQuery = useQuery({
        queryKey: QUERY_KEYS.AUDIT_LOGS,
        queryFn: recruitmentApi.getAuditLogs,
        retry: false,
    });
    const filteredLogs = useMemo(() => {
        return (auditQuery.data || []).filter((item) => {
            const text = `${item.action} ${item.actor || ""} ${item.entity_type || ""} ${JSON.stringify(item.metadata_json)}`;
            return !search || text.toLowerCase().includes(search.toLowerCase());
        });
    }, [auditQuery.data, search]);
    const columns: DataTableColumn<AuditLogItem>[] = [
        {
            key: "action",
            header: "Action",
            render: (item) => <span className="font-medium text-slate-950">{item.action}</span>,
        },
        {
            key: "user",
            header: "User",
            render: (item) => item.actor || "System",
        },
        {
            key: "entity",
            header: "Entity",
            render: (item) => `${item.entity_type || "-"} #${item.entity_id || "-"}`,
        },
        {
            key: "timestamp",
            header: "Timestamp",
            render: (item) => formatRelativeDateTime(item.created_at),
        },
        {
            key: "detail",
            header: "Detail",
            render: (item) => (
                <code className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">
                    {JSON.stringify(item.metadata_json)}
                </code>
            ),
        },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                description="System-level activity log for generation, Agent review, approvals, simulations, cancellations, and candidate updates."
                title="Audit Logs"
            />
            <SearchFilterBar
                onSearchChange={setSearch}
                searchPlaceholder="Search action, user, entity, detail..."
                searchValue={search}
            />
            {auditQuery.error && <ErrorState message={`${auditQuery.error.message} The frontend is ready for /audit-logs once the backend exposes it.`} />}
            {auditQuery.isLoading ? (
                <LoadingSkeleton rows={8} />
            ) : (
                <DataTable
                    columns={columns}
                    data={filteredLogs}
                    emptyState={<EmptyState description="Audit events will appear after workflow actions are performed." icon={Activity} title="No audit logs yet" />}
                />
            )}
        </div>
    );
}
