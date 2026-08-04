import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface KPIStatCardProps {
    description: string;
    icon: LucideIcon;
    label: string;
    trend: string;
    value: number | string;
}

export function KPIStatCard({ description, icon: Icon, label, trend, value }: KPIStatCardProps) {
    return (
        <Card>
            <CardContent className="p-5">
                <div className="flex items-start justify-between">
                    <div className="space-y-1">
                        <p className="text-sm font-medium text-slate-500">{label}</p>
                        <p className="text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
                    </div>
                    <div className="rounded-md bg-primary-50 p-2 text-primary-500 dark:bg-primary-950/30 dark:text-primary-300">
                        <Icon className="h-5 w-5" />
                    </div>
                </div>
                <div className="mt-4 flex items-center justify-between gap-3 text-xs">
                    <span className="text-slate-500">{description}</span>
                    <span className="font-medium text-primary-500">{trend}</span>
                </div>
            </CardContent>
        </Card>
    );
}
