import {
    Activity,
    BarChart3,
    Inbox,
    UserRoundSearch,
} from "lucide-react";

export const NAVIGATION_ITEMS = [
    {
        title: "Dashboard",
        href: "/",
        icon: BarChart3,
    },
    {
        title: "Candidates",
        href: "/candidates",
        icon: UserRoundSearch,
    },
    {
        title: "Email Operations",
        href: "/email-operations",
        icon: Inbox,
    },
    {
        title: "Audit Logs",
        href: "/audit-logs",
        icon: Activity,
    },
] as const;
