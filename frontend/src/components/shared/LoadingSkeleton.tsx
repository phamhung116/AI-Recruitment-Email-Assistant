import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
    className?: string;
    rows?: number;
}

export function LoadingSkeleton({ className, rows = 3 }: LoadingSkeletonProps) {
    return (
        <div className={cn("space-y-3", className)}>
            {Array.from({ length: rows }).map((_, index) => (
                <div
                    className="h-12 animate-pulse rounded-md bg-muted"
                    key={index}
                />
            ))}
        </div>
    );
}
