import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": `${import.meta.dirname}/src`,
        },
    },
    test: {
        environment: "jsdom",
        include: ["src/**/*.test.{ts,tsx}"],
        setupFiles: "./src/test/setup.ts",
        coverage: {
            provider: "v8",
            reporter: ["text", "html"],
            include: [
                "src/components/shared/EmailReviewPanel.tsx",
                "src/constants/emailTypes.ts",
                "src/features/emailQueue/EmailQueuePage.tsx",
            ],
            thresholds: {
                branches: 70,
                functions: 70,
                lines: 80,
                statements: 80,
            },
        },
    },
});
