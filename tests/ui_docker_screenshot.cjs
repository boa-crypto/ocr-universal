/* Capture d'écran de la recette Docker : charge la page servie par le
 * conteneur avec le Chromium livré par npm (même pile que les recettes
 * navigateur) et échoue si le rendu casse ou si l'image est vide. */
const { chromium } = require("playwright-core");
const binary = require("@sparticuz/chromium").default;
const assert = require("node:assert/strict");
const cp = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const z = require("node:zlib");

async function main() {
  const base = process.argv[2] || "http://127.0.0.1:8000";
  const out = path.resolve(process.argv[3] || "/tmp/unocr-screenshot.png");
  fs.mkdirSync(path.dirname(out), { recursive: true });

  // Bibliothèques d'exécution livrées avec le binaire (comme ui:product).
  const libs = path.join(os.tmpdir(), "uniocr-chromium-libs");
  fs.mkdirSync(libs, { recursive: true });
  const archive = path.resolve(
    path.dirname(require.resolve("@sparticuz/chromium")),
    "../bin/al2023.tar.br",
  );
  if (process.platform === "linux" && fs.existsSync(archive)) {
    const tar = path.join(libs, "runtime.tar");
    fs.writeFileSync(tar, z.brotliDecompressSync(fs.readFileSync(archive)));
    cp.execFileSync("tar", ["xf", tar, "-C", libs]);
  }

  const args = binary.args.filter(
    (a) =>
      !a.includes("disable-web-security") &&
      !a.includes("allow-running-insecure-content"),
  );
  const browser = await chromium.launch({
    executablePath: await binary.executablePath(),
    args,
    headless: true,
    env: {
      ...process.env,
      LD_LIBRARY_PATH: [path.join(libs, "lib"), process.env.LD_LIBRARY_PATH]
        .filter(Boolean)
        .join(":"),
    },
  });
  try {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 1024 },
      serviceWorkers: "block",
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const response = await page.goto(base, { waitUntil: "networkidle" });
    assert(response && response.ok(), `page d'accueil HTTP ${response && response.status()}`);
    await page.evaluate(() => document.fonts.ready);
    assert.deepEqual(errors, [], `erreurs de page : ${errors.join(" | ")}`);
    await page.screenshot({ path: out });
  } finally {
    await browser.close();
  }
  const size = fs.statSync(out).size;
  assert(size > 0, "capture vide");
  console.log(`capture écrite : ${out} (${size} octets)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
