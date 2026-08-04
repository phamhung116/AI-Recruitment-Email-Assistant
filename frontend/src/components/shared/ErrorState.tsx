import { AlertCircle } from "lucide-react";

export function ErrorState({ message }: { message: string }) {
    return (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
                <p className="font-medium">Something went wrong</p>
                <p>{message}</p>
            </div>
        </div>
    );
}
