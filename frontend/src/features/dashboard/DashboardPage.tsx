import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, FlaskConical, Inbox, MailCheck, Users } from "lucide-react";
import type { ReactNode } from "react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Line,
    LineChart,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

import { ActivityTimeline } from "@/components/shared/ActivityTimeline";
import { ErrorState } from "@/components/shared/ErrorState";
import { KPIStatCard } from "@/components/shared/KPIStatCard";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { HILAB_CHART_PALETTE, HILAB_CHART_SERIES } from "@/constants/chartPalette";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { recruitmentApi } from "@/services/recruitmentApi";

export function DashboardPage() {
    const statsQuery = useQuery({
        queryKey: QUERY_KEYS.DASHBOARD,
        queryFn: recruitmentApi.getDashboardStats,
    });
    const candidatesQuery = useQuery({
        queryKey: QUERY_KEYS.CANDIDATES,
        queryFn: () => recruitmentApi.getCandidates(),
    });
    const queueQuery = useQuery({
        queryKey: QUERY_KEYS.EMAIL_QUEUE,
        queryFn: recruitmentApi.getEmailQueue,
    });
    const auditQuery = useQuery({
        queryKey: QUERY_KEYS.AUDIT_LOGS,
        queryFn: recruitmentApi.getAuditLogs,
        retry: false,
    });

    const isLoading = statsQuery.isLoading || candidatesQuery.isLoading || queueQuery.isLoading;
    const error = statsQuery.error || candidatesQuery.error || queueQuery.error;

    const candidateStatusData = Object.entries(
        (candidatesQuery.data || []).reduce<Record<string, number>>((result, candidate) => {
            result[candidate.status] = (result[candidate.status] || 0) + 1;
            return result;
        }, {}),
    ).map(([name, value]) => ({ name, value }));

    const queueStatusData = Object.entries(
        (queueQuery.data || []).reduce<Record<string, number>>((result, item) => {
            result[item.status] = (result[item.status] || 0) + 1;
            return result;
        }, {}),
    ).map(([name, value]) => ({ name, value }));

    const emailActivityData = buildEmailActivityData(queueQuery.data || []);

    return (
        <div className="space-y-6">
            <PageHeader
                description="Monitor recruitment email operations, approvals, and candidate pipeline health."
                title="Dashboard"
            />
            {error && <ErrorState message={error.message} />}
            {isLoading ? (
                <LoadingSkeleton rows={6} />
            ) : (
                <>
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <KPIStatCard
                            description="Active candidate records"
                            icon={Users}
                            label="Total Candidates"
                            trend="+0.0%"
                            value={statsQuery.data?.total_candidates || 0}
                        />
                        <KPIStatCard
                            description="Drafts and approvals waiting"
                            icon={Inbox}
                            label="Pending Emails"
                            trend="Review"
                            value={statsQuery.data?.pending_emails || 0}
                        />
                        <KPIStatCard
                            description="Recorded demo deliveries"
                            icon={FlaskConical}
                            label="Simulated Sends"
                            trend="+0.0%"
                            value={statsQuery.data?.sent_emails || 0}
                        />
                        <KPIStatCard
                            description="Simulation needs investigation"
                            icon={AlertTriangle}
                            label="Failed Emails"
                            trend="Watch"
                            value={statsQuery.data?.failed_emails || 0}
                        />
                    </div>
                    <div className="grid gap-4 xl:grid-cols-3">
                        <ChartCard description="Candidates grouped by recruitment status." title="Candidate Status">
                            <ResponsiveContainer height={260} width="100%">
                                <BarChart data={candidateStatusData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="name" fontSize={11} tickLine={false} />
                                    <YAxis allowDecimals={false} fontSize={12} tickLine={false} />
                                    <Tooltip />
                                    <Bar dataKey="value" fill={HILAB_CHART_PALETTE.primary} radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </ChartCard>
                        <ChartCard description="Operational queue distribution." title="Email Queue Status">
                            <ResponsiveContainer height={260} width="100%">
                                <PieChart>
                                    <Pie data={queueStatusData} dataKey="value" innerRadius={58} nameKey="name" outerRadius={92}>
                                        {queueStatusData.map((entry, index) => (
                                            <Cell fill={HILAB_CHART_SERIES[index % HILAB_CHART_SERIES.length]} key={entry.name} />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                        </ChartCard>
                        <ChartCard description="Email actions by day." title="Email Activity">
                            <ResponsiveContainer height={260} width="100%">
                                <LineChart data={emailActivityData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="date" fontSize={12} tickLine={false} />
                                    <YAxis allowDecimals={false} fontSize={12} tickLine={false} />
                                    <Tooltip />
                                    <Line dataKey="emails" stroke={HILAB_CHART_PALETTE.primary} strokeWidth={2} type="monotone" />
                                </LineChart>
                            </ResponsiveContainer>
                        </ChartCard>
                    </div>
                    <Card>
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <MailCheck className="h-4 w-4 text-primary-500" />
                                <CardTitle>Recent Activities</CardTitle>
                            </div>
                            <CardDescription>Latest audit events from recruitment workflow.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ActivityTimeline
                                items={(auditQuery.data || []).slice(0, 6).map((item) => ({
                                    title: item.action,
                                    description: `${item.entity_type || "entity"} #${item.entity_id || "-"}`,
                                    time: item.created_at,
                                    status: item.actor || "System",
                                }))}
                            />
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
}

function ChartCard({ children, description, title }: { children: ReactNode; description: string; title: string }) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>{children}</CardContent>
        </Card>
    );
}

function buildEmailActivityData(items: { created_at: string }[]) {
    const byDate = items.reduce<Record<string, number>>((result, item) => {
        const date = new Date(item.created_at).toISOString().slice(5, 10);
        result[date] = (result[date] || 0) + 1;
        return result;
    }, {});

    return Object.entries(byDate).map(([date, emails]) => ({ date, emails }));
}
