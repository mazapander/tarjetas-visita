import { copyFileSync, cpSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const src = join(root, "src");
const dist = join(root, "dist");
const assets = join(dist, "assets");

rmSync(dist, { recursive: true, force: true });
mkdirSync(assets, { recursive: true });
copyFileSync(join(src, "index.html"), join(dist, "index.html"));
cpSync(join(src, "assets"), assets, { recursive: true });

console.log("Built code/web/dist");
