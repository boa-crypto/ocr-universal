/* Exercises the actual reusable Shadow DOM components, without API writes. */
const {
    launchBrowser,
    inspect,
    verify,
  } = require("./ui_field_contrast_browser.cjs"),
  fs = require("node:fs"),
  path = require("node:path"),
  assert = require("node:assert/strict");
const out =
  process.argv[2] || "/home/user/recettes-unocr/field-contrast/shadow";
fs.mkdirSync(out, { recursive: true });
const report = { cases: [], errors: [], writes: [] };
(async () => {
  for (const width of [1440, 390])
    for (const theme of ["light", "dark"]) {
      const b = await launchBrowser();
      try {
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
        await p.addScriptTag({
          type: "module",
          url: "/web/components/forms/Form.js",
        });
        await p.waitForFunction(() => customElements.get("form-input"));
        await p.evaluate(() => {
          const lab = document.createElement("section");
          lab.id = "shadow-lab";
          lab.style.cssText =
            "position:fixed;inset:8px;z-index:2147483646;overflow:auto;background:var(--pe-paper);color:var(--field-text);padding:24px";
          const h = document.createElement("h1");
          h.textContent = "Composants réutilisables — recette Shadow DOM";
          lab.append(h);
          for (const type of [
            "text",
            "email",
            "password",
            "number",
            "date",
            "textarea",
            "select",
          ]) {
            const host = document.createElement(
              type === "textarea"
                ? "form-textarea"
                : type === "select"
                  ? "form-select"
                  : "form-input",
            );
            host.id = "shadow-" + type;
            host.setAttribute("label", type);
            host.setAttribute("type", type);
            host.setAttribute("placeholder", "Placeholder lisible");
            host.style.cssText =
              "display:inline-block;vertical-align:top;width:280px;margin:8px";
            if (type === "select") {
              for (const txt of ["Algérie", "Oran"]) {
                const o = document.createElement("option");
                o.textContent = txt;
                host.append(o);
              }
            }
            lab.append(host);
          }
          document.body.append(lab);
        });
        await p.waitForFunction(() =>
          [
            ...document.querySelectorAll(
              "#shadow-lab form-input,#shadow-lab form-textarea,#shadow-lab form-select",
            ),
          ].every((h) => h.shadowRoot.querySelector("link")?.sheet),
        );
        for (const type of [
          "text",
          "email",
          "password",
          "number",
          "date",
          "textarea",
          "select",
        ]) {
          const host = p.locator("#shadow-" + type),
            f = host.locator("input,textarea,select");
          if (type === "select") await f.selectOption({ label: "Oran" });
          else
            await f.fill(
              {
                email: "audit@example.test",
                number: "1234",
                date: "2026-11-04",
              }[type] || "Lisibilité 0123",
            );
          if (type === "text") {
            await f.fill("");
            await f.pressSequentially("Saisie continue 0123");
            assert.equal(await f.inputValue(), "Saisie continue 0123");
            assert.equal(
              await host.getAttribute("value"),
              "Saisie continue 0123",
            );
            assert(
              await host.evaluate(
                (h) =>
                  h.shadowRoot.activeElement ===
                  h.shadowRoot.querySelector("input"),
              ),
            );
            await host.evaluate((h) => (h.value = 0));
            assert.equal(await f.inputValue(), "0");
          }
          for (const state of [
            "normal",
            "focus",
            "error",
            "readonly",
            "disabled",
          ]) {
            if (type === "select" && state === "readonly") continue;
            await host.evaluate((h, state) => {
              h.removeAttribute("error");
              h.removeAttribute("readonly");
              h.removeAttribute("disabled");
              if (state === "error")
                h.setAttribute("error", "Valeur à vérifier");
              if (state === "readonly") h.setAttribute("readonly", "");
              if (state === "disabled") h.setAttribute("disabled", "");
            }, state);
            if (state === "focus") await f.focus();
            await p.waitForTimeout(170);
            assert.equal(
              await p.locator("html").getAttribute("data-theme"),
              theme,
              "typing must not toggle theme",
            );
            const rows = (await p.evaluate(inspect)).filter(
              (r) => r.host === "shadow-" + type,
            );
            assert.equal(rows.length, 1);
            verify(rows, "Shadow " + type + " " + state);
            if (state === "error") {
              const actual = await f.evaluate(
                  (e) => getComputedStyle(e).borderTopColor,
                ),
                expected = await p.evaluate(() => {
                  const e = document.createElement("span");
                  e.style.color = "var(--field-error)";
                  document.body.append(e);
                  const s = getComputedStyle(e).color;
                  e.remove();
                  return s;
                });
              assert.equal(actual, expected);
            }
            report.cases.push({ width, theme, type, state, ...rows[0] });
          }
          await host.evaluate((h) => {
            h.removeAttribute("disabled");
            h.removeAttribute("readonly");
            h.removeAttribute("error");
          });
        }
        await p.screenshot({
          path: path.join(out, `${width}-${theme}.png`),
          timeout: 60000,
        });
      } finally {
        await b.close();
      }
    }
  assert.equal(report.errors.length, 0, JSON.stringify(report.errors));
  assert.equal(report.writes.length, 0);
  console.log(
    JSON.stringify({
      cases: report.cases.length,
      errors: report.errors.length,
      writes: report.writes.length,
    }),
  );
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(() =>
    fs.writeFileSync(
      path.join(out, "report.json"),
      JSON.stringify(report, null, 2),
    ),
  );
