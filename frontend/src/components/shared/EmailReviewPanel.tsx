import {
    AlertCircle,
    Bot,
    CheckCircle2,
    ChevronRight,
    CircleDashed,
    Info,
    RefreshCw,
    ShieldAlert,
    ShieldCheck,
    Sparkles,
    TriangleAlert,
} from "lucide-react";
import { useId, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getAsyncReviewMetadata, getAsyncReviewStatus } from "@/lib/reviewState";
import type {
    AgentReviewResult,
    AsyncReviewStatus,
    DeterministicValidationIssue,
    RiskCheckResult,
} from "@/types/recruitment";

interface EmailReviewPanelProps {
    currentBody: string;
    currentSubject: string;
    isReviewing?: boolean;
    isStale?: boolean;
    onApplySuggestion?: (subject: string, body: string) => void;
    onRequestReview?: () => void;
    queueId?: number;
    riskResult: RiskCheckResult;
}

const SEVERITY_STYLES = {
    info: "border-blue-200 bg-blue-50 text-blue-950",
    warning: "border-amber-200 bg-amber-50 text-amber-950",
    error: "border-red-200 bg-red-50 text-red-950",
    blocker: "border-red-300 bg-red-50 text-red-950",
} as const;

export function EmailReviewPanel({
    currentBody,
    currentSubject,
    isReviewing = false,
    isStale = false,
    onApplySuggestion,
    onRequestReview,
    queueId,
    riskResult,
}: EmailReviewPanelProps) {
    const titleId = useId();
    const deterministicIssues = Array.isArray(riskResult.issues) ? riskResult.issues : [];
    const legacyErrors = Array.isArray(riskResult.errors) ? riskResult.errors : [];
    const agentReview = riskResult.agent_review;
    const asyncReviewStatus = getAsyncReviewStatus(riskResult);
    const asyncReview = getAsyncReviewMetadata(riskResult);
    const agentJourney = agentReview?.trace.filter((step) => ["act", "decide", "finalize", "loop_limit", "observe"].includes(step.step)) || [];
    const hasBlockingIssue = riskResult.passed === false || deterministicIssues.some((issue) => issue.is_blocking);
    const requiresHumanReview = Boolean(riskResult.requires_human_review || agentReview?.requires_human_review);
    const status = getOverallStatus(hasBlockingIssue, requiresHumanReview, agentReview, asyncReviewStatus, isStale);
    const hasSuggestion = Boolean(
        !isStale && agentReview
        && (agentReview.draft_subject !== currentSubject || agentReview.draft_body !== currentBody),
    );

    return (
        <section aria-labelledby={titleId} className="overflow-hidden rounded-lg border border-border bg-card">
            <div className={cn("border-b px-5 py-4", status.containerClassName)} aria-live="polite">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex gap-3">
                        <span className={cn("mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full", status.iconClassName)}>
                            {status.icon}
                        </span>
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Safety review</p>
                            <h3 className="mt-1 text-base font-semibold text-card-foreground" id={titleId}>{status.title}</h3>
                            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{status.description}</p>
                        </div>
                    </div>
                    {onRequestReview && (
                        <Button disabled={isReviewing} onClick={onRequestReview} size="sm" variant="secondary">
                            <RefreshCw className={cn("h-3.5 w-3.5", isReviewing && "animate-spin motion-reduce:animate-none")} />
                            {isReviewing ? "Reviewing..." : "Refresh review"}
                        </Button>
                    )}
                </div>
            </div>

            <div className="space-y-5 p-5">
                <div className="grid gap-2 sm:grid-cols-3">
                    <ReviewSignal
                        icon={<ShieldCheck className="h-4 w-4" />}
                        label="Rule checks"
                        tone={hasBlockingIssue ? "danger" : "success"}
                        value={hasBlockingIssue ? "Blocked" : "Passed"}
                    />
                    <ReviewSignal
                        icon={<Bot className="h-4 w-4" />}
                        label="Review pipeline"
                        tone={reviewPipelineTone(asyncReviewStatus, agentReview, isStale)}
                        value={isStale ? "Save to re-check" : asyncReviewStatus ? reviewStatusLabel(asyncReviewStatus) : agentStatusLabel(agentReview)}
                    />
                    <ReviewSignal
                        icon={<ShieldAlert className="h-4 w-4" />}
                        label="HR checkpoint"
                        tone={requiresHumanReview ? "warning" : "success"}
                        value={requiresHumanReview ? "Required" : "Not required"}
                    />
                </div>

                {(deterministicIssues.length > 0 || legacyErrors.length > 0) && (
                    <ReviewSection title="Rule findings" subtitle="Backend checks that Gemini cannot override.">
                        <div className="space-y-2">
                            {deterministicIssues.map((issue) => (
                                <DeterministicIssueItem issue={issue} key={`${issue.rule_id}-${issue.message}`} />
                            ))}
                            {legacyErrors.map((error) => (
                                <IssueShell icon={<AlertCircle className="h-4 w-4" />} key={error} severity="error" title="Validation error">
                                    <p>{error}</p>
                                </IssueShell>
                            ))}
                        </div>
                    </ReviewSection>
                )}

                {agentReview && (
                    <ReviewSection title="Gemini assessment" subtitle={agentMetadataLabel(agentReview)}>
                        <div className="space-y-3">
                            <p className="text-sm leading-6 text-card-foreground/80">{agentReview.review_summary}</p>
                            {agentReview.uncertainty.has_uncertainty && (
                                <IssueShell icon={<CircleDashed className="h-4 w-4" />} severity="warning" title="Uncertainty detected">
                                    <p>{agentReview.uncertainty.reason || "Gemini could not verify all material facts."}</p>
                                </IssueShell>
                            )}
                            {agentReview.issues.map((issue) => (
                                <IssueShell icon={severityIcon(issue.severity)} key={`${issue.rule_id}-${issue.message}`} severity={issue.severity} title={humanizeRuleId(issue.rule_id)}>
                                    <p>{issue.message}</p>
                                    <p className="mt-1 text-xs opacity-75">Evidence: {issue.evidence}</p>
                                </IssueShell>
                            ))}
                        </div>
                    </ReviewSection>
                )}

                {agentJourney.length > 0 && (
                    <ReviewSection title="Agent review journey" subtitle="The agent chose read-only checks, observed their results, then produced its assessment.">
                        <ol className="relative ml-2 space-y-0 border-l border-slate-200" aria-label="Agent review journey">
                            {agentJourney.map((step, index) => (
                                <AgentJourneyStep
                                    detail={step.detail}
                                    isLast={index === agentJourney.length - 1}
                                    key={`${step.step}-${index}`}
                                    status={step.status}
                                    step={step.step}
                                />
                            ))}
                        </ol>
                    </ReviewSection>
                )}

                {agentReview && hasSuggestion && (
                    <ReviewSection title="Suggested wording" subtitle="Advisory only. Review the changes before saving.">
                        <div className="space-y-3 rounded-md border border-violet-200 bg-violet-50 p-4 text-sm text-violet-950">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">Subject</p>
                                <p className="mt-1 font-medium">{agentReview.draft_subject}</p>
                            </div>
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">Body</p>
                                <p className="mt-1 whitespace-pre-wrap leading-6">{agentReview.draft_body}</p>
                            </div>
                            {onApplySuggestion && (
                                <Button onClick={() => onApplySuggestion(agentReview.draft_subject, agentReview.draft_body)} size="sm" variant="secondary">
                                    <Sparkles className="h-3.5 w-3.5" />
                                    Use suggested wording
                                </Button>
                            )}
                        </div>
                    </ReviewSection>
                )}

                <details className="group rounded-md border border-border bg-muted/40 px-4 py-3 text-sm">
                    <summary className="flex cursor-pointer list-none items-center gap-2 font-medium text-card-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500">
                        <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90 motion-reduce:transition-none" />
                        Technical review details
                    </summary>
                    <div className="mt-3 space-y-2 border-t border-border pt-3 text-xs text-muted-foreground">
                        <dl className="grid gap-2 sm:grid-cols-3">
                            <div>
                                <dt className="font-medium text-card-foreground">Queue ID</dt>
                                <dd>{queueId ? `#${queueId}` : "Unavailable"}</dd>
                            </div>
                            <div>
                                <dt className="font-medium text-card-foreground">Draft version</dt>
                                <dd>{riskResult.draft_version ?? asyncReview?.draft_version ?? "Unavailable"}</dd>
                            </div>
                            <div>
                                <dt className="font-medium text-card-foreground">Review version</dt>
                                <dd>{asyncReview?.review_version ?? "Pending"}</dd>
                            </div>
                        </dl>
                        <p>Deterministic check: {riskResult.checked_at ? new Date(riskResult.checked_at).toLocaleString() : "Timestamp unavailable"}</p>
                        {agentReview && (
                            <p>
                                Provider: {agentReview.model_metadata.provider} / Model: {agentReview.model_metadata.model} / Prompt: {agentReview.model_metadata.prompt_version}
                                {` / Model calls: ${agentReview.model_metadata.attempts}`}
                                {agentReview.model_metadata.loop_steps !== undefined && ` / Loop steps: ${agentReview.model_metadata.loop_steps}`}
                                {agentReview.model_metadata.tool_calls !== undefined && ` / Tools: ${agentReview.model_metadata.tool_calls}`}
                            </p>
                        )}
                    </div>
                </details>
            </div>
        </section>
    );
}

