import { Bell, ChevronRight, Menu, Search } from "lucide-react";
import { useMemo } from "react";
import { Link, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NAVIGATION_ITEMS } from "@/constants/navigation";
import { useUiStore } from "@/stores/uiStore";

export function Topbar() {
    const location = useLocation();
    const toggleMobileSidebar = useUiStore((state) => state.toggleMobileSidebar);
    const breadcrumbs = useMemo(() => {
        return buildBreadcrumbs(location.pathname);
    }, [location.pathname]);

    return (
        <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-card/95 px-4 backdrop-blur lg:px-6">
            <Button className="lg:hidden" onClick={toggleMobileSidebar} size="icon" variant="ghost">
                <Menu className="h-5 w-5" />
            </Button>
            <div className="min-w-0 flex-1 md:flex-none">
                <p className="text-xs text-muted-foreground">Workspace</p>
                <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1 truncate text-sm">
                    {breadcrumbs.map((item, index) => {
                        const isLast = index === breadcrumbs.length - 1;

                        return (
                            <span className="inline-flex min-w-0 items-center gap-1" key={`${item.href}-${item.title}`}>
                                {index > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                                {isLast ? (
                                    <span className="truncate font-medium text-card-foreground">{item.title}</span>
                                ) : (
                                    <Link className="truncate text-muted-foreground transition-colors hover:text-primary-600" to={item.href}>
                                        {item.title}
                                    </Link>
                                )}
                            </span>
                        );
                    })}
                </nav>
            </div>
            <div className="ml-auto hidden w-full max-w-md items-center md:flex">
                <div className="relative w-full">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input className="pl-9" placeholder="Search candidates, emails, templates..." />
                </div>
            </div>
            <Button size="icon" variant="ghost">
                <Bell className="h-5 w-5" />
            </Button>
            <div className="flex items-center gap-3 rounded-full border border-border bg-card py-1 pl-1 pr-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-900 text-xs font-semibold text-white ring-2 ring-primary-100 dark:bg-gray-800 dark:ring-primary-900/60">
                    HR
                </div>
                <div className="hidden text-sm sm:block">
                    <p className="font-medium text-card-foreground">Demo HR</p>
                    <p className="text-xs text-muted-foreground">Recruitment Team</p>
                </div>
            </div>
        </header>
    );
}

function buildBreadcrumbs(pathname: string) {
    const exactMatch = NAVIGATION_ITEMS.find((item) => item.href === pathname);

    if (exactMatch) {
        return exactMatch.href === "/"
            ? [{ title: "Dashboard", href: "/" }]
            : [
                { title: "Dashboard", href: "/" },
                { title: exactMatch.title, href: exactMatch.href },
            ];
    }

    const parentMatch = NAVIGATION_ITEMS
        .filter((item) => item.href !== "/" && pathname.startsWith(`${item.href}/`))
        .sort((first, second) => second.href.length - first.href.length)[0];

    if (!parentMatch) {
        return [
            { title: "Dashboard", href: "/" },
            { title: "Workspace", href: pathname },
        ];
    }

    return [
        { title: "Dashboard", href: "/" },
        { title: parentMatch.title, href: parentMatch.href },
        { title: "Detail", href: pathname },
    ];
}
