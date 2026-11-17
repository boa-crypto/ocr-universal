/* Compteurs par run : lecture seule, pas calibration ni décision métier. */
(function () {
  "use strict";
  const esc = value => String(value).replace(/[&<>"']/g, c =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const count = value => Number.isInteger(value) && value >= 0 && value <= 10000;
  const pageNumber = value => Number.isSafeInteger(value) && value > 0;
  const mean = value => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;

  function provenance(run, page) {
    const p = run.confidence_provenance;
    if (run.engine !== "baidu" || run.ok !== true || !pageNumber(page) || run.page_num !== page ||
        !p || typeof p !== "object" || Array.isArray(p) ||
        Object.keys(p).sort().join(",") !== "calibrated,invalid,missing,policy,reported" ||
        p.policy !== "provider_average_else_zero" || p.calibrated !== false ||
        ![p.reported, p.missing, p.invalid, run.word_count].every(count) || !mean(run.mean_confidence)) return null;
    const total = p.reported + p.missing + p.invalid;
    const ceiling = total ? p.reported / total : 0;
    return total === run.word_count && total <= 10000 && run.mean_confidence <= ceiling ? p : null;
  }

  function render(pages) {
    const rows = [];
    for (const page of Array.isArray(pages) ? pages : []) {
      if (!page || !Array.isArray(page.engine_runs)) continue;
      page.engine_runs.forEach((value, index) => {
        const run = value && typeof value === "object" && !Array.isArray(value) ? value : {};
        const name = typeof run.engine === "string" ? run.engine : "Moteur inconnu";
        const pageLabel = pageNumber(page.page_num) ? page.page_num : "?";
        const status = run.ok === true ? "Run réussi" : run.ok === false ? "Échec du run" : "Statut non confirmé";
        const storedMean = mean(run.mean_confidence) ? `${Math.round(run.mean_confidence * 100)} %` : "indisponible";
        const elements = Number.isSafeInteger(run.word_count) && run.word_count >= 0 ? run.word_count : "indisponible";
        const duration = typeof run.duration_ms === "number" && Number.isFinite(run.duration_ms) && run.duration_ms >= 0 ?
          `${Math.round(run.duration_ms)} ms` : "indisponible";
        let detail = '<p>Provenance des scores non fournie pour ce moteur.</p>';
        if (name === "baidu") {
          const p = provenance(run, page.page_num);
          detail = p ? `<p class="engine-confidence-counts">${p.reported} déclaré(s) · ${p.missing} absent(s) · ${p.invalid} invalide(s)</p>
            <p>Compteurs par run, pas statut individuel par mot. Score non calibré.
            Zéro de repli si nécessaire, pas un score nul mesuré.${run.word_count === 0 ? " Run vide : aucun élément mesuré." : ""}</p>` :
            '<p class="engine-confidence-unavailable">Provenance indisponible : moyenne enregistrée non qualifiée. Aucun compteur déduit.</p>';
        }
        rows.push(`<section class="engine-run" aria-label="${esc(name)} — page ${pageLabel} — run ${index + 1}">
          <h4>${esc(name)} · page ${pageLabel} · run ${index + 1}</h4>
          <p>${status} · Moyenne enregistrée : ${storedMean}</p>
          <p>Éléments du run : ${elements} · Durée : ${duration}</p>${detail}</section>`);
      });
    }
    return rows.length ? '<p>Exécutions séparées, pouvant inclure plusieurs variantes. Pas de classement des moteurs ni de validation humaine ou juridique.</p>' + rows.join("") :
      '<div class="empty">Aucune trace d’exécution disponible.</div>';
  }
  window.UniOCREngineRuns = Object.freeze({render});
})();
