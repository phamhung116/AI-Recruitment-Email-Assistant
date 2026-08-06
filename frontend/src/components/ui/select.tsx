import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import type { ComponentPropsWithoutRef, ElementRef } from "react";
import { forwardRef } from "react";

import { cn } from "@/lib/utils";

export const Select = SelectPrimitive.Root;
export const SelectValue = SelectPrimitive.Value;

export const SelectTrigger = forwardRef<
    ElementRef<typeof SelectPrimitive.Trigger>,
    ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger> & { hideIcon?: boolean }
>(({ children, className, hideIcon = false, ...props }, ref) => (
    <SelectPrimitive.Trigger
        className={cn(
            "flex h-9 w-full items-center justify-between rounded-md border border-input bg-card px-3 text-sm text-card-foreground shadow-sm outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-primary-950/50",
            className,
        )}
        ref={ref}
        {...props}
    >
        {children}
        {!hideIcon && (
            <SelectPrimitive.Icon asChild>
                <ChevronDown className="h-4 w-4 opacity-60" />
            </SelectPrimitive.Icon>
        )}
    </SelectPrimitive.Trigger>
));

SelectTrigger.displayName = "SelectTrigger";

export const SelectContent = forwardRef<
    ElementRef<typeof SelectPrimitive.Content>,
    ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ children, className, ...props }, ref) => (
    <SelectPrimitive.Portal>
        <SelectPrimitive.Content
            className={cn("z-50 min-w-32 overflow-hidden rounded-md border border-border bg-card shadow-lg", className)}
            ref={ref}
            {...props}
        >
            <SelectPrimitive.Viewport className="p-1">
                {children}
            </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
));

SelectContent.displayName = "SelectContent";

export const SelectItem = forwardRef<
    ElementRef<typeof SelectPrimitive.Item>,
    ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ children, className, ...props }, ref) => (
    <SelectPrimitive.Item
        className={cn("relative flex cursor-pointer select-none items-center rounded-sm px-8 py-2 text-sm outline-none hover:bg-muted data-[disabled]:pointer-events-none data-[disabled]:opacity-50", className)}
        ref={ref}
        {...props}
    >
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
            <SelectPrimitive.ItemIndicator>
                <Check className="h-4 w-4" />
            </SelectPrimitive.ItemIndicator>
        </span>
        <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
));

SelectItem.displayName = "SelectItem";
