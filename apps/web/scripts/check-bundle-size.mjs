// Fails when the gzipped initial JS of the built app exceeds the budget (NFR-003).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const DIST = new URL("../dist/", import.meta.url).pathname;
const LIMIT_BYTES = 150 * 1024;

const html = readFileSync(join(DIST, "index.html"), "utf8");
const initial = new Set();
for (const match of html.matchAll(/(?:src|href)="([^"]+\.js)"/g)) {
  initial.add(match[1].replace(/^\//, ""));
}
if (initial.size === 0) {
  console.error("bundle check: no JS referenced from dist/index.html");
  process.exit(1);
}

let total = 0;
for (const file of initial) {
  total += gzipSync(readFileSync(join(DIST, file))).length;
}
const kb = (total / 1024).toFixed(1);
if (total > LIMIT_BYTES) {
  console.error(`bundle check: initial JS ${kb} KB gzipped exceeds 150 KB`);
  process.exit(1);
}
console.log(`bundle check: initial JS ${kb} KB gzipped (limit 150 KB)`);
