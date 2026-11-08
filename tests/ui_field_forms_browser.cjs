/* Actual dynamic create/edit forms, opened and cancelled. Never submitted. */
const {
  inspect,
  verify,
  launchBrowser,
} = require("./ui_field_contrast_browser.cjs");
const fs = require("node:fs"),
  path = require("node:path"),
  assert = require("node:assert/strict");
const out = process.argv[2] || "/home/user/recettes-unocr/field-contrast/forms";
fs.mkdirSync(out, { recursive: true });
const report = { forms: [], errors: [], writes: [] };
(async () => {
  let b;
  try {
    for (const width of [1440, 390])
      for (const theme of ["light", "dark"]) {
        b = await launchBrowser();
        const c = await b.newContext({
            viewport: { width, height: 1000 },
            serviceWorkers: "block",
          }),
          p = await c.newPage();
        p.on("pageerror", (e) => report.errors.push(e.message));
        await p.route("**/*", (r) => {
          if (!["GET", "HEAD"].includes(r.request().method())) {
            report.writes.push(r.request().method());
            return r.abort();
          }
          return r.continue();
        });
        await p.goto("http://127.0.0.1:8000/", {
          waitUntil: "domcontentloaded",
        });
        await p.evaluate((t) => {
          if (document.documentElement.dataset.theme !== t)
            document.getElementById("themeToggle").click();
          if (document.documentElement.dataset.theme !== t)
            throw Error("Theme not applied: " + t);
        }, theme);
        const search = p.locator("#globalSearch");
        await search.fill("facture");
        await p.waitForTimeout(750);
        await search.press("ArrowDown");
        await p.waitForTimeout(200);
        verify(
          await p.evaluate(inspect, true),
          "actual global search and custom choices",
        );
        await p.screenshot({
          path: path.join(out, `${width}-${theme}-search-choices.png`),
          timeout: 60000,
        });
        await search.press("Escape");
        await search.fill("");
        const routes = await p.evaluate(() =>
          Navigation.getConfig()
            .flatMap((g) => [g.route, ...g.subitems.map((s) => s.route)])
            .filter((r) => {
              const e = UniOCREcrans.ecrans[r.slice(1)];
              return e && !e.lectureSeule && (e.creation || e.edition);
            }),
        );
        for (const route of routes) {
          await p.goto("http://127.0.0.1:8000/" + route);
          await p.waitForFunction(
            (r) =>
              window.__ecranCourant &&
              window.__ecranCourant.ecran === UniOCREcrans.ecrans[r.slice(1)],
            route,
            { timeout: 15000 },
          );
          await p.waitForTimeout(200);
          for (const mode of ["creation", "edition"]) {
            const button =
              mode === "creation"
                ? p
                    .locator(".ecran__actions button")
                    .filter({ hasText: /^Nouveau$/ })
                    .first()
                : p
                    .locator(".ecran__td-actions button")
                    .filter({ hasText: /^Modifier$/ })
                    .first();
            if (!(await button.isVisible())) continue;
            await button.click();
            const modal = p.locator(".ecran__boite").last();
            await modal.waitFor({ state: "visible" });
            await p.waitForTimeout(80);
            let rows = await p.evaluate(inspect);
            verify(rows, `${width} ${theme} ${route} ${mode}`);
            const editable = modal
              .locator(
                'input[type="text"]:not([readonly]):not([disabled]),input:not([type]):not([readonly]):not([disabled]),textarea:not([readonly]):not([disabled])',
              )
              .first();
            if (await editable.isVisible()) {
              const old = await editable.inputValue();
              await editable.fill("Lisible — 0123");
              await editable.hover();
              verify(await p.evaluate(inspect), "typed dynamic form");
              await editable.fill(old);
            }
            report.forms.push({
              width,
              theme,
              route,
              mode,
              fields: rows.filter((r) => r.id.startsWith("champ-")),
            });
            if (
              [
                "/finance/frais",
                "#finance/frais",
                "#referentiels/devises",
                "#referentiels/clients",
                "#douane/controles",
              ].includes(route)
            ) {
              await p.screenshot({
                path: path.join(
                  out,
                  `${width}-${theme}-${route.slice(1).replaceAll("/", "-")}-${mode}.png`,
                ),
                timeout: 60000,
              });
            }
            await modal
              .getByRole("button", { name: "Annuler", exact: true })
              .click();
            assert.equal(await p.locator(".ecran__boite").count(), 0);
          }
        }
        await c.close();
        await b.close();
        b = null;
      }
    assert(report.forms.some((f) => f.mode === "creation"));
    assert(report.forms.some((f) => f.mode === "edition"));
    assert.equal(report.errors.length, 0);
    assert.equal(report.writes.length, 0);
    console.log(
      JSON.stringify({
        forms: report.forms.length,
        fields: report.forms.reduce((n, f) => n + f.fields.length, 0),
        errors: report.errors.length,
        writes: report.writes.length,
      }),
    );
  } finally {
    fs.writeFileSync(
      path.join(out, "report.json"),
      JSON.stringify(report, null, 2),
    );
    if (b) await b.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
