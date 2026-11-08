import { expect, test, type Page } from "@playwright/test";

async function ping(page: Page, name: string) {
  await page.getByRole("textbox", { name: "Your name" }).fill(name);
  await page.getByRole("button", { name: "Ping API" }).click();
}

test("greets the player through the real API", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { level: 1, name: "Welcome to Canasta" }),
  ).toBeVisible();

  await ping(page, "Ana");

  await expect(page.getByRole("status")).toHaveText("Welcome to Canasta, Ana!");
});

test("shows an alert when the API is unreachable", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await ping(page, "Ana");

  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("status")).toHaveCount(0);
});

for (const width of [375, 1280]) {
  test(`has no horizontal scroll at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/");
    await ping(page, "Ana");
    await expect(page.getByRole("status")).toBeVisible();

    const { scrollWidth, clientWidth } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
  });
}
