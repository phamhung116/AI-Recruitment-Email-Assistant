import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CANDIDATE_STATUSES, isCandidateStatus } from "@/constants/candidateWorkflow";
import type { CandidateStatus } from "@/types/recruitment";

interface CandidateStatusSelectProps {
    id: string;
    label?: string;
    onChange: (status: CandidateStatus) => void;
    value: CandidateStatus;
}

export function CandidateStatusSelect({ id, label = "Status", onChange, value }: CandidateStatusSelectProps) {
    return (
        <div className="space-y-2">
            <Label htmlFor={id}>{label}</Label>
            <Select
                onValueChange={(nextValue) => isCandidateStatus(nextValue) && onChange(nextValue)}
                value={value}
            >
                <SelectTrigger aria-label={label} id={id}>
                    <SelectValue />
                </SelectTrigger>
                <SelectContent>
                    {CANDIDATE_STATUSES.map((status) => (
                        <SelectItem key={status} value={status}>{status}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}
