import * as DialogPrimitive from "@radix-ui/react-dialog";
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
    return (
        <DialogPrimitive.Root onOpenChange={(nextIsOpen) => !nextIsOpen && onClose()} open={isOpen}>
            <DialogPrimitive.Portal>
                <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-slate-950/40" />
                <DialogPrimitive.Content className="fixed right-0 top-0 z-50 flex h-full w-[min(760px,100vw)] flex-col border-l border-border bg-card text-card-foreground shadow-2xl focus:outline-none">
                    <div className="flex h-16 shrink-0 items-center justify-between border-b border-border px-6">
                        <div>
                            <DialogPrimitive.Title className="text-lg font-semibold text-card-foreground">{title}</DialogPrimitive.Title>
                            <DialogPrimitive.Description className="sr-only">Review email content, safety findings, and available workflow actions.</DialogPrimitive.Description>
                        </div>
                        <DialogPrimitive.Close asChild>
                            <Button aria-label="Close review drawer" size="icon" variant="ghost">
                                <X className="h-5 w-5" />
                            </Button>
                        </DialogPrimitive.Close>
                    </div>
                    <div className="flex-1 overflow-auto p-4 sm:p-6">{children}</div>
                </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
    );
}
