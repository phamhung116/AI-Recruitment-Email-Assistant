import { create } from "zustand";

type ToastVariant = "success" | "warning" | "error" | "info";

interface ToastState {
    id: number;
    message: string;
    variant: ToastVariant;
}

interface UiStore {
    closeMobileSidebar: () => void;
    isSidebarCollapsed: boolean;
    isMobileSidebarOpen: boolean;
    toast: ToastState | null;
    hideToast: () => void;
    showToast: (message: string, variant?: ToastVariant) => void;
    toggleMobileSidebar: () => void;
    toggleSidebar: () => void;
}

export const useUiStore = create<UiStore>((set) => ({
    isSidebarCollapsed: false,
    isMobileSidebarOpen: false,
    toast: null,
    closeMobileSidebar: () => set({ isMobileSidebarOpen: false }),
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
    toggleMobileSidebar: () => set((state) => ({ isMobileSidebarOpen: !state.isMobileSidebarOpen })),
    toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
}));
