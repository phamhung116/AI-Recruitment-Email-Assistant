import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

interface SideDrawerProps {
    children: ReactNode;
    isOpen: boolean;
    onClose: () => void;
    title: string;
}

export function SideDrawer({ children, isOpen, onClose, title }: SideDrawerProps) {
    if (!isOpen) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-40">
            <button
                aria-label="Close drawer"
                className="absolute inset-0 bg-slate-950/40"
                onClick={onClose}
                type="button"
            />
            <aside className="absolute right-0 top-0 flex h-full w-[min(720px,100vw)] flex-col border-l border-border bg-card shadow-2xl">
                <div className="flex h-16 items-center justify-between border-b border-border px-6">
                    <h2 className="text-lg font-semibold text-card-foreground">{title}</h2>
                    <Button onClick={onClose} size="icon" variant="ghost">
                        <X className="h-5 w-5" />
                    </Button>
                </div>
                <div className="flex-1 overflow-auto p-6">{children}</div>
            </aside>
        </div>
    );
}
