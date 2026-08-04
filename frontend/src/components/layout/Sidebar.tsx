import { ChevronLeft, Sparkles } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { NAVIGATION_ITEMS } from "@/constants/navigation";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/uiStore";

export function Sidebar() {
    const isSidebarCollapsed = useUiStore((state) => state.isSidebarCollapsed);
    const toggleSidebar = useUiStore((state) => state.toggleSidebar);

    return (
        <aside
            className={cn(
                "sticky top-0 hidden h-screen shrink-0 border-r border-border bg-card transition-all duration-200 lg:flex lg:flex-col",
                isSidebarCollapsed ? "w-20" : "w-72",
            )}
        >
            <div className="flex h-16 items-center justify-between border-b border-border px-4">
                <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-500 text-white shadow-sm shadow-primary-900/10">
                        <Sparkles className="h-5 w-5" />
                    </div>
                    {!isSidebarCollapsed && (
                        <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-card-foreground">HiLab Technology</p>
                            <p className="truncate text-xs text-muted-foreground">Recruitment Email</p>
                        </div>
                    )}
                </div>
                <Button
                    className="hidden lg:inline-flex"
                    onClick={toggleSidebar}
                    size="icon"
                    variant="ghost"
                >
                    <ChevronLeft className={cn("h-4 w-4 transition-transform", isSidebarCollapsed && "rotate-180")} />
                </Button>
            </div>
            <nav className="space-y-1 p-3">
                {NAVIGATION_ITEMS.map((item) => (
                    <NavLink
                        className={({ isActive }) => cn(
                            "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-primary-50 hover:text-primary-700 dark:hover:bg-primary-950/25 dark:hover:text-primary-100",
                            isActive && "bg-primary-50 text-primary-600 ring-1 ring-primary-100 dark:bg-primary-950/30 dark:text-primary-200 dark:ring-primary-900",
                            isSidebarCollapsed && "justify-center px-0",
                        )}
                        end={item.href === "/"}
                        key={item.href}
                        to={item.href}
                    >
                        <item.icon className="h-4 w-4 shrink-0" />
                        {!isSidebarCollapsed && <span>{item.title}</span>}
                    </NavLink>
                ))}
            </nav>
        </aside>
    );
}
