import { create } from "zustand";

type ToastVariant = "success" | "warning" | "error" | "info";

interface ToastState {
    id: number;
    message: string;
    variant: ToastVariant;
}

interface UiStore {
    isSidebarCollapsed: boolean;
    toast: ToastState | null;
    hideToast: () => void;
    showToast: (message: string, variant?: ToastVariant) => void;
    toggleSidebar: () => void;
}

export const useUiStore = create<UiStore>((set) => ({
    isSidebarCollapsed: false,
    toast: null,
    hideToast: () => set({ toast: null }),
    showToast: (message, variant = "info") => {
        set({
            toast: {
                id: Date.now(),
                message,
                variant,
            },
        });
    },
    toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
}));