export function ReviewStatusBadge({ riskResult }: { riskResult: RiskCheckResult }) {
    const agentReview = riskResult.agent_review;
    const asyncReviewStatus = getAsyncReviewStatus(riskResult);
    const hasBlockingIssue = riskResult.passed === false || riskResult.issues?.some((issue) => issue.is_blocking) === true;
    const requiresHumanReview = Boolean(riskResult.requires_human_review || agentReview?.requires_human_review);
    const status = getOverallStatus(hasBlockingIssue, requiresHumanReview, agentReview, asyncReviewStatus, false);

    return (
        <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium", status.badgeClassName)}>
            {status.smallIcon}
            {asyncReviewStatus ? reviewStatusLabel(asyncReviewStatus) : status.shortTitle}
        </span>
    );
}

function DeterministicIssueItem({ issue }: { issue: DeterministicValidationIssue }) {
    return (
        <IssueShell icon={severityIcon(issue.severity)} severity={issue.severity} title={humanizeRuleId(issue.rule_id)}>
            <p>{issue.message}</p>
            {issue.remediation && <p className="mt-1 text-xs opacity-75">Next action: {issue.remediation}</p>}
        </IssueShell>
    );
}

function ReviewSection({ children, subtitle, title }: { children: ReactNode; subtitle: string; title: string }) {
    return (
        <div>
            <div className="mb-2">
                <h4 className="text-sm font-semibold text-card-foreground">{title}</h4>
                <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
            </div>
            {children}
        </div>
    );
}

