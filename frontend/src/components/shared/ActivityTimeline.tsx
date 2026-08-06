import { Circle } from "lucide-react";

import { formatRelativeDateTime } from "@/lib/date";

interface TimelineItem {
    description?: string;
    status?: string;
    time: string;
    title: string;
}

export function ActivityTimeline({ items }: { items: TimelineItem[] }) {
    if (items.length === 0) {
        return <p className="text-sm text-slate-500">No activities yet.</p>;
    }

    return (
        <div className="space-y-4">
            {items.map((item, index) => (
                <div className="flex gap-3" key={`${item.title}-${index}`}>
                    <div className="mt-1 text-primary-500">
                        <Circle className="h-3 w-3 fill-current" />
                    </div>
                    <div>
                        <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-medium text-slate-900">{item.title}</p>
                            {item.status && <span className="text-xs text-slate-500">{item.status}</span>}
                        </div>
                        {item.description && <p className="text-sm text-slate-500">{item.description}</p>}
                        <p className="text-xs text-slate-400">{formatRelativeDateTime(item.time)}</p>
                    </div>
                </div>
            ))}
        </div>
    );
}
