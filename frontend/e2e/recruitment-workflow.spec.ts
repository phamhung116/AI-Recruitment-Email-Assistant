import { expect, test, type Locator, type Page } from "@playwright/test";

async function candidateRow(page: Page, candidateName: string): Promise<Locator> {
    const row = page.getByRole("row").filter({ hasText: candidateName }).first();
    await expect(row).toBeVisible();
    return row;
}

async function queueRow(page: Page, candidateName: string): Promise<Locator> {
    const row = page.getByRole("row").filter({ hasText: candidateName }).first();
    await expect(row).toBeVisible();
    return row;
}

test("HR completes the safe recruitment email demo workflow", async ({ page }) => {
    await page.goto("/candidates");
    await expect(page.getByRole("heading", { name: "Candidates" })).toBeVisible();

    const candidateSearch = page.getByPlaceholder("Search candidate name or email...");
    await candidateSearch.fill("Do Gia Bao");
    const pendingCandidate = await candidateRow(page, "Do Gia Bao");
    await pendingCandidate.getByRole("cell", { name: "Do Gia Bao" }).click();
    await page.getByRole("button", { name: "Generate Email Draft" }).first().click();
    let generateDialog = page.getByRole("dialog", { name: "Generate Email Draft" });
    await expect(generateDialog.getByText("No email allowed")).toBeVisible();
    await expect(generateDialog.getByRole("button", { name: "Continue" })).toBeDisabled();
    await generateDialog.getByRole("button", { name: "Close" }).click();

    await page.goto("/candidates");
    await expect(page.getByRole("heading", { name: "Candidates" })).toBeVisible();
    await candidateSearch.fill("Nguyen Minh An");
    const eligibleCandidate = await candidateRow(page, "Nguyen Minh An");
    await eligibleCandidate.getByRole("cell", { name: "Nguyen Minh An" }).click();
    await page.getByRole("button", { name: "Generate Email Draft" }).first().click();
    generateDialog = page.getByRole("dialog", { name: "Generate Email Draft" });

    await expect(generateDialog.getByText("PASS_CV")).toBeVisible();
    await expect(generateDialog.getByText("INTERVIEW_INVITATION")).toBeVisible();
    await generateDialog.getByRole("button", { name: "Continue" }).click();
    await expect(generateDialog.getByText("Verified template selected by backend policy")).toBeVisible();
    await expect(generateDialog.getByText("Interview Invitation", { exact: true })).toBeVisible();
    await generateDialog.getByRole("button", { name: "Continue" }).click();

    await expect(generateDialog.getByRole("heading", { name: "Draft saved – review queued" })).toBeVisible();
    await expect(generateDialog.getByText("Queued", { exact: true })).toBeVisible();
    await expect(generateDialog.getByText("Not required", { exact: true })).toBeVisible();
    await generateDialog.getByRole("button", { name: "Done" }).click();

    await page.getByRole("link", { name: "Email Queue" }).click();
    let generatedRow = await queueRow(page, "Nguyen Minh An");
    await generatedRow.getByRole("button", { name: "Open review" }).click();
    let reviewDrawer = page.getByRole("dialog", { name: "Review email draft" });
    await expect(reviewDrawer.getByRole("heading", { name: "Automated review unavailable" })).toBeVisible({ timeout: 20_000 });
    await expect(reviewDrawer.getByRole("button", { name: "Approve" })).toBeDisabled();
    const unavailableSimulate = reviewDrawer.getByRole("button", { name: "Simulate send" });
    if (await unavailableSimulate.count()) {
        await expect(unavailableSimulate).toBeDisabled();
    }
    await reviewDrawer.getByRole("button", { name: "Close review drawer" }).click();

    const sensitiveRow = await queueRow(page, "Tran Bao Chau");
    await expect(sensitiveRow.getByText("PENDING_APPROVAL")).toBeVisible();
    await sensitiveRow.getByRole("button", { name: "Open review" }).click();
    const sensitiveDrawer = page.getByRole("dialog", { name: "Review email draft" });
    await expect(sensitiveDrawer.getByRole("button", { name: "Approve" })).toBeEnabled();
    await expect(sensitiveDrawer.getByRole("button", { name: "Simulate send" })).toHaveCount(0);
    await sensitiveDrawer.getByRole("button", { name: "Approve" }).click();
    const approveDialog = page.getByRole("dialog", { name: "Approve this email draft?" });
    await approveDialog.getByRole("button", { name: "Approve draft" }).click();
    await expect(page.getByText("Draft approved")).toBeVisible();

    generatedRow = await queueRow(page, "Tran Bao Chau");
    await expect(generatedRow.getByText("APPROVED")).toBeVisible();
    await generatedRow.getByRole("button", { name: "Open review" }).click();
    reviewDrawer = page.getByRole("dialog", { name: "Review email draft" });
    await reviewDrawer.getByRole("button", { name: "Simulate send" }).click();
    const simulationDialog = page.getByRole("dialog", { name: "Simulate sending this email?" });
    await expect(simulationDialog.getByText("No real email will be delivered.")).toBeVisible();
    await simulationDialog.getByRole("button", { name: "Run simulation" }).click();
    await expect(page.getByText("Send simulation recorded")).toBeVisible();

    await page.getByRole("link", { name: "Email History" }).click();
    const historyRow = await queueRow(page, "Tran Bao Chau");
    await expect(historyRow.getByText("REJECTION_AFTER_CV")).toBeVisible();
    await expect(historyRow.getByText("chau.tran@example.com")).toBeVisible();

    await page.getByRole("link", { name: "Audit Logs" }).click();
    await expect(page.getByText("ai_generate_email").first()).toBeVisible();
    // Gemini is intentionally disabled in this isolated E2E environment, so the
    // durable queue event is the expected audit evidence for the attempted review.
    await expect(page.getByText("queue_agent_review").first()).toBeVisible();
    await expect(page.getByText("approve_email").first()).toBeVisible();
    await expect(page.getByText("send_email").first()).toBeVisible();
});
