/* Read-only real-browser field inventory + explicitly labelled native state lab.
   No app data or API response is substituted. Fixtures exist only in this browser. */
const { chromium } = require("playwright-core"),
  binary = require("@sparticuz/chromium").default,
  fs = require("node:fs"),
  path = require("node:path"),
  assert = require("node:assert/strict");
const out = process.argv[2] || "/home/user/recettes-unocr/field-contrast";
fs.mkdirSync(out, { recursive: true });
const report = {
  routes: [],
  fields: [],
  states: [],
  baseline: [],
  errors: [],
  writes: [],
};
function inspect(includeChoices = false) {
  const rgb = (s) => {
    const a = s.match(/[\d.]+/g);
    return a ? a.slice(0, 3).map(Number) : [0, 0, 0];
  };
  const lum = (c) => {
    const a = c.map((n) => {
      n /= 255;
      return n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
  };
  const ratio = (a, b) => {
    a = lum(rgb(a));
    b = lum(rgb(b));
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  };
  const scopes = [document];
  for (let i = 0; i < scopes.length; i++)
    for (const e of scopes[i].querySelectorAll("*"))
      if (e.shadowRoot) scopes.push(e.shadowRoot);
  return scopes
    .flatMap((root) => [
      ...root.querySelectorAll(
        'input,textarea,select,[contenteditable="true"],[role="combobox"]' +
          (includeChoices ? ', [role="listbox"],[role="option"]' : ""),
      ),
    ])
    .filter(
      (e) =>
        e.getClientRects().length &&
        getComputedStyle(e).visibility !== "hidden" &&
        (e.getAttribute("role") === "option" ||
          ![
            "hidden",
            "checkbox",
            "radio",
            "range",
            "color",
            "button",
            "submit",
            "reset",
            "image",
          ].includes(e.type)),
    )
    .map((e) => {
      const s = getComputedStyle(e),
        p = getComputedStyle(e, "::placeholder");
      let opacity = 1;
      for (let n = e; n; n = n.parentElement || n.getRootNode().host)
        opacity *= Number(getComputedStyle(n).opacity);
      return {
        id: e.id,
        host: e.getRootNode().host?.id || null,
        type: e.type || e.getAttribute("role") || e.tagName.toLowerCase(),
        text: s.color,
        fill: s.webkitTextFillColor,
        background: s.backgroundColor,
        caret: s.caretColor,
        opacity,
        ratio: ratio(s.webkitTextFillColor || s.color, s.backgroundColor),
        caretRatio: ratio(s.caretColor, s.backgroundColor),
        placeholder: e.hasAttribute("placeholder")
          ? ratio(p.webkitTextFillColor || p.color, s.backgroundColor)
          : null,
        border: ratio(s.borderTopColor, s.backgroundColor),
        outline:
          s.outlineStyle === "none"
            ? null
            : ratio(s.outlineColor, s.backgroundColor),
      };
    });
}
function verify(rows, where) {
  for (const f of rows) {
    assert(f.ratio >= 4.5, where + " text " + JSON.stringify(f));
    assert(f.opacity >= 0.99, where + " opacity " + JSON.stringify(f));
    if (f.placeholder !== null)
      assert(f.placeholder >= 4.5, where + " placeholder " + JSON.stringify(f));
    assert(!f.fill.includes("rgba(0, 0, 0, 0)"), where + " transparent text");
  }
}
async function launchBrowser() {
  return chromium.launch({
    executablePath: await binary.executablePath(),
    args: binary.args.filter(
      (a) =>
        !a.includes("disable-web-security") &&
        !a.includes("allow-running-insecure-content"),
    ),
    env: { ...process.env, LD_LIBRARY_PATH: "/tmp/uniocr-chromium-libs/lib" },
  });
}
module.exports = { inspect, verify, launchBrowser };
if (require.main === module)
  (async () => {
    let b;
    try {
      for (const width of [1440, 1280, 834, 390].filter(
        (w) =>
          !process.env.UI_FIELD_WIDTH ||
          w === Number(process.env.UI_FIELD_WIDTH),
      )) {
        b = await launchBrowser();
        const c = await b.newContext({
          viewport: { width, height: 1000 },
          serviceWorkers: "block",
        });
        let p;
        const openGuardedPage = async () => {
          p = await c.newPage();
          p.on("pageerror", (e) => report.errors.push(e.message));
          await p.route("**/*", (r) => {
            if (!["GET", "HEAD"].includes(r.request().method())) {
              report.writes.push(r.request().method() + " " + r.request().url());
              return r.abort();
            }
            return r.continue();
          });
        };
        await openGuardedPage();
        await p.goto("http://127.0.0.1:8000/", {
          waitUntil: "domcontentloaded",
        });
        const routes = await p.evaluate(() =>
          Navigation.getConfig().flatMap((g) => [
            g.route,
            ...g.subitems.map((s) => s.route),
          ]),
        );
        for (const theme of ["light", "dark"]) {
          await p.evaluate((t) => {
            if (document.documentElement.dataset.theme !== t)
              document.getElementById("themeToggle").click();
            if (document.documentElement.dataset.theme !== t)
              throw Error("Theme not applied: " + t);
          }, theme);
          if (width === 1440) {
            await p.goto("http://127.0.0.1:8000/#dossiers/nouveau");
            await p.waitForTimeout(250);
            await p.evaluate(
              () =>
                (document.querySelector(
                  'link[href$="field-accessibility.css"]',
                ).disabled = true),
            );
            report.baseline.push({ theme, fields: await p.evaluate(inspect) });
            await p.evaluate(
              () =>
                (document.querySelector(
                  'link[href$="field-accessibility.css"]',
                ).disabled = false),
            );
            await p.keyboard.press("Escape");
          }
          for (const route of process.env.UI_FIELD_STATES_ONLY ? [] : routes) {
            await p.goto("http://127.0.0.1:8000/" + route);
            await p.waitForTimeout(400);
            await p.waitForFunction(
              (currentRoute) => {
                const definition =
                  window.UniOCREcrans?.ecrans?.[currentRoute.slice(1)];
                if (
                  definition &&
                  window.__ecranCourant?.ecran !== definition
                )
                  return false;
                return [...document.querySelectorAll("input,textarea,select")]
                  .filter((e) => e.getClientRects().length)
                  .every((e) => {
                    for (
                      let n = e;
                      n;
                      n = n.parentElement || n.getRootNode().host
                    )
                      if (Number(getComputedStyle(n).opacity) < 0.999)
                        return false;
                    return true;
                  });
              },
              route,
              { polling: 100, timeout: 30000 },
            );
            assert.equal(
              await p.locator("html").getAttribute("data-theme"),
              theme,
              "route theme persisted",
            );
            const rows = await p.evaluate(inspect);
            verify(rows, `${width} ${theme} ${route}`);
            report.routes.push({ width, theme, route, fields: rows.length });
            report.fields.push(
              ...rows.map((f) => ({ ...f, width, theme, route })),
            );
            if (route === "#dossiers/nouveau") await p.keyboard.press("Escape");
          }
          // Fresh document after route inventory releases historical module trees.
          await p.close();
          await openGuardedPage();
          await p.goto("http://127.0.0.1:8000/", {
            waitUntil: "domcontentloaded",
          });
          await p.evaluate((t) => {
            if (document.documentElement.dataset.theme !== t)
              document.getElementById("themeToggle").click();
            if (document.documentElement.dataset.theme !== t)
              throw Error("Theme not applied: " + t);
          }, theme);
          await p.goto("http://127.0.0.1:8000/#dossiers/nouveau");
          await p.waitForFunction(
            () => document.getElementById("dos-create")?.open,
            null,
            { polling: 100, timeout: 30000 },
          );
          const modal = p.locator("#dos-create");
          if (await modal.evaluate((e) => e.open)) {
            const field = modal.locator('input:not([type="hidden"])').first();
            await field.fill("Contraste réel — 0123");
            await field.hover();
            verify(await p.evaluate(inspect), "real creation form");
            await p.screenshot({
              timeout: 60000,
              path: path.join(out, `${width}-${theme}-creation.png`),
            });
            await p.keyboard.press("Escape");
          }
          await p.goto("http://127.0.0.1:8000/#cockpit");
          await p.evaluate(() => {
            const lab = document.createElement("section");
            lab.id = "field-audit-lab";
            lab.style.cssText =
              "position:fixed;inset:8px;z-index:2147483646;overflow:auto;padding:20px;background:var(--pe-paper);color:var(--pe-ink)";
            const h = document.createElement("h1");
            h.textContent =
              "Recette des contrôles natifs — laboratoire navigateur uniquement";
            lab.append(h);
            for (const type of [
              "text",
              "search",
              "password",
              "email",
              "url",
              "tel",
              "number",
              "date",
              "datetime-local",
              "time",
              "month",
              "week",
              "textarea",
              "select",
              "editable",
              "combobox",
              "file",
            ]) {
              const l = document.createElement("label");
              l.style.cssText =
                "display:inline-grid;width:280px;gap:8px;margin:8px";
              l.textContent = type;
              let e = document.createElement(
                type === "textarea"
                  ? "textarea"
                  : type === "select"
                    ? "select"
                    : type === "editable"
                      ? "div"
                      : "input",
              );
              e.id = "audit-" + type;
              if (e.tagName === "INPUT")
                e.type = type === "combobox" ? "text" : type;
              if (type === "number") e.step = "any";
              if (type === "combobox") e.setAttribute("role", "combobox");
              if (type === "editable") {
                e.contentEditable = "true";
                e.style.cssText =
                  "min-height:40px;border:1px solid;padding:8px";
              }
              if (type === "select")
                for (const txt of [
                  "Choisir une valeur",
                  "Algérie — sélection réelle",
                  "Oran",
                ]) {
                  const o = document.createElement("option");
                  o.textContent = txt;
                  e.append(o);
                }
              if (!["select", "editable"].includes(type))
                e.setAttribute("placeholder", "Saisie lisible — 0123");
              l.append(e);
              lab.append(l);
            }
            document.body.append(lab);
          });
          for (const type of [
            "text",
            "search",
            "password",
            "email",
            "url",
            "tel",
            "number",
            "date",
            "datetime-local",
            "time",
            "month",
            "week",
            "textarea",
            "select",
            "editable",
            "combobox",
            "file",
          ]) {
            const f = p.locator("#audit-" + type);
            if (type === "select") await f.focus();
            else if (type !== "file") await f.click();
            if (type === "file")
              await f.setInputFiles({
                name: "lecture-lisible.txt",
                mimeType: "text/plain",
                buffer: Buffer.from("recette locale"),
              });
            else if (type === "select") {
              await f.selectOption({ label: "Algérie — sélection réelle" });
              await p.keyboard.press("Escape");
            } else if (["month", "week"].includes(type)) {
              await f.evaluate((e, t) => {
                e.value = t === "month" ? "2026-11" : "2026-W45";
                e.dispatchEvent(new Event("input", { bubbles: true }));
              }, type);
            } else
              await f.fill(
                {
                  number: "12345.67",
                  date: "2026-11-04",
                  "datetime-local": "2026-11-04T14:30",
                  time: "14:30",
                  email: "audit@example.test",
                  url: "https://example.test",
                }[type] || "Lisibilité — 0123",
              );
            for (const state of [
              "filled",
              "hover",
              "focus",
              "error",
              "success",
              "readonly",
              "disabled",
            ]) {
              if (
                (type === "editable" &&
                  ["readonly", "disabled"].includes(state)) ||
                (["select", "file"].includes(type) && state === "readonly")
              )
                continue;
              await p.mouse.move(2, 2);
              await f.evaluate((e, state) => {
                e.blur();
                e.removeAttribute("aria-invalid");
                e.classList.remove("is-valid");
                e.removeAttribute("readonly");
                e.removeAttribute("disabled");
                if (state === "error") e.setAttribute("aria-invalid", "true");
                if (state === "success") e.classList.add("is-valid");
                if (state === "readonly") e.setAttribute("readonly", "");
                if (state === "disabled") e.setAttribute("disabled", "");
              }, state);
              if (state === "hover") await f.hover();
              if (state === "focus") await f.focus();
              await f.evaluate(async (e) => {
                getComputedStyle(e).borderTopColor;
                await Promise.all(
                  e
                    .getAnimations()
                    .filter((a) =>
                      Number.isFinite(a.effect.getComputedTiming().endTime),
                    )
                    .map((a) => a.finished.catch(() => {})),
                );
              });
              const rows = (await p.evaluate(inspect)).filter(
                (e) => e.id === "audit-" + type,
              );
              verify(rows, `${width} ${theme} ${type} ${state}`);
              const actual = await f.evaluate((e, state) => {
                const s = getComputedStyle(e),
                  probe = document.createElement("span");
                probe.style.color =
                  "var(--field-" +
                  (state === "error"
                    ? "error"
                    : state === "success"
                      ? "success"
                      : state === "focus" || state === "hover"
                        ? "focus"
                        : "border") +
                  ")";
                e.parentElement.append(probe);
                const expected = getComputedStyle(probe).color;
                probe.remove();
                return {
                  border: s.borderTopColor,
                  expected,
                  bg: s.backgroundColor,
                  muted: s.getPropertyValue("--field-muted-bg").trim(),
                };
              }, state);
              assert.equal(
                actual.border,
                actual.expected,
                `${type} ${state} semantic border`,
              );
              if (["readonly", "disabled"].includes(state)) {
                const expected = await f.evaluate((e) => {
                  const p = document.createElement("span");
                  p.style.background = "var(--field-muted-bg)";
                  e.parentElement.append(p);
                  const c = getComputedStyle(p).backgroundColor;
                  p.remove();
                  return c;
                });
                assert.equal(actual.bg, expected, `${type} ${state} surface`);
              }

              assert(
                rows[0].border >= 3,
                "field boundary " + JSON.stringify(rows),
              );
              if (state === "focus") {
                assert(rows[0].outline >= 3, "focus ring");
                assert(rows[0].caretRatio >= 4.5, "caret contrast");
              }
              report.states.push({ width, theme, type, state, ...rows[0] });
            }
            await f.evaluate((e) => {
              e.removeAttribute("disabled");
              e.removeAttribute("readonly");
            });
          }
          await p.screenshot({
            timeout: 60000,
            path: path.join(out, `${width}-${theme}-native-fields.png`),
          });
          const select = p.locator("#audit-select");
          await select.scrollIntoViewIfNeeded();
          await select.focus();
          await p.keyboard.press("Space");
          await p.screenshot({
            timeout: 60000,
            path: path.join(out, `${width}-${theme}-select-menu.png`),
          });
          await p.keyboard.press("Escape");
          console.log("Fields verified", width, theme);
          // Chrome's own autofill pseudo-state, without storing any credentials.
          const cdp = await c.newCDPSession(p);
          const { root } = await cdp.send("DOM.getDocument");
          const { nodeId } = await cdp.send("DOM.querySelector", {
            nodeId: root.nodeId,
            selector: "#audit-text",
          });
          await cdp.send("DOM.enable");
          await cdp.send("CSS.enable");
          await cdp.send("CSS.forcePseudoState", {
            nodeId,
            forcedPseudoClasses: ["autofill"],
          });
          verify(
            (await p.evaluate(inspect)).filter((e) => e.id === "audit-text"),
            "Chromium autofill",
          );
          report.states.push({
            width,
            theme,
            type: "text",
            state: "autofill",
            ...(await p.evaluate(inspect)).find((e) => e.id === "audit-text"),
          });
          await cdp.send("CSS.forcePseudoState", {
            nodeId,
            forcedPseudoClasses: [],
          });
          await cdp.detach();
          await p.evaluate(() => {
            const lab = document.getElementById("field-audit-lab");
            lab.querySelectorAll("label").forEach((l) => l.remove());
            lab.scrollTop = 0;
            for (const state of [
              "normal",
              "placeholder",
              "prefilled",
              "focus",
              "error",
              "success",
              "readonly",
              "disabled",
            ]) {
              const l = document.createElement("label");
              l.style.cssText =
                "display:inline-grid;width:280px;gap:8px;margin:8px";
              l.textContent = state;
              const e = document.createElement("input");
              e.type = "text";
              e.placeholder = "Placeholder lisible";
              e.value = ["normal", "placeholder"].includes(state)
                ? ""
                : "Valeur lisible — 0123";
              if (state === "error") e.setAttribute("aria-invalid", "true");
              if (state === "success") e.classList.add("is-valid");
              if (state === "readonly") e.readOnly = true;
              if (state === "disabled") e.disabled = true;
              if (state === "focus") e.id = "audit-focus-matrix";
              l.append(e);
              lab.append(l);
            }
          });
          await p.locator("#audit-focus-matrix").focus();
          verify(await p.evaluate(inspect), "visual state matrix");
          await p.screenshot({
            timeout: 60000,
            path: path.join(out, `${width}-${theme}-states.png`),
          });
          await p.evaluate(() =>
            document.getElementById("field-audit-lab").remove(),
          );
        }
        await c.close();
        await b.close();
        b = null;
      }
      assert.equal(report.errors.length, 0, JSON.stringify(report.errors));
      assert.equal(report.writes.length, 0, JSON.stringify(report.writes));
      console.log(
        JSON.stringify({
          routes: report.routes.length,
          fields: report.fields.length,
          states: report.states.length,
          minimumText: Math.min(
            ...report.fields.concat(report.states).map((x) => x.ratio),
          ),
          minimumPlaceholder: Math.min(
            ...report.fields
              .concat(report.states)
              .filter((x) => x.placeholder !== null)
              .map((x) => x.placeholder),
          ),
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
