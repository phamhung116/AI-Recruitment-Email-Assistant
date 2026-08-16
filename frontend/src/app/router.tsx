import { createBrowserRouter } from "react-router-dom";
import { lazy, Suspense } from "react";
import type { ReactNode } from "react";

import { AppLayout } from "@/components/layout/AppLayout";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";

const AuditLogsPage = lazy(() => import("@/features/auditLogs/AuditLogsPage").then((module) => ({ default: module.AuditLogsPage })));
const CandidateDetailPage = lazy(() => import("@/features/candidates/CandidateDetailPage").then((module) => ({ default: module.CandidateDetailPage })));
const CandidatesPage = lazy(() => import("@/features/candidates/CandidatesPage").then((module) => ({ default: module.CandidatesPage })));
const DashboardPage = lazy(() => import("@/features/dashboard/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const EmailQueuePage = lazy(() => import("@/features/emailQueue/EmailQueuePage").then((module) => ({ default: module.EmailQueuePage })));

function withSuspense(page: ReactNode) {
    return (
        <Suspense fallback={<LoadingSkeleton rows={8} />}>
            {page}
        </Suspense>
    );
}

export const router = createBrowserRouter([
    {
        path: "/",
        element: <AppLayout />,
        children: [
            {
                index: true,
                element: withSuspense(<DashboardPage />),
            },
            {
                path: "candidates",
                element: withSuspense(<CandidatesPage />),
            },
            {
                path: "candidates/:candidateId",
                element: withSuspense(<CandidateDetailPage />),
            },
            {
                path: "email-operations",
                element: withSuspense(<EmailQueuePage />),
            },
            {
                path: "audit-logs",
                element: withSuspense(<AuditLogsPage />),
            },
        ],
    },
]);
