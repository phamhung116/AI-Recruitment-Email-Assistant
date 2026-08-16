import { expect, test } from "@playwright/test";


test("HR reviews a protected draft and reaches real-send confirmation", async ({ page }, testInfo) => {
    await page.goto("/candidates");
    await expect(page.getByRole("heading", { name: "Candidates" })).toBeVisible();
    await expect(page.getByRole("row").filter({ hasText: "Nguyen Minh An" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("candidates.png"), fullPage: true });

    await page.getByRole("row").filter({ hasText: "Nguyen Minh An" }).click();
    await expect(page.getByRole("heading", { name: "Nguyen Minh An" })).toBeVisible();

    const emptyDraftAction = page.getByRole("button", { name: "Generate Draft" });
    if (await emptyDraftAction.isVisible()) {
        await emptyDraftAction.click();
        await expect(page.getByRole("button", { name: /Revision 1/ })).toBeVisible();
    }

    await expect(page.getByText("Protected decision content")).toBeVisible();
    await page.getByRole("button", { name: "Send Real Email" }).click();
    const confirmation = page.getByRole("dialog", { name: "Send this email through Resend?" });
    await expect(confirmation).toContainText("This will send a real INTERVIEW_INVITATION email");
    await page.screenshot({ path: testInfo.outputPath("real-send-confirmation.png"), fullPage: true });
    await confirmation.getByRole("button", { name: "Cancel" }).click();

    await page.goto("/audit-logs");
    await expect(page.getByText("DRAFT_GENERATED").first()).toBeVisible();
});
