// UniOCR - Transit Maritime Module
// Full-featured maritime transit management UI
// All data is sourced from the real API. No mock data.
(function () {
  "use strict";

  const API = window.__uniocr_api || (() => {});
  const BASE = window.__apiBase || "/api";

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ── Helper: badge ── */
  function badge(text, cls) {
    return `<span class="transit-badge transit-badge--${cls}">${esc(text)}</span>`;
  }

  /* ── Helper: status badge ── */
  function statusBadge(status) {
    const map = {
      nouveau: ["nouveau", "gray"],
      preparation: ["en préparation", "blue"],
      en_cours: ["en cours", "amber"],
      attente: ["en attente", "amber"],
      bloque: ["bloqué", "red"],
      livre: ["livré", "green"],
      cloture: ["clôturé", "gray"],
    };
    const [label, cls] = map[status] || [status, "gray"];
    return badge(label, cls);
  }

  /* ── Helper: priority badge ── */
  function priorityBadge(p) {
    const map = { critical: ["critique", "red"], high: ["haute", "amber"], normal: ["normale", "blue"], low: ["basse", "gray"] };
    const [label, cls] = map[p] || [p, "gray"];
    return badge(label, cls);
  }

  /* ── Dashboard KPIs ── */
  async function refreshDashboard() {
    try {
      const res = await fetch(`${BASE}/dossiers?limit=100`);
      if (!res.ok) return;
      const data = await res.json();
      const items = data.items || [];

      const total = items.length;
      const enCours = items.filter(d => d.status === "en_cours" || d.status === "preparation").length;
      const termines = items.filter(d => d.status === "livre" || d.status === "cloture").length;
      const erreurs = items.filter(d => d.status === "bloque").length;

      const el = id => $(id);
      if (el("transitTotal")) el("transitTotal").textContent = total;
      if (el("transitEnCours")) el("transitEnCours").textContent = enCours;
      if (el("transitTermines")) el("transitTermines").textContent = termines;
      if (el("transitErreurs")) el("transitErreurs").textContent = erreurs;
    } catch (e) {
      console.warn("[Transit] Dashboard refresh failed:", e);
    }
  }

  /* ── Recent Dossiers List ── */
  async function refreshRecent() {
    const box = $("transitDossiersRecent");
    if (!box) return;
    box.innerHTML = '<div class="muted">Chargement…</div>';
    try {
      const res = await fetch(`${BASE}/dossiers?limit=5&sort=-created_at`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items = data.items || [];
      if (!items.length) {
        box.innerHTML = '<div class="transit-empty"><div class="transit-empty__icon">⚓</div><div class="transit-empty__text">Aucun dossier de transit</div></div>';
        return;
      }
      let html = '<div class="doc-list">';
      items.forEach(d => {
        const conf = d.quality ? Math.round(d.quality.global * 100) : "—";
        html += `
          <div class="doc-item" data-dossier="${esc(d.id)}">
            <div class="doc-item__icon">${(d.ref || "TR").slice(0, 4)}</div>
            <div class="doc-item__info">
              <div class="doc-item__name">${esc(d.ref || d.id)}</div>
              <div class="doc-item__meta">${esc(d.client || "—")} · ${new Date(d.created_at).toLocaleDateString("fr-FR")}</div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
              ${statusBadge(d.status)}
              <span class="doc-item__conf" style="color:${confidenceColor(conf)}">${conf}%</span>
            </div>
          </div>`;
      });
      html += "</div>";
      box.innerHTML = html;
      box.querySelectorAll(".doc-item").forEach(el => {
        el.addEventListener("click", () => openDossier(el.dataset.dossier));
      });
    } catch (e) {
      box.innerHTML = `<div class="muted">Erreur: ${esc(e.message)}</div>`;
    }
  }

  /* ── Confidence Color ── */
  function confidenceColor(v) {
    if (v === "—") return "var(--color-fg-muted)";
    if (v >= 90) return "var(--semantic-success)";
    if (v >= 75) return "var(--brand-secondary)";
    if (v >= 60) return "var(--brand-accent)";
    return "var(--semantic-error)";
  }

  /* ── Open Dossier Detail ── */
  let currentDossierId = null;

  async function openDossier(id) {
    currentDossierId = id;
    const el = $("transitDossierDetail");
    if (!el) return;
    el.innerHTML = '<div class="muted">Chargement du dossier…</div>';

    try {
      const res = await fetch(`${BASE}/dossiers/${encodeURIComponent(id)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      renderDossierDetail(d);
    } catch (e) {
      el.innerHTML = `<div class="muted">Erreur: ${esc(e.message)}</div>`;
    }
  }

  function renderDossierDetail(d) {
    const el = $("transitDossierDetail");
    if (!el) return;

    const conf = d.quality ? Math.round(d.quality.global * 100) : 0;
    const created = d.created_at ? new Date(d.created_at).toLocaleString("fr-FR") : "—";
    const updated = d.updated_at ? new Date(d.updated_at).toLocaleString("fr-FR") : "—";

    const progressPct = Math.min(100, Math.round(conf * 0.8 + (d.status === "cloture" ? 20 : 0)));

    const docs = (d.documents || []).map(doc => `
      <div class="doc-item">
        <div class="doc-item__icon">${doc.type || "DOC"}</div>
        <div class="doc-item__info">
          <div class="doc-item__name">${esc(doc.filename || doc.name || "Document")}</div>
          <div class="doc-item__meta">${esc(doc.type || "document")} · ${(doc.size ? (doc.size / 1024).toFixed(1) : "—")} KB</div>
        </div>
        <span class="doc-item__conf" style="color:${confidenceColor(doc.confidence ? Math.round(doc.confidence * 100) : "—")}">${doc.confidence ? Math.round(doc.confidence * 100) + "%" : "—"}</span>
      </div>`).join("");

    const anomalies = (d.anomalies || []).slice(0, 10).map(a => `
      <div class="anomaly-item anomaly-item--${a.severity === "error" ? "error" : a.severity === "warning" ? "warning" : "info"}">
        <span class="anomaly-item__type">${esc(a.type || "anomalie")}</span>
        <span class="anomaly-item__text">${esc(a.message || a.description || "—")}</span>
      </div>`).join("");

    const containers = (d.containers || []).slice(0, 5).map(c => `
      <div class="container-card">
        <div class="container-card__header">
          <span class="container-card__iso">${esc(c.iso || c.number || "—")}</span>
          ${badge(c.type || "standard", "blue")}
        </div>
        <dl class="container-card__grid">
          <dt>Dimensions</dt><dd>${esc(c.dimensions || "—")}</dd>
          <dt>Poids</dt><dd>${esc(c.weight ? c.weight + " kg" : "—")}</dd>
          <dt>Cargaison</dt><dd>${esc(c.cargo || "—")}</dd>
          <dt>État</dt><dd>${statusBadge(c.status)}</dd>
        </dl>
      </div>`).join("");

    const fees = (d.fees || []).slice(0, 10).map(f => `
      <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--color-border);font-size:var(--text-sm)">
        <span style="color:var(--color-fg)">${esc(f.type || f.label || "Frais")}</span>
        <span style="font-family:var(--font-mono);font-weight:var(--font-weight-semibold);color:var(--brand-secondary)">${f.amount ? f.amount + " " + (f.currency || "€") : "—"}</span>
      </div>`).join("");

    const timeline = [
      { time: created, title: "Dossier créé", desc: "Création du dossier de transit", done: true },
      { time: d.updated_at ? new Date(d.updated_at).toLocaleString("fr-FR") : "—", title: "Dernière mise à jour", desc: "Statut: " + (d.status || "—"), done: d.status !== "nouveau", active: d.status !== "nouveau" && d.status !== "cloture" },
      { time: d.status === "cloture" ? new Date(d.updated_at).toLocaleString("fr-FR") : "—", title: "Clôture", desc: d.status === "cloture" ? "Dossier clôturé" : "En attente", done: d.status === "cloture" },
    ].map(t => `
      <div class="dossier-timeline__step ${t.done ? "done" : ""} ${t.active ? "active" : ""}">
        <div class="dossier-timeline__dot"></div>
        <div class="dossier-timeline__time">${esc(t.time)}</div>
        <div class="dossier-timeline__title">${esc(t.title)}</div>
        <div class="dossier-timeline__desc">${esc(t.desc)}</div>
      </div>`).join("");

    const html = `
      <div class="transit-animate">
        <!-- Header -->
        <div class="dossier-header">
          <div class="dossier-header__top">
            <div>
              <div class="dossier-header__ref">${esc(d.ref || d.id)}</div>
              <div style="font-size:var(--text-sm);opacity:0.8;margin-top:4px">${esc(d.client || "Client inconnu")}</div>
            </div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              ${statusBadge(d.status)}
              ${d.priority ? priorityBadge(d.priority) : ""}
            </div>
          </div>
          <div class="dossier-header__meta">
            <div class="dossier-header__field">
              <span class="dossier-header__field-label">Navire</span>
              <span class="dossier-header__field-value">${esc(d.vessel || "—")}</span>
            </div>
            <div class="dossier-header__field">
              <span class="dossier-header__field-label">ETA</span>
              <span class="dossier-header__field-value">${esc(d.eta ? new Date(d.eta).toLocaleDateString("fr-FR") : "—")}</span>
            </div>
            <div class="dossier-header__field">
              <span class="dossier-header__field-label">Gestionnaire</span>
              <span class="dossier-header__field-value">${esc(d.manager || "—")}</span>
            </div>
            <div class="dossier-header__field">
              <span class="dossier-header__field-label">Créé le</span>
              <span class="dossier-header__field-value">${esc(created)}</span>
            </div>
          </div>
        </div>

        <!-- Progress -->
        <div class="dossier-progress">
          <div class="dossier-progress__label">
            <span>Progression du traitement</span>
            <span>${conf}% confiance globale</span>
          </div>
          <div class="dossier-progress__bar">
            <div class="dossier-progress__fill" style="width:${progressPct}%"></div>
          </div>
        </div>

        <!-- Section Tabs -->
        <div class="dossier-sections">
          <button class="dossier-sections__tab active" data-section="timeline">Chronologie</button>
          <button class="dossier-sections__tab" data-section="docs">Documents (${(d.documents || []).length})</button>
          <button class="dossier-sections__tab" data-section="anomalies">Anomalies (${(d.anomalies || []).length})</button>
          <button class="dossier-sections__tab" data-section="containers">Conteneurs (${(d.containers || []).length})</button>
          <button class="dossier-sections__tab" data-section="fees">Frais (${(d.fees || []).length})</button>
        </div>

        <!-- Section Content -->
        <div id="transitSectionContent">
          <div class="transit-panel" data-section-panel="timeline">
            <div class="transit-panel__body">
              <div class="dossier-timeline">${timeline}</div>
            </div>
          </div>
          <div class="transit-panel" data-section-panel="docs" style="display:none">
            <div class="transit-panel__body">
              ${docs || '<div class="muted">Aucun document attaché</div>'}
            </div>
          </div>
          <div class="transit-panel" data-section-panel="anomalies" style="display:none">
            <div class="transit-panel__body">
              ${anomalies || '<div class="muted">Aucune anomalie détectée</div>'}
            </div>
          </div>
          <div class="transit-panel" data-section-panel="containers" style="display:none">
            <div class="transit-panel__body">
              ${containers || '<div class="muted">Aucun conteneur associé</div>'}
            </div>
          </div>
          <div class="transit-panel" data-section-panel="fees" style="display:none">
            <div class="transit-panel__body">
              ${fees || '<div class="muted">Aucun frais enregistré</div>'}
            </div>
          </div>
        </div>
      </div>`;

    el.innerHTML = html;

    // Section tab clicks
    el.querySelectorAll(".dossier-sections__tab").forEach(btn => {
      btn.addEventListener("click", () => {
        el.querySelectorAll(".dossier-sections__tab").forEach(b => b.classList.remove("active"));
        el.querySelectorAll("[data-section-panel]").forEach(p => p.style.display = "none");
        btn.classList.add("active");
        const panel = el.querySelector(`[data-section-panel="${btn.dataset.section}"]`);
        if (panel) panel.style.display = "";
      });
    });
  }

  /* ── Create Dossier ── */
  async function createDossier() {
    const ref = $("transitRef")?.value.trim();
    const client = $("transitClient")?.value.trim();
    const msg = $("transitMsg");
    if (!msg) return;
    if (!ref) { msg.textContent = "Référence requise"; msg.style.color = "var(--semantic-error)"; return; }

    msg.textContent = "Création…";
    msg.style.color = "var(--color-fg-muted)";
    try {
      const res = await fetch(`${BASE}/dossiers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ref, client, status: "nouveau" }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      msg.textContent = `Créé: ${d.id || ref}`;
      msg.style.color = "var(--semantic-success)";
      $("transitRef").value = "";
      $("transitClient").value = "";
      refreshDashboard();
      refreshRecent();
    } catch (e) {
      msg.textContent = `Erreur: ${e.message}`;
      msg.style.color = "var(--semantic-error)";
    }
  }

  /* ── OCR Analysis in Transit ── */
  let _transitFile = null;

  function setupTransitDropzone() {
    const dz = $("transitDropZone");
    const fi = $("transitFileInput");
    if (!dz || !fi) return;

    dz.addEventListener("click", () => fi.click());
    dz.addEventListener("dragover", e => { e.preventDefault(); dz.style.borderColor = "var(--brand-secondary)"; });
    dz.addEventListener("dragleave", () => { dz.style.borderColor = ""; });
    dz.addEventListener("drop", e => {
      e.preventDefault();
      dz.style.borderColor = "";
      const file = e.dataTransfer.files[0];
      if (file) handleTransitFile(file);
    });
    fi.addEventListener("change", () => {
      if (fi.files[0]) handleTransitFile(fi.files[0]);
    });
  }

  function handleTransitFile(file) {
    _transitFile = file;
    const nameEl = $("transitFileName");
    const sizeEl = $("transitFileSize");
    if (nameEl) nameEl.textContent = file.name;
    if (sizeEl) sizeEl.textContent = (file.size / 1024).toFixed(1) + " KB";
    const btn = $("transitAnalyser");
    if (btn) btn.disabled = false;
  }

  async function runTransitOcr() {
    if (!_transitFile) return;
    const statEl = $("transitStatutOcr");
    const msgEl = $("transitMsg");
    if (statEl) statEl.textContent = "Analyse en cours…";
    if (msgEl) { msgEl.textContent = ""; msgEl.style.color = ""; }

    try {
      const form = new FormData();
      form.append("file", _transitFile);
      form.append("profile", "generic");
      form.append("quality_mode", "accurate");

      const res = await fetch(`${BASE}/process`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();

      if (statEl) statEl.textContent = "Terminé ✓";
      if (msgEl) { msgEl.textContent = `Confiance: ${Math.round((result.quality?.global || 0) * 100)}%`; msgEl.style.color = "var(--semantic-success)"; }

      // Show preview
      const ap = $("transitApercu");
      if (ap) {
        ap.innerHTML = `<div class="muted" style="font-size:12px;line-height:1.8;max-height:200px;overflow-y:auto">
          ${esc(result.text?.slice(0, 500) || "Aucun texte extrait")}
        </div>`;
      }

      // Show anomalies
      const an = $("transitAnomalies");
      if (an && result.anomalies?.length) {
        an.innerHTML = result.anomalies.slice(0, 5).map(a =>
          `<div class="anomaly-item anomaly-item--${a.severity === "error" ? "error" : "warning"}" style="margin-bottom:8px">
            <span class="anomaly-item__type">${esc(a.type)}</span>
            <span class="anomaly-item__text">${esc(a.message)}</span>
          </div>`
        ).join("");
      }

      // Show actions
      const act = $("transitActions");
      if (act) {
        act.innerHTML = `<div style="display:flex;flex-direction:column;gap:8px">
          <button class="btn btn-sm" onclick="window.__uniocr_open_dossier('${result.job_id || result.id}')">Ouvrir le dossier</button>
          <button class="btn btn-sm btn-ghost" onclick="window.location.href='${BASE}/jobs/${encodeURIComponent(result.job_id || result.id)}/export/json'">Exporter JSON</button>
        </div>`;
      }

      refreshDashboard();
    } catch (e) {
      if (statEl) statEl.textContent = "Erreur";
      if (msgEl) { msgEl.textContent = e.message; msgEl.style.color = "var(--semantic-error)"; }
    }
  }

  /* ── Init ── */
  function init() {
    refreshDashboard();
    refreshRecent();
    setupTransitDropzone();

    const creerBtn = $("transitCreer");
    if (creerBtn) creerBtn.addEventListener("click", createDossier);

    const analyserBtn = $("transitAnalyser");
    if (analyserBtn) analyserBtn.disabled = true;
    if (analyserBtn) analyserBtn.addEventListener("click", runTransitOcr);

    // Expose for section tab clicks
    window.__uniocr_open_dossier = openDossier;
  }

  // Run when DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Also listen for hash changes (nav clicks)
  window.addEventListener("hashchange", () => {
    if (location.hash === "#transit" || document.getElementById("tab-transit")?.classList.contains("active")) {
      refreshDashboard();
      refreshRecent();
    }
  });
})();
