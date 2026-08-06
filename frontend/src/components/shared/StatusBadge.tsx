import { ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";

import { STATUS_STYLE_MAP } from "@/constants/statusStyles";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
    endAdornment?: ReactNode;
    value: string;
    sensitive?: boolean;
}

export function StatusBadge({ endAdornment, sensitive = false, value }: StatusBadgeProps) {
    const normalizedValue = normalizeStatusValue(value);
    const statusClassName = sensitive
        ? STATUS_STYLE_MAP.SENSITIVE
        : STATUS_STYLE_MAP[normalizedValue] || "border-slate-200 bg-slate-50 text-slate-700";

    return (
        <span className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium", statusClassName)}>
            {sensitive && <ShieldAlert className="h-3.5 w-3.5" />}
            {normalizedValue}
            {endAdornment}
        </span>
    );
}

function normalizeStatusValue(value: string) {
    return value.trim().toUpperCase().replaceAll("-", "_").replaceAll(" ", "_");
}