function IssueShell({ children, icon, severity, title }: { children: ReactNode; icon: ReactNode; severity: keyof typeof SEVERITY_STYLES; title: string }) {
    return (
        <div className={cn("flex gap-3 rounded-md border p-3 text-sm", SEVERITY_STYLES[severity])}>
            <span className="mt-0.5 shrink-0">{icon}</span>
            <div className="min-w-0">
                <p className="font-semibold">{title}</p>
                <div className="mt-1 leading-5">{children}</div>
            </div>
        </div>
    );
}

function ReviewSignal({ icon, label, tone, value }: { icon: ReactNode; label: string; tone: "danger" | "neutral" | "success" | "warning"; value: string }) {
    const toneClassNames = {
        danger: "border-red-200 bg-red-50 text-red-900",
        neutral: "border-slate-200 bg-slate-50 text-slate-700",
        success: "border-emerald-200 bg-emerald-50 text-emerald-900",
        warning: "border-amber-200 bg-amber-50 text-amber-900",
    };

    return (
        <div className={cn("rounded-md border px-3 py-2.5", toneClassNames[tone])}>
            <div className="flex items-center gap-2 text-xs font-medium opacity-75">{icon}{label}</div>
            <p className="mt-1 text-sm font-semibold">{value}</p>
        </div>
    );
}

function AgentJourneyStep({ detail, isLast, status, step }: { detail: string; isLast: boolean; status: string; step: string }) {
    const presentation = journeyPresentation(step, status);
    return (
        <li className={cn("relative ml-5 pb-4", isLast && "pb-0")}>
            <span className={cn("absolute -left-[29px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-white", presentation.dotClassName)} aria-hidden="true" />
            <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-2">
                <p className="text-sm font-medium text-card-foreground">{presentation.label}</p>
                <span className={cn("w-fit rounded-full px-2 py-0.5 text-[11px] font-medium", presentation.badgeClassName)}>{statusLabel(status)}</span>
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
        </li>
    );
}

function journeyPresentation(step: string, status: string) {
    const failed = ["blocked", "failed", "rejected", "unavailable"].includes(status);
    const base = {
        badgeClassName: failed ? "bg-red-50 text-red-700" : "bg-slate-100 text-slate-600",
        dotClassName: failed ? "bg-red-500" : "bg-primary-500",
    };
    if (step === "decide") return { ...base, label: "Agent chose the next step" };
    if (step === "act") return { ...base, label: "Backend ran a safe tool" };
    if (step === "observe") return { ...base, label: "Agent observed the tool result" };
    if (step === "finalize") return { ...base, label: "Agent created the final assessment" };
    return { ...base, label: "Agent loop stopped safely" };
}

