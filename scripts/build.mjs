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

const html = await readFile(join(dist, "static", "index.html"), "utf8");
if (!html.includes("演示数据，实际价格以平台为准")) {
  throw new Error("Required demo disclaimer is missing");
}

const worker = `const html = ${JSON.stringify(html)};

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname !== "/" && url.pathname !== "/index.html") {
      return new Response("Not found", { status: 404 });
    }
    return new Response(html, {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "public, max-age=300"
      }
    });
  }
};
`;

await writeFile(join(dist, "server", "index.js"), worker, "utf8");
console.log("Built static Sites bundle");