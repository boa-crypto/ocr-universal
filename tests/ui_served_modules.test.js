"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const http = require("http");
const {loadServedModules, readLocal} = require("./served_modules");
const {validateRenderOutput} = require("./render_output");
async function withServer(handler, action) {
  const server = http.createServer(handler);
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  try { await action(server.address().port); }
  finally { await new Promise(resolve => server.close(resolve)); }
}
const tag = '<script src="/dossier.js" defer></script>';
test("charge exactement les octets HTTP référencés, pas une copie disque", async () => {
  const requests = [];
  await withServer((req, res) => {
    requests.push(req.url); res.end(req.url === "/" ? tag : "REMOTE_ONLY");
  }, async port => {
    const result = await loadServedModules(port, ["/dossier.js"]);
    assert.equal(result.sources["/dossier.js"], "REMOTE_ONLY");
    assert.deepEqual(requests, ["/", "/dossier.js"]);
  });
});
for (const html of ["", tag + tag, '<script src="https://example.org/dossier.js"></script>',
  '<script src="/dossier.js?x=1"></script>',
  '<script data-src="/dossier.js"></script>', '<!-- ' + tag + ' -->',
  '<script data-note="src=\'/dossier.js\'"></script>']) {
  test("refuse référence absente/dupliquée/externe/alias : " + html, async () => {
    await withServer((req, res) => res.end(html), async port => {
      await assert.rejects(loadServedModules(port, ["/dossier.js"]), /module servi/);
    });
  });
}
for (const status of [302, 401, 404, 500]) {
  test("refuse HTTP " + status + " sans redirection ni repli", async () => {
    await withServer((req, res) => {
      res.statusCode = req.url === "/" ? 200 : status;
      res.setHeader("Location", "/dossier.js"); res.end(tag);
    }, async port => assert.rejects(loadServedModules(port, ["/dossier.js"]), /HTTP/));
  });
}
test("borne les réponses", async () => {
  await withServer((req, res) => res.end("x".repeat(2 * 1024 * 1024 + 1)),
    async port => assert.rejects(readLocal(port, "/"), /trop grande/));
});
for (const port of ["0", "65536", "abc", "80/path"]) {
  test("refuse port invalide " + port, async () => {
    await assert.rejects(readLocal(port, "/"), /port local invalide/);
  });
}
test("accepte tous les contrôles attendus", () => {
  assert.equal(validateRenderOutput("[OK] un\n[OK] deux", 2), 2);
});
for (const output of ["", "[OK] un", "[OK] un\n[FAIL] deux", "[OK] un\n[OK] deux\n[REJET] exception",
  "[OK] un\n[OK] deux\n[THROW] exception", "[OK] un\n[OK] deux\n[NON GERE] exception"]) {
  test("refuse bilan incomplet ou erreur : " + output, () => {
    assert.throws(() => validateRenderOutput(output, 2), /contrôles/);
  });
}
