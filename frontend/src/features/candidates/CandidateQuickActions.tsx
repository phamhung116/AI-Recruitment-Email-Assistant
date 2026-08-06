import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, MailPlus, UserRound } from "lucide-react";
import { useState } from "react";

import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { INTERVIEW_STAGE, isCandidateStatus } from "@/constants/candidateWorkflow";
import { QUERY_KEYS } from "@/constants/queryKeys";
import { CandidateStatusSelect } from "@/features/candidates/CandidateStatusSelect";
import { toDateTimeInputValue } from "@/lib/date";
import { recruitmentApi } from "@/services/recruitmentApi";
import { useUiStore } from "@/stores/uiStore";
import type { Candidate, CandidateStatus } from "@/types/recruitment";

interface CandidateQuickActionsProps {
    candidate: Candidate;
    onGenerateDraft: () => void;
}

export function CandidateQuickActions({ candidate, onGenerateDraft }: CandidateQuickActionsProps) {
    const queryClient = useQueryClient();
    const showToast = useUiStore((state) => state.showToast);
    const [isStatusOpen, setIsStatusOpen] = useState(false);
    const [isScheduleOpen, setIsScheduleOpen] = useState(false);
    const [selectedStatus, setSelectedStatus] = useState<CandidateStatus>(getSupportedStatus(candidate.status));
    const [interviewer, setInterviewer] = useState(candidate.interviewer || "");
    const [interviewTime, setInterviewTime] = useState(toDateTimeInputValue(candidate.interview_time));

    async function refreshCandidate(updatedCandidate: Candidate) {
        queryClient.setQueryData([...QUERY_KEYS.CANDIDATES, candidate.id], updatedCandidate);
        await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CANDIDATES });
        await queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DASHBOARD });
    }

    const statusMutation = useMutation({
        mutationFn: () => recruitmentApi.updateCandidate(candidate.id, { status: selectedStatus }),
        onSuccess: async (updatedCandidate) => {
            setIsStatusOpen(false);
            showToast("Candidate status updated", "success");
            await refreshCandidate(updatedCandidate);
        },
        onError: (error) => showToast(error.message, "error"),
    });
    const scheduleMutation = useMutation({
        mutationFn: () => recruitmentApi.updateCandidate(candidate.id, {
            interviewer: interviewer.trim(),
            interview_time: new Date(interviewTime).toISOString(),
            stage: INTERVIEW_STAGE,
        }),
        onSuccess: async (updatedCandidate) => {
            setIsScheduleOpen(false);
            showToast("Interview scheduled", "success");
            await refreshCandidate(updatedCandidate);
        },
        onError: (error) => showToast(error.message, "error"),
    });

    function openStatusDialog() {
        setSelectedStatus(getSupportedStatus(candidate.status));
        setIsStatusOpen(true);
    }

    function openScheduleDialog() {
        setInterviewer(candidate.interviewer || "");
        setInterviewTime(toDateTimeInputValue(candidate.interview_time));
        setIsScheduleOpen(true);
    }

    return (
        <>
            <Card>
                <CardHeader>
                    <CardTitle>Quick Actions</CardTitle>
                    <CardDescription>Common HR operations for this candidate.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    <Button className="w-full justify-start" onClick={onGenerateDraft}>
                        <MailPlus className="h-4 w-4" />
                        Generate Email Draft
                    </Button>
                    <Button className="w-full justify-start" onClick={openStatusDialog} variant="secondary">
                        <UserRound className="h-4 w-4" />
                        Update Status
                    </Button>
                    <Button className="w-full justify-start" onClick={openScheduleDialog} variant="secondary">
                        <CalendarClock className="h-4 w-4" />
                        Schedule Interview
                    </Button>
                    <div className="rounded-lg border border-border bg-muted/30 p-3">
                        <p className="text-xs font-medium uppercase text-muted-foreground">Current Status</p>
                        <div className="mt-2">
                            <StatusBadge value={candidate.status} />
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Dialog onOpenChange={setIsStatusOpen} open={isStatusOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Update Candidate Status</DialogTitle>
                        <DialogDescription>
                            Record the HR decision explicitly. This controls which recruitment email type is allowed.
                        </DialogDescription>
                    </DialogHeader>
                    <CandidateStatusSelect
                        id="quick-action-status"
                        onChange={setSelectedStatus}
                        value={selectedStatus}
                    />
                    <DialogFooter>
                        <Button disabled={statusMutation.isPending} onClick={() => setIsStatusOpen(false)} variant="secondary">Cancel</Button>
                        <Button
                            disabled={statusMutation.isPending || selectedStatus === candidate.status}
                            onClick={() => statusMutation.mutate()}
                        >
                            {statusMutation.isPending ? "Updating..." : "Update Status"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog onOpenChange={setIsScheduleOpen} open={isScheduleOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Schedule Interview</DialogTitle>
                        <DialogDescription>
                            Save the verified interviewer and local interview time. The candidate stage will move to INTERVIEW.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="schedule-interviewer">Interviewer</Label>
                            <Input
                                id="schedule-interviewer"
                                onChange={(event) => setInterviewer(event.target.value)}
                                placeholder="Recruiter or interviewer name"
                                value={interviewer}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="schedule-interview-time">Interview Time</Label>
                            <Input
                                id="schedule-interview-time"
                                onChange={(event) => setInterviewTime(event.target.value)}
                                type="datetime-local"
                                value={interviewTime}
                            />
                        </div>
                    </div>
                    <div className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
                        Stage after scheduling: <span className="font-medium text-card-foreground">INTERVIEW</span>
                    </div>
                    <DialogFooter>
                        <Button disabled={scheduleMutation.isPending} onClick={() => setIsScheduleOpen(false)} variant="secondary">Cancel</Button>
                        <Button
                            disabled={scheduleMutation.isPending || !interviewer.trim() || !interviewTime}
                            onClick={() => scheduleMutation.mutate()}
                        >
                            {scheduleMutation.isPending ? "Scheduling..." : "Schedule Interview"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

function getSupportedStatus(status: string): CandidateStatus {
    return isCandidateStatus(status) ? status : "PENDING";
}
