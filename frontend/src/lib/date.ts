export function formatDateTime(value?: string | null) {
    if (!value) {
        return "-";
    }

    return new Intl.DateTimeFormat("en", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

export function formatRelativeDateTime(value?: string | null) {
    if (!value) {
        return "-";
    }

    const date = new Date(value);
    const diffMs = Date.now() - date.getTime();
    const diffMinutes = Math.max(Math.floor(diffMs / 60000), 0);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMinutes < 1) {
        return "just now";
    }

    if (diffMinutes < 60) {
        return `${diffMinutes} minute${diffMinutes > 1 ? "s" : ""} ago`;
    }

    if (diffHours < 24) {
        return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    }

    if (diffDays <= 5) {
        return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    }

    return formatDateTime(value);
}

export function formatRelativeDateTimeWithActor(value?: string | null, actor?: string | null) {
    const dateLabel = formatRelativeDateTime(value);

    if (dateLabel === "-") {
        return "-";
    }

    return `${dateLabel}${actor ? `, ${formatActorName(actor)}` : ""}`;
}

function formatActorName(actor: string) {
    const currentUserAliases = new Set(["hieu", "demo_hr", "demo hr"]);
    const normalizedActor = actor.trim().toLowerCase();

    return currentUserAliases.has(normalizedActor) ? "me" : actor;
}

export function toDateTimeInputValue(value?: string | null) {
    if (!value) {
        return "";
    }

    return new Date(value).toISOString().slice(0, 16);
}
