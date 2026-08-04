import { Search } from "lucide-react";
import type { ReactNode } from "react";

import { Input } from "@/components/ui/input";

interface SearchFilterBarProps {
    children?: ReactNode;
    onSearchChange: (value: string) => void;
    searchPlaceholder: string;
    searchValue: string;
}

export function SearchFilterBar({ children, onSearchChange, searchPlaceholder, searchValue }: SearchFilterBarProps) {
    return (
        <div className="grid gap-3 rounded-lg border border-border bg-card p-3 lg:grid-cols-[minmax(260px,1fr)_auto]">
            <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                    className="pl-9"
                    onChange={(event) => onSearchChange(event.target.value)}
                    placeholder={searchPlaceholder}
                    value={searchValue}
                />
            </div>
            {children && <div className="grid gap-3 sm:grid-flow-col sm:auto-cols-max">{children}</div>}
        </div>
    );
}