function statusLabel(status: string) {
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
}

function getOverallStatus(
    hasBlockingIssue: boolean,
    requiresHumanReview: boolean,
    agentReview: AgentReviewResult | undefined,
    asyncReviewStatus: AsyncReviewStatus | null,
    isStale: boolean,
) {
    if (isStale) {
        return {
            badgeClassName: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100",
            containerClassName: "border-amber-200 bg-amber-50/70 dark:border-amber-900 dark:bg-amber-950/20",
            description: "The content has changed since the displayed checks. Save to validate and review the new version.",
            icon: <TriangleAlert className="h-5 w-5" />,
            iconClassName: "bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-200",
            shortTitle: "Review stale",
            smallIcon: <TriangleAlert className="h-3.5 w-3.5" />,
            title: "Unsaved changes need review",
        };
    }
    if (asyncReviewStatus === "QUEUED") {
        return {
            badgeClassName: "border-blue-200 bg-blue-50 text-blue-900",
            containerClassName: "border-blue-200 bg-blue-50/70",
            description: "The draft is safely stored. The dispatcher will send this version to the review worker.",
            icon: <CircleDashed className="h-5 w-5" />,
            iconClassName: "bg-blue-100 text-blue-700",
            shortTitle: "Queued",
            smallIcon: <CircleDashed className="h-3.5 w-3.5" />,
            title: "Draft saved – review queued",
        };
    }
    if (asyncReviewStatus === "REVIEWING") {
        return {
            badgeClassName: "border-violet-200 bg-violet-50 text-violet-900",
            containerClassName: "border-violet-200 bg-violet-50/70",
            description: "The worker is checking this exact draft version. This panel updates automatically.",
            icon: <RefreshCw className="h-5 w-5 animate-spin motion-reduce:animate-none" />,
            iconClassName: "bg-violet-100 text-violet-700",
            shortTitle: "Reviewing",
            smallIcon: <RefreshCw className="h-3.5 w-3.5" />,
            title: "Gemini is reviewing this draft",
        };
    }
    if (asyncReviewStatus === "UNAVAILABLE") {
        return {
            badgeClassName: "border-amber-200 bg-amber-50 text-amber-900",
            containerClassName: "border-amber-200 bg-amber-50/70",
            description: "The draft remains saved, but automated review is unavailable. Approval stays locked.",
            icon: <TriangleAlert className="h-5 w-5" />,
            iconClassName: "bg-amber-100 text-amber-700",
            shortTitle: "Unavailable",
            smallIcon: <TriangleAlert className="h-3.5 w-3.5" />,
            title: "Automated review unavailable",
        };
    }
    if (asyncReviewStatus === "FAILED") {
        return {
            badgeClassName: "border-red-200 bg-red-50 text-red-900",
            containerClassName: "border-red-200 bg-red-50/70",
            description: "The worker could not complete this review. The saved draft is unchanged and actions remain locked.",
            icon: <AlertCircle className="h-5 w-5" />,
            iconClassName: "bg-red-100 text-red-700",
            shortTitle: "Failed",
            smallIcon: <AlertCircle className="h-3.5 w-3.5" />,
            title: "Automated review failed",
        };
    }
    if (asyncReviewStatus === "STALE") {
        return {
            badgeClassName: "border-amber-200 bg-amber-50 text-amber-900",
            containerClassName: "border-amber-200 bg-amber-50/70",
            description: "This result belongs to an older draft version and cannot authorize workflow actions.",
            icon: <TriangleAlert className="h-5 w-5" />,
            iconClassName: "bg-amber-100 text-amber-700",
            shortTitle: "Stale",
            smallIcon: <TriangleAlert className="h-3.5 w-3.5" />,
            title: "Review result is stale",
        };
    }
    if (hasBlockingIssue) {
        return {
            badgeClassName: "border-red-200 bg-red-50 text-red-900",
            containerClassName: "border-red-200 bg-red-50/70",
            description: "A backend rule must be resolved before this draft can move forward.",
            icon: <ShieldAlert className="h-5 w-5" />,
            iconClassName: "bg-red-100 text-red-700",
            shortTitle: "Blocked",
            smallIcon: <ShieldAlert className="h-3.5 w-3.5" />,
            title: "Blocked by a safety rule",
        };
    }
    if (agentReview?.status === "unavailable") {
        return {
            badgeClassName: "border-amber-200 bg-amber-50 text-amber-900",
            containerClassName: "border-amber-200 bg-amber-50/70",
            description: "Gemini was unavailable. The draft is preserved and requires a human decision.",
            icon: <TriangleAlert className="h-5 w-5" />,
            iconClassName: "bg-amber-100 text-amber-700",
            shortTitle: "AI unavailable",
            smallIcon: <TriangleAlert className="h-3.5 w-3.5" />,
            title: "Human review required",
        };
    }
    if (requiresHumanReview) {
        return {
            badgeClassName: "border-amber-200 bg-amber-50 text-amber-900",
            containerClassName: "border-amber-200 bg-amber-50/70",
            description: "Review the findings and wording before approving this draft.",
            icon: <ShieldAlert className="h-5 w-5" />,
            iconClassName: "bg-amber-100 text-amber-700",
            shortTitle: "HR review",
            smallIcon: <ShieldAlert className="h-3.5 w-3.5" />,
            title: "Waiting for HR review",
        };
    }
    if (agentReview?.status === "disabled") {
        return {
            badgeClassName: "border-slate-200 bg-slate-50 text-slate-700",
            containerClassName: "border-slate-200 bg-slate-50/70",
            description: "Backend rules passed. Gemini review is disabled in the current environment.",
            icon: <CircleDashed className="h-5 w-5" />,
            iconClassName: "bg-slate-200 text-slate-700",
            shortTitle: "Rules passed",
            smallIcon: <CircleDashed className="h-3.5 w-3.5" />,
            title: "Deterministic checks passed",
        };
    }
    if (!agentReview) {
        return {
            badgeClassName: "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
            containerClassName: "border-slate-200 bg-slate-50/70 dark:border-slate-700 dark:bg-slate-900/50",
            description: "Backend rules passed. This legacy queue item does not have a recorded Gemini review.",
            icon: <CircleDashed className="h-5 w-5" />,
            iconClassName: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
            shortTitle: "Rules passed",
            smallIcon: <CircleDashed className="h-3.5 w-3.5" />,
            title: "Deterministic checks passed",
        };
    }
    return {
        badgeClassName: "border-emerald-200 bg-emerald-50 text-emerald-900",
        containerClassName: "border-emerald-200 bg-emerald-50/70",
        description: "No blocking rule or semantic concern was found. HR remains in control of the next action.",
        icon: <CheckCircle2 className="h-5 w-5" />,
        iconClassName: "bg-emerald-100 text-emerald-700",
        shortTitle: "Ready",
        smallIcon: <CheckCircle2 className="h-3.5 w-3.5" />,
        title: "Ready for the next step",
    };
}

