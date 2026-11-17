/* Operational journeys against real read-only API data. No fixture injected into the app. */
const { chromium } = require("playwright-core"),
  binary = require("@sparticuz/chromium").default,
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
(async () => {
  let out = process.argv[2] || "/home/user/recettes-unocr/world-class/journeys";
  fs.mkdirSync(out, { recursive: true });
  let report = [];
  const base = process.env.UI_BASE || "http://127.0.0.1:8000";
  for (const width of [1440, 1280, 834, 390]) {
    let b = await chromium.launch({
      executablePath: await binary.executablePath(),
      args: binary.args.filter(
        (a) =>
          !a.includes("disable-web-security") &&
          !a.includes("allow-running-insecure-content"),
      ),
      env: { ...process.env, LD_LIBRARY_PATH: "/tmp/uniocr-chromium-libs/lib" },
    });
    try {
      let c = await b.newContext({
          viewport: { width, height: 1000 },
          serviceWorkers: "block",
        }),
        p = await c.newPage(),
        errors = [],
        writes = [];
      p.on("pageerror", (e) => errors.push(e.message));
      await p.route("**/*", (r) => {
        if (!["GET", "HEAD"].includes(r.request().method())) {
          writes.push(r.request().method());
          return r.abort();
        }
        return r.continue();
      });
      await p.goto(base + "/#dossiers/tous", {
        waitUntil: "networkidle",
      });
      await p.locator(".dos-row").first().waitFor();
      let expected = await p.evaluate(() =>
        Math.min(40, Dossiers.etat.dossiers.length),
      );
      await p.locator('[data-case-view="board"]').click();
      assert.equal(await p.locator(".case-lane .dos-row").count(), expected);
      await p.waitForTimeout(700);
      await p.screenshot({ path: path.join(out, width + "-pilotage.png") });
      const cardIndex = await p
        .locator(".case-lane .dos-row")
        .evaluateAll((rows) => {
          const index = rows.findIndex((row) =>
            Dossiers.etat.dossiers.some(
              (d) =>
                d.id === row.dataset.id &&
                Array.isArray(d.pieces) &&
                d.pieces.length,
            ),
          );
          return index < 0 ? 0 : index;
        });
      let sourceId = await p
        .locator(".case-lane .dos-row")
        .nth(cardIndex)
        .getAttribute("data-id");
      await p.locator(".case-lane .dos-row").nth(cardIndex).click();
      await p.waitForFunction(() => Dossiers.etat.detail !== null);
      assert(
        (await p.locator(".dos-detail__eyebrow").textContent()) === sourceId,
      );
      assert.equal(await p.locator(".case-next .case-next__action").count(), 4);
      assert(await p.locator("#dos-detail-empty").isHidden());
      await p.locator(".case-identity summary").click();
      assert(await p.locator(".dos-detail__meta").isVisible());
      await p.screenshot({ path: path.join(out, width + "-identity.png") });
      await p.locator(".case-identity summary").click();

      let tabs = p.locator(".dos-tab"),
        length = await tabs.count();
      for (let i = 0; i < length; i++) {
        await tabs.nth(i).click();
        let panel = await tabs.nth(i).getAttribute("aria-controls");
        assert(await p.locator('[id="' + panel + '"]').isVisible());
      }
      await p.locator(".case-next .case-next__action").nth(0).click();
      await p.waitForTimeout(200);
      await p.screenshot({ path: path.join(out, width + "-pieces.png") });
      let sourceInspectorHTTP = null;
      const inspect = p.locator(".dos-doc .case-next__action").first();
      if (await inspect.count()) {
        const job = await p.evaluate(
          () =>
            Dossiers.etat.detail.pieces.find((piece) => piece.job_id).job_id,
        );
        const requested = p.waitForRequest(
          (request) =>
            new URL(request.url()).pathname === "/api/jobs/" + job + "/result",
        );
        await inspect.click();
        const request = await requested;
        const response = await request.response();
        sourceInspectorHTTP = response.status();
        await p.locator("#tab-result").waitFor({ state: "visible" });
        if (sourceInspectorHTTP === 200)
          await p.waitForFunction(
            (id) =>
              document.getElementById("tab-result").dataset.resultSource === id,
            job,
          );
        else
          await p
            .locator(".result-load-state[role=alert]")
            .waitFor({ state: "visible" });
        await p.waitForTimeout(300);
        await p.screenshot({
          path: path.join(out, width + "-source-inspector.png"),
        });
        await p.goto(base + "/#dossiers/tous");
        await p.locator('.dos-row[data-id="' + sourceId + '"]').click();
        await p.waitForFunction(() => Dossiers.etat.detail !== null);
      }
      await p.locator(".case-next .case-next__action").nth(3).click();
      await p.waitForTimeout(400);
      await p.screenshot({ path: path.join(out, width + "-chronologie.png") });
      await p.locator('.dos-tab[aria-selected="true"]').focus();
      await p.keyboard.press("Home");
      assert.equal(
        await p
          .locator('.dos-tab[aria-selected="true"]')
          .getAttribute("data-tab"),
        "synthese",
      );
      await p.locator(".case-return").click();
      assert.equal(
        await p.evaluate(() => document.activeElement.getAttribute("data-id")),
        sourceId,
      );
      await p.locator("#dos-search").fill("NO-MATCH-EXACT-9ec793b7");
      assert.equal(await p.locator(".dos-row").count(), 0);
      assert(await p.locator("#dos-empty").isVisible());
      await p.screenshot({ path: path.join(out, width + "-empty.png") });
      await p.locator("#dos-search").fill("");
      await p.locator('[data-case-view="liste"]').click();
      assert.equal(await p.locator("#dos-list .dos-row").count(), expected);
      await p.locator(".context-guide").click();
      assert(await p.locator(".studio-guide").evaluate((d) => d.open));
      let destinations = await p
        .locator(".studio-guide__route")
        .evaluateAll((links) => links.map((a) => a.hash));
      let allowed = await p
        .locator("#mainNav a")
        .evaluateAll((links) => links.map((a) => a.hash));
      assert(destinations.every((a) => allowed.includes(a)));
      await p.screenshot({ path: path.join(out, width + "-guide.png") });
      await p.keyboard.press("Escape");
      assert.equal(
        await p.evaluate(() =>
          document.activeElement.classList.contains("context-guide"),
        ),
        true,
      );
      await p.goto(base + "/#dossiers/nouveau");
      await p.locator("#dos-create[open]").waitFor();
      assert.equal(await p.locator(".studio-form-progress").count(), 1);
      assert.equal(
        await p.locator("#dos-create-form").evaluate((f) => f.checkValidity()),
        false,
      );
      await p.locator(".studio-form-errors").waitFor({ state: "visible" });
      await p.screenshot({ path: path.join(out, width + "-form-errors.png") });
      await p
        .locator('#dos-create-form input[name="label"]')
        .fill("Test de saisie local, non envoyé");
      await p.waitForTimeout(100);
      assert(
        (await p.locator(".studio-form-progress").textContent()).startsWith(
          "1 / 1",
        ),
      );
      assert(await p.locator(".studio-form-errors").isHidden());
      await p.locator("#dos-create-cancel").click();
      await p.goto(base + "/#dossiers/tous");
      assert(
        await p.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      );
      await p.emulateMedia({ reducedMotion: "reduce" });
      await p.locator(".context-guide").click();
      assert.equal(
        await p
          .locator(".studio-guide")
          .evaluate((e) => e.getAnimations().length),
        0,
      );
      assert.deepEqual(errors, []);
      assert.deepEqual(writes, []);
      report.push({
        width,
        sourceId,
        tabs: length,
        boardRows: expected,
        sourceInspectorHTTP,
        search: true,
        guideAllowedOnly: true,
        formValidation: true,
        keyboard: true,
        reducedMotion: true,
        errors,
        writes,
      });
    } finally {
      await b.close();
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
