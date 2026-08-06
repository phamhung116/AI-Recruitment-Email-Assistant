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
import { formatRelativeDateTime } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import type { EmailHistoryItem } from "@/types/recruitment";

export function EmailHistoryPage() {
    const [search, setSearch] = useState("");
    const [sortBy, setSortBy] = useState("sentAt");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
    const historyQuery = useQuery({
        queryKey: QUERY_KEYS.EMAIL_HISTORY,
        queryFn: () => recruitmentApi.getEmailHistory(),
    });
    const filteredItems = useMemo(() => {
        const items = (historyQuery.data || []).filter((item) => {
            return !search || `${item.candidate?.full_name || ""} ${item.email_type} ${item.to_email}`.toLowerCase().includes(search.toLowerCase());
        });

        return sortItems(items, sortBy, sortOrder);
    }, [historyQuery.data, search, sortBy, sortOrder]);
    const columns: DataTableColumn<EmailHistoryItem>[] = [
        {
            key: "candidate",
            header: "Candidate",
            sortable: true,
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
            sortable: true,
            render: (item) => item.to_email,
        },
        {
            key: "sentBy",
            header: "Sent By",
            sortable: true,
            render: (item) => item.sent_by || "System",
        },
        {
            key: "sentAt",
            header: "Sent At",
            sortable: true,
            render: (item) => formatRelativeDateTime(item.sent_at),
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
                    emptyState={<EmptyState description="Sent emails will appear here after queue simulation succeeds." icon={History} title="No sent emails yet" />}
                    onSortChange={(key, order) => {
                        setSortBy(key);
                        setSortOrder(order);
                    }}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                />
            )}
        </div>
    );
}

function sortItems(items: EmailHistoryItem[], sortBy: string, sortOrder: "asc" | "desc") {
    const sorted = [...items].sort((first, second) => getSortValue(first, sortBy).localeCompare(getSortValue(second, sortBy)));

    return sortOrder === "asc" ? sorted : sorted.reverse();
}

function getSortValue(item: EmailHistoryItem, sortBy: string) {
    if (sortBy === "candidate") {
        return item.candidate?.full_name || "";
    }

    if (sortBy === "emailType") {
        return item.email_type;
    }

    if (sortBy === "recipient") {
        return item.to_email;
    }

    if (sortBy === "sentBy") {
        return item.sent_by || "";
    }

    if (sortBy === "sentAt") {
        return item.sent_at;
    }

    return "";
}
