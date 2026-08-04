export function formatDateTime(value?: string | null) {
    if (!value) {
        return "-";
    }

    return new Intl.DateTimeFormat("en", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

export function toDateTimeInputValue(value?: string | null) {
    if (!value) {
        return "";
    }

    return new Date(value).toISOString().slice(0, 16);
}
