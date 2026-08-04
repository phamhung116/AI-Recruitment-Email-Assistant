import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => {
    return (
        <input
            className={cn(
                "h-9 w-full rounded-md border border-input bg-card px-3 text-sm text-card-foreground shadow-sm outline-none placeholder:text-muted-foreground focus:border-primary-500 focus:ring-2 focus:ring-primary-100 disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-70 dark:focus:ring-primary-950/50",
                className,
            )}
            ref={ref}
            {...props}
        />
    );
});

Input.displayName = "Input";
