"use strict";
const http = require("http");
const {JSDOM} = require("jsdom");

// Harnais Node uniquement : URL loopback, chemins fixes, sans redirection.
function readLocal(port, pathname) {
  if (!/^[0-9]{1,5}$/.test(String(port)) || Number(port) < 1 || Number(port) > 65535)
    return Promise.reject(new Error("port local invalide"));
  return new Promise((resolve, reject) => {
    const req = http.get({hostname: "127.0.0.1", port, path: pathname}, response => {
      if (response.statusCode !== 200) {
        response.resume(); reject(new Error(`HTTP ${response.statusCode} sur ${pathname}`)); return;
      }
      const chunks = []; let bytes = 0;
      response.on("data", chunk => {
        bytes += chunk.length;
        if (bytes > 2 * 1024 * 1024) response.destroy(new Error("réponse locale trop grande"));
        else chunks.push(chunk);
      });
      response.on("error", reject);
      response.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    });
    req.setTimeout(5000, () => req.destroy(new Error("délai HTTP local dépassé")));
    req.on("error", reject);
  });
}

async function loadServedModules(port, paths) {
  const html = await readLocal(port, "/");
  const dom = new JSDOM(html); // analyse seulement ; scripts et ressources non exécutés
  const scripts = [...dom.window.document.querySelectorAll("script[src]")]
    .map(script => script.getAttribute("src"));
  dom.window.close();
  const sources = {};
  for (const pathname of paths) {
    if (!/^\/[a-z]+\.js$/.test(pathname) || scripts.filter(p => p === pathname).length !== 1)
      throw new Error(`module servi absent, dupliqué ou chemin refusé : ${pathname}`);
    sources[pathname] = await readLocal(port, pathname);
  }
  return {html, sources};
}
module.exports = {readLocal, loadServedModules};
