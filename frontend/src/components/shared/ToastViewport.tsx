import { useEffect } from "react";

import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/uiStore";

const TOAST_CLASS_MAP = {
    error: "border-red-200 bg-red-50 text-red-900",
    info: "border-gray-200 bg-gray-50 text-gray-900 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100",
    success: "border-green-200 bg-green-50 text-green-900",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
};

export function ToastViewport() {
    const hideToast = useUiStore((state) => state.hideToast);
    const toast = useUiStore((state) => state.toast);

    useEffect(() => {
        if (!toast) {
            return;
        }

        const timerId = window.setTimeout(hideToast, 4000);
        return () => window.clearTimeout(timerId);
    }, [hideToast, toast]);

    if (!toast) {
        return null;
    }

    return (
        <div className={cn("fixed right-5 top-5 z-50 w-[min(380px,calc(100vw-2rem))] rounded-lg border p-4 text-sm shadow-lg", TOAST_CLASS_MAP[toast.variant])}>
            {toast.message}
        </div>
    );
}
