import {
    Activity,
    BarChart3,
    History,
    Inbox,
    MailCheck,
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
        title: "Email Templates",
        href: "/email-templates",
        icon: MailCheck,
    },
    {
        title: "Email Queue",
        href: "/email-queue",
        icon: Inbox,
    },
    {
        title: "Email History",
        href: "/email-history",
        icon: History,
    },
    {
        title: "Audit Logs",
        href: "/audit-logs",
        icon: Activity,
    },
] as const;
