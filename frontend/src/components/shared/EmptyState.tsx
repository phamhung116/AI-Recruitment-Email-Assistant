import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

interface EmptyStateProps {
    actionLabel?: string;
    description: string;
    icon: LucideIcon;
    onAction?: () => void;
    title: string;
}

export function EmptyState({ actionLabel, description, icon: Icon, onAction, title }: EmptyStateProps) {
    return (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card p-8 text-center">
            <div className="mb-4 rounded-full bg-primary-50 p-3 text-primary-500 dark:bg-primary-950/30 dark:text-primary-300">
                <Icon className="h-6 w-6" />
            </div>
            <h3 className="text-base font-semibold text-card-foreground">{title}</h3>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
            {actionLabel && onAction && (
                <Button className="mt-4" onClick={onAction}>
                    {actionLabel}
                </Button>
            )}
        </div>
    );
}
