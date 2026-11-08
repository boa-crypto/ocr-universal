/* Real browser motion audit. No business writes; the existing server is untouched. */
const { chromium } = require("playwright-core"),
  binary = require("@sparticuz/chromium").default,
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
(async () => {
  const out =
    process.argv[2] || "/home/user/recettes-unocr/visual-motion/motion";
  fs.mkdirSync(out, { recursive: true });
  const report = [];
  for (const width of [1440, 834, 390])
    for (const reducedMotion of ["no-preference", "reduce"]) {
      const browser = await chromium.launch({
        executablePath: await binary.executablePath(),
        args: binary.args.filter(
          (a) =>
            !a.includes("disable-web-security") &&
            !a.includes("allow-running-insecure-content"),
        ),
        env: {
          ...process.env,
          LD_LIBRARY_PATH: "/tmp/uniocr-chromium-libs/lib",
        },
      });
      try {
        const context = await browser.newContext({
            viewport: { width, height: 1000 },
            reducedMotion,
            serviceWorkers: "block",
          }),
          page = await context.newPage(),
          errors = [],
          writes = [];
        page.on("pageerror", (e) => errors.push(e.message));
        await page.route("**/*", (r) => {
          if (!["GET", "HEAD"].includes(r.request().method())) {
            writes.push(r.request().method());
            return r.abort();
          }
          return r.continue();
        });
        await page.addInitScript(() => {
          window.motionCalls = 0;
          window.visualCLS = 0;
          const original = Element.prototype.animate;
          Element.prototype.animate = function (...args) {
            window.motionCalls++;
            return original.apply(this, args);
          };
          new PerformanceObserver((list) =>
            list.getEntries().forEach((e) => {
              if (!e.hadRecentInput) window.visualCLS += e.value;
            }),
          ).observe({ type: "layout-shift", buffered: true });
        });
        await page.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle" });
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(800);
        assert.equal(
          await page.locator("html").getAttribute("data-visual-motion"),
          "ready",
        );
        assert(
          await page
            .locator(".document-art img")
            .evaluate((e) => e.complete && e.naturalWidth === 600),
        );
        assert(await page.locator("#globalSearch").isVisible());
        assert(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
        );
        let calls = await page.evaluate(() => motionCalls);
        if (reducedMotion === "reduce") assert.equal(calls, 0);
        else assert(calls > 0);
        await page.screenshot({
          path: path.join(out, width + "-" + reducedMotion + ".png"),
        });
        await page.locator(".intent-trigger").click();
        await page.waitForTimeout(30);
        let menuAnimations = await page
          .locator(".intent-dialog")
          .evaluate((e) => e.getAnimations().length);
        if (reducedMotion === "reduce") assert.equal(menuAnimations, 0);
        else assert(menuAnimations > 0);
        await page.keyboard.press("Escape");
        await page.locator("#notifBtn").click();
        assert(await page.locator("#notifMenu").isVisible());
        await page.locator("#notifBtn").click();
        await page.locator(".action-path").first().hover();
        await page.waitForTimeout(250);
        assert.equal(await page.locator(".action-path").count(), 3);
        if (width < 1101) {
          await page.locator(".mobile-document-art").scrollIntoViewIfNeeded();
          await page.waitForTimeout(500);
          await page.screenshot({
            path: path.join(
              out,
              width + "-" + reducedMotion + "-illustration.png",
            ),
          });
        }
        await page.emulateMedia({ reducedMotion: "reduce" });
        await page.waitForTimeout(50);
        assert.equal(
          await page
            .locator("section.page")
            .first()
            .evaluate((e) => e.getAnimations().length),
          0,
        );
        assert(
          (await page.evaluate(() => visualCLS)) < 0.05,
          "Initial lab CLS exceeded 0.05",
        );
        assert.deepEqual(errors, []);
        assert.deepEqual(writes, []);
        report.push({
          width,
          reducedMotion,
          motionCalls: calls,
          menuAnimations,
          cls: await page.evaluate(() => visualCLS),
          errors,
          writes,
        });
      } finally {
        await browser.close();
      }
    }
  fs.writeFileSync(
    path.join(out, "report.json"),
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report));
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
