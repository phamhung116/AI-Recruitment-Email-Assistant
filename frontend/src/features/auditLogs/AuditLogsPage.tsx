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
import type { AuditEvent } from "@/types/recruitment";

export function AuditLogsPage() {
    const [search, setSearch] = useState("");
    const auditQuery = useQuery({
        queryKey: QUERY_KEYS.AUDIT_LOGS,
        queryFn: recruitmentApi.getAuditLogs,
        retry: false,
    });
    const filteredLogs = useMemo(() => {
        return (auditQuery.data?.items || []).filter((item) => {
            const text = `${item.event_name} ${item.actor} ${item.entity_type} ${JSON.stringify(item.payload_json)}`;
            return !search || text.toLowerCase().includes(search.toLowerCase());
        });
    }, [auditQuery.data, search]);
    const columns: DataTableColumn<AuditEvent>[] = [
        {
            key: "action",
            header: "Action",
            render: (item) => <span className="font-medium text-slate-950">{item.event_name}</span>,
        },
        {
            key: "user",
            header: "User",
            render: (item) => item.actor,
        },
        {
            key: "entity",
            header: "Entity",
            render: (item) => `${item.entity_type} #${item.entity_id}`,
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
                    {JSON.stringify(item.payload_json)}
                </code>
            ),
        },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                description="Immutable event trail for imports, protected drafts, provider sends and governed resolutions."
                title="Audit Logs"
            />
            <SearchFilterBar
                onSearchChange={setSearch}
                searchPlaceholder="Search action, user, entity, detail..."
                searchValue={search}
            />
            {auditQuery.error && <ErrorState message={auditQuery.error.message} />}
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
