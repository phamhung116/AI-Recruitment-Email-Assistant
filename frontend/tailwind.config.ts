import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: ["class"],
    content: [
        "./index.html",
        "./src/**/*.{ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                gray: {
                    50: "#f9fafb",
                    100: "#f3f4f6",
                    200: "#e5e7eb",
                    300: "#d1d5dc",
                    400: "#99a1af",
                    500: "#6a7282",
                    600: "#4a5565",
                    700: "#334155",
                    800: "#1e2939",
                    900: "#101828",
                    950: "#0b1220",
                },
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                primary: {
                    DEFAULT: "hsl(var(--primary))",
                    foreground: "hsl(var(--primary-foreground))",
                    50: "#fff1f2",
                    100: "#ffe3e5",
                    200: "#ffc9cd",
                    300: "#ff9ca3",
                    400: "#ff5f69",
                    500: "#fb2c36",
                    600: "#e31825",
                    700: "#c0101b",
                    800: "#9f121b",
                    900: "#841820",
                    950: "#49070c",
                },
                accent: {
                    50: "#fffbe8",
                    100: "#fff4bf",
                    200: "#ffe875",
                    300: "#ffdc3f",
                    400: "#fac800",
                    500: "#d9a900",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                },
            },
            borderRadius: {
                lg: "0.5rem",
                md: "0.375rem",
                sm: "0.25rem",
            },
        },
    },
    plugins: [],
};

export default config;
