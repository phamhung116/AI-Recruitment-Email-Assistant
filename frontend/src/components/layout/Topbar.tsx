import { Bell, Menu, Search } from "lucide-react";
import { useMemo } from "react";
import { useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NAVIGATION_ITEMS } from "@/constants/navigation";

export function Topbar() {
    const location = useLocation();
    const breadcrumb = useMemo(() => {
        const match = NAVIGATION_ITEMS.find((item) => item.href === location.pathname);
        return match?.title || "Workspace";
    }, [location.pathname]);

    return (
        <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-card/95 px-4 backdrop-blur lg:px-6">
            <Button className="lg:hidden" size="icon" variant="ghost">
                <Menu className="h-5 w-5" />
            </Button>
            <div className="min-w-0">
                <p className="text-xs text-muted-foreground">Workspace</p>
                <p className="truncate text-sm font-medium text-card-foreground">{breadcrumb}</p>
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
