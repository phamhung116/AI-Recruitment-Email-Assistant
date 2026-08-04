import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
    "inline-flex h-9 items-center justify-center gap-2 whitespace-nowrap rounded-md px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:pointer-events-none disabled:opacity-50",
    {
        variants: {
            variant: {
                default: "bg-primary-500 text-white hover:bg-primary-600",
                secondary: "border border-gray-200 bg-white text-gray-800 hover:border-primary-100 hover:bg-primary-50 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100 dark:hover:bg-primary-950/25",
                ghost: "text-gray-700 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-200 dark:hover:bg-gray-800 dark:hover:text-white",
                destructive: "bg-red-600 text-white hover:bg-red-700",
                outline: "border border-primary-500 bg-transparent text-primary-500 hover:bg-primary-50 hover:text-primary-600 dark:border-primary-400 dark:text-primary-300 dark:hover:bg-primary-950/30",
            },
            size: {
                default: "h-9 px-3",
                sm: "h-8 px-2.5 text-xs",
                icon: "h-9 w-9 px-0",
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
    },
);

interface ButtonProps
    extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
    asChild?: boolean;
}

export function Button({ asChild, className, size, type = "button", variant, ...props }: ButtonProps) {
    const Component = asChild ? Slot : "button";

    return (
        <Component
            className={cn(buttonVariants({ variant, size }), className)}
            type={type}
            {...props}
        />
    );
}
