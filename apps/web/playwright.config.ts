import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const here = dirname(fileURLToPath(import.meta.url));
const distDir = resolve(here, "dist");
const port = 8123;

// The e2e run never builds: `npm run e2e` builds first, and a missing bundle is an error.
if (!existsSync(resolve(distDir, "index.html"))) {
  throw new Error(`Web bundle not found at ${distDir}; run "npm run build" first.`);
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `uv run --project ../api uvicorn canasta_api.main:app --host 127.0.0.1 --port ${port}`,
    url: `http://127.0.0.1:${port}/api/v1/health`,
    env: { WEB_DIST_DIR: distDir, LOG_LEVEL: "WARNING" },
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
