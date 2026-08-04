export const HILAB_CHART_PALETTE = {
    primary: "#fb2c36",
    primaryMuted: "#9f121b",
    accent: "#fac800",
    grayDark: "#1e2939",
    gray: "#6a7282",
    grayMuted: "#99a1af",
} as const;

export const HILAB_CHART_SERIES = [
    HILAB_CHART_PALETTE.primary,
    HILAB_CHART_PALETTE.grayDark,
    HILAB_CHART_PALETTE.gray,
    HILAB_CHART_PALETTE.accent,
    HILAB_CHART_PALETTE.primaryMuted,
    HILAB_CHART_PALETTE.grayMuted,
] as const;
