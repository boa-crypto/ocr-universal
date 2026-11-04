
/* PWA : installe la coquille hors ligne. Silencieux si l'API n'est pas là. */
if ("serviceWorker" in navigator && location.protocol !== "file:") {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function () {});
  });
}