function reviewStatusLabel(status: AsyncReviewStatus) {
    return status.charAt(0) + status.slice(1).toLowerCase();
}

function reviewPipelineTone(
    status: AsyncReviewStatus | null,
    review: AgentReviewResult | undefined,
    isStale: boolean,
): "danger" | "neutral" | "success" | "warning" {
    if (isStale || status === "STALE" || status === "UNAVAILABLE") return "warning";
    if (status === "FAILED") return "danger";
    if (status === "COMPLETED") return "success";
    if (status === "QUEUED" || status === "REVIEWING") return "neutral";
    if (review?.status === "completed") return "success";
    if (review?.status === "unavailable") return "danger";
    return "neutral";
}

function agentStatusLabel(review?: AgentReviewResult) {
    if (!review) return "Not recorded";
    if (review.status === "completed") return "Completed";
    if (review.status === "disabled") return "Disabled";
    if (review.status === "unavailable") return "Unavailable";
    return "Blocked by rules";
}

function agentMetadataLabel(review: AgentReviewResult) {
    const toolLabel = review.model_metadata.tool_calls !== undefined
        ? ` / ${review.model_metadata.tool_calls} safe tools`
        : "";
    return `${agentStatusLabel(review)} / ${review.model_metadata.model} / ${review.model_metadata.attempts} model calls${toolLabel}`;
}

function severityIcon(severity: "blocker" | "error" | "info" | "warning") {
    if (severity === "info") return <Info className="h-4 w-4" />;
    if (severity === "warning") return <TriangleAlert className="h-4 w-4" />;
    return <AlertCircle className="h-4 w-4" />;
}

function humanizeRuleId(ruleId: string) {
    return ruleId
        .replace(/^AI_/, "")
        .split("_")
        .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
        .join(" ");
}
