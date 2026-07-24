import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(join(dist, "static"), { recursive: true });
await mkdir(join(dist, "server"), { recursive: true });
await mkdir(join(dist, ".openai"), { recursive: true });

await cp(join(root, "index.html"), join(dist, "static", "index.html"));
await cp(join(root, ".openai", "hosting.json"), join(dist, ".openai", "hosting.json"));

const worker = `export default {
  async fetch(request, env) {
    return env.ASSETS.fetch(request);
  }
};
`;

await writeFile(join(dist, "server", "index.js"), worker, "utf8");

const html = await readFile(join(dist, "static", "index.html"), "utf8");
if (!html.includes("婕旂ず鏁版嵁锛屽疄闄呬环鏍间互骞冲彴涓哄噯")) {
  throw new Error("Required demo disclaimer is missing");
}

console.log("Built static Sites bundle");