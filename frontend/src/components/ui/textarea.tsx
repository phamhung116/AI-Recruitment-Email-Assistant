import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
    return (
        <textarea
            className={cn(
                "min-h-32 w-full resize-y rounded-md border border-input bg-card px-3 py-2 text-sm text-card-foreground shadow-sm outline-none placeholder:text-muted-foreground focus:border-primary-500 focus:ring-2 focus:ring-primary-100 disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-70 dark:focus:ring-primary-950/50",
                className,
            )}
            {...props}
        />
    );
}
