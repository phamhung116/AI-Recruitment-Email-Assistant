import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

interface ConfirmDialogProps {
    confirmLabel?: string;
    description: string;
    isOpen: boolean;
    isDestructive?: boolean;
    onConfirm: () => void;
    onOpenChange: (isOpen: boolean) => void;
    title: string;
}

export function ConfirmDialog({
    confirmLabel = "Confirm",
    description,
    isDestructive = false,
    isOpen,
    onConfirm,
    onOpenChange,
    title,
}: ConfirmDialogProps) {
    return (
        <Dialog onOpenChange={onOpenChange} open={isOpen}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>{description}</DialogDescription>
                </DialogHeader>
                <DialogFooter>
                    <Button onClick={() => onOpenChange(false)} variant="secondary">
                        Cancel
                    </Button>
                    <Button onClick={onConfirm} variant={isDestructive ? "destructive" : "default"}>
                        {confirmLabel}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
