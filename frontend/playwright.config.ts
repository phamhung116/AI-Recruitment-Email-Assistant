import { defineConfig, devices } from "@playwright/test";

const browserChannel = process.env.PLAYWRIGHT_CHANNEL;
const channelConfig = browserChannel ? { channel: browserChannel } : {};

export default defineConfig({
    testDir: "./e2e",
    fullyParallel: false,
    forbidOnly: Boolean(process.env.CI),
    retries: process.env.CI ? 1 : 0,
    workers: 1,
    reporter: [["list"], ["html", { open: "never" }]],
    use: {
        baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:14173",
        screenshot: "only-on-failure",
        trace: "retain-on-failure",
        video: "off",
    },
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"], ...channelConfig },
        },
        {
            name: "mobile-chromium",
            use: { ...devices["Pixel 7"], ...channelConfig },
        },
    ],
});
