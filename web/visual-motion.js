/* Purposeful motion, progressive enhancement. Never animates business values. */
(function () {
  "use strict";
  function init() {
    if (document.documentElement.dataset.visualMotion) return;
    document.documentElement.dataset.visualMotion = "ready";
    var preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    var active = new Map();
    var revealed = new WeakSet();
    var pending = false;
    function enabled() {
      return !preference.matches && !document.hidden;
    }
    function animate(node, frames, duration, delay) {
      if (!enabled() || !node || typeof node.animate !== "function") return;
      if (active.has(node)) active.get(node).cancel();
      var animation = node.animate(frames, {
        duration: duration || 320,
        delay: delay || 0,
        easing: "cubic-bezier(.2,.7,.2,1)",
      });
      active.set(node, animation);
      function done() {
        if (active.get(node) === animation) active.delete(node);
      }
      animation.onfinish = done;
      animation.oncancel = done;
    }
    function stop() {
      active.forEach(function (animation) {
        animation.cancel();
      });
      active.clear();
    }
    preference.addEventListener("change", function () {
      if (preference.matches) stop();
    });
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stop();
    });
    var observer =
      typeof IntersectionObserver === "function"
        ? new IntersectionObserver(
            function (entries) {
              var index = 0;
              entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                observer.unobserve(entry.target);
                if (revealed.has(entry.target)) return;
                revealed.add(entry.target);
                animate(
                  entry.target,
                  [
                    { opacity: 0.86, transform: "translateY(8px)" },
                    { opacity: 1, transform: "translateY(0)" },
                  ],
                  380,
                  Math.min(index++ * 35, 140),
                );
              });
            },
            { threshold: 0.08 },
          )
        : null;
    function discover() {
      pending = false;
      if (!observer) return;
      document
        .querySelectorAll(".action-path,.kpi,.workspace .panel")
        .forEach(function (node) {
          if (!revealed.has(node)) observer.observe(node);
        });
    }
    function schedule() {
      if (!pending) {
        pending = true;
        requestAnimationFrame(discover);
      }
    }
    var workspace = document.querySelector("main.workspace");
    if (workspace)
      new MutationObserver(schedule).observe(workspace, {
        childList: true,
        subtree: true,
      });
    window.addEventListener("hashchange", function () {
      // Native routing remains in charge; add no artificial navigation delay.
      requestAnimationFrame(function () {
        var page = Array.from(document.querySelectorAll("section.page")).find(
          function (node) {
            return getComputedStyle(node).display !== "none";
          },
        );
        animate(
          page,
          [
            { opacity: 0.94, transform: "translateY(4px)" },
            { opacity: 1, transform: "none" },
          ],
          220,
        );
        schedule();
      });
    });
    var kpis = document.getElementById("cockpit-kpis");
    var values = new WeakMap();
    function feedback() {
      if (!kpis) return;
      kpis.querySelectorAll(".kpi-val").forEach(function (node) {
        var next = node.textContent;
        var previous = values.get(node);
        values.set(node, next);
        if (previous !== undefined && previous !== next) {
          animate(
            node,
            [
              { opacity: 0.55, transform: "translateY(3px)" },
              { opacity: 1, transform: "none" },
            ],
            300,
          );
        }
      });
    }
    if (kpis) {
      feedback();
      new MutationObserver(feedback).observe(kpis, {
        childList: true,
        characterData: true,
        subtree: true,
      });
    }
    // Pointer feedback is spatial, brief and bounded; no decorative infinite loop.
    document.addEventListener("click", function (event) {
      var button =
        event.target.closest &&
        event.target.closest(".btn,.action-path,.intent-trigger");
      if (button && !button.disabled)
        animate(
          button,
          [{ transform: "scale(.985)" }, { transform: "scale(1)" }],
          170,
        );
    });
    var actions = document.querySelector(".action-paths");
    if (actions) {
      var figure = document.createElement("figure");
      figure.className = "mobile-document-art";
      var image = document.createElement("img");
      image.src = "/web/assets/document-flow.svg";
      image.alt = "";
      image.width = 180;
      image.height = 120;
      image.loading = "lazy";
      image.decoding = "async";
      var caption = document.createElement("figcaption");
      caption.textContent =
        "De la pièce source aux champs structurés. Illustration du parcours documentaire.";
      figure.append(image, caption);
      actions.append(figure);
    }
    discover();
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
