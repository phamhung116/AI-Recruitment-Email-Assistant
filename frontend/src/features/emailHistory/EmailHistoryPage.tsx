import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";
import { useMemo, useState } from "react";

import { DataTable, type DataTableColumn } from "@/components/shared/DataTable";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { SearchFilterBar } from "@/components/shared/SearchFilterBar";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { formatDateTime } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import type { EmailHistoryItem } from "@/types/recruitment";

export function EmailHistoryPage() {
    const [search, setSearch] = useState("");
    const historyQuery = useQuery({
        queryKey: QUERY_KEYS.EMAIL_HISTORY,
        queryFn: () => recruitmentApi.getEmailHistory(),
    });
    const filteredItems = useMemo(() => {
        return (historyQuery.data || []).filter((item) => {
            return !search || `${item.candidate?.full_name || ""} ${item.email_type} ${item.to_email}`.toLowerCase().includes(search.toLowerCase());
        });
    }, [historyQuery.data, search]);
    const columns: DataTableColumn<EmailHistoryItem>[] = [
        {
            key: "candidate",
            header: "Candidate",
            render: (item) => item.candidate?.full_name || `Candidate #${item.candidate_id}`,
        },
        {
            key: "emailType",
            header: "Email Type",
            render: (item) => item.email_type,
        },
        {
            key: "recipient",
            header: "Recipient",
            render: (item) => item.to_email,
        },
        {
            key: "sentBy",
            header: "Recorded By",
            render: (item) => item.sent_by || "System",
        },
        {
            key: "sentAt",
            header: "Simulated At",
            render: (item) => formatDateTime(item.sent_at),
        },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                description="Immutable record of simulated recruitment emails sent to candidates."
                title="Email History"
            />
            <SearchFilterBar
                onSearchChange={setSearch}
                searchPlaceholder="Filter by candidate, email type, recipient..."
                searchValue={search}
            />
            {historyQuery.error && <ErrorState message={historyQuery.error.message} />}
            {historyQuery.isLoading ? (
                <LoadingSkeleton rows={8} />
            ) : (
                <DataTable
                    columns={columns}
                    data={filteredItems}
                    emptyState={<EmptyState description="Simulation records will appear here after a queue simulation succeeds." icon={History} title="No simulated sends yet" />}
                />
            )}
        </div>
    );
}
