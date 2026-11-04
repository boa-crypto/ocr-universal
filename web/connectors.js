/* ═══════════════ CONNECTEUR HUB ═══════════════
   Rubrique « Connecteurs » : 12 sous-menus, assistant de création en 9 étapes,
   écran de validation avant transmission. Aucune ressource externe, aucun appel
   réseau non sollicité par l'utilisateur.                                     */
const CnxHub = (() => {
  const $ = id => document.getElementById(id);
  const STATE_LABEL = {
    unconfigured: ["Non configuré", "off"],
    to_test: ["À tester", "warn"],
    connected: ["Connecté", "info"],
    functional: ["Fonctionnel", "ok"],
    degraded: ["Dégradé", "warn"],
    auth_expired: ["Authentification expirée", "err"],
    error: ["Erreur", "err"],
    disabled: ["Désactivé", "off"],
  };
  const SECTIONS = [
    ["overview", "Vue d'ensemble"], ["catalog", "Catalogue"],
    ["active", "Connecteurs actifs"], ["add", "Ajouter"],
    ["config", "Configuration"], ["mapping", "Correspondance des champs"],
    ["forms", "Modèles de formulaires"], ["flow", "Flux d'intégration"],
    ["history", "Historique"], ["errors", "Erreurs et reprises"],
    ["security", "Sécurité"], ["audit", "Journaux d'audit"],
  ];
  const WIZARD = [
    ["organisme", "Organisme", "Quel système doit recevoir vos documents ?"],
    ["mode", "Mode d'intégration", "A — API officielle, B — préremplissage autorisé, C — export assisté."],
    ["acces", "Accès et environnement", "Environnement de test ou production, et niveau d'accès obtenu."],
    ["test", "Test de connexion", "Un test réel détermine l'état du connecteur."],
    ["schema", "Schéma du formulaire", "Champs attendus, obligatoires et formats."],
    ["mapping", "Correspondance", "Règles explicites entre champs extraits et champs cibles."],
    ["essai", "Essai sur document non sensible", "Préremplissage sans transmission."],
    ["validation", "Validation humaine", "Vérification et confirmation avant tout envoi."],
    ["activation", "Activation", "Le connecteur devient utilisable."],
  ];
  let section = "overview", wizardStep = 0, wizard = {};

  /* ─────────────── sous-menus ─────────────── */
  function renderSubnav() {
    $("cnxSubnav").innerHTML = SECTIONS.map(([k, label], i) =>
      `<button class="cnx-sub${k === section ? " on" : ""}" data-cnx="${k}" role="tab">
         <i>${String(i + 1).padStart(2, "0")}</i>${esc(label)}</button>`).join("");
    $("cnxSubnav").querySelectorAll("[data-cnx]").forEach(b =>
      b.addEventListener("click", () => show(b.dataset.cnx)));
  }
  function show(k) {
    section = k;
    document.querySelectorAll(".cnx-sub").forEach(b =>
      b.classList.toggle("on", b.dataset.cnx === k));
    document.querySelectorAll(".cnx-pane").forEach(p =>
      p.classList.toggle("hidden", p.dataset.cnx !== k));
    if (k === "overview") loadOverview();
    if (k === "catalog") loadCatalog();
    if (k === "active") loadActive();
    if (k === "add") renderWizard();
    if (k === "config") loadConfig();
    if (k === "flow") loadModes();
    if (k === "mapping") loadMapping();
    if (k === "forms") loadForms();
    if (k === "history") loadHistory();
    if (k === "errors") loadErrors();
    if (k === "security") loadSecurity();
    if (k === "audit") loadAudit();
  }

  const badge = (text, kind) => `<span class="cnx-badge ${kind || ""}">${esc(text)}</span>`;
  const stateBadge = st => { const [l, k] = STATE_LABEL[st] || [st, "off"]; return badge(l, k); };
  const empty = (msg) => `<div class="cnx-empty">${esc(msg)}</div>`;
  const TX_LABEL = {
    total: "Total", by_status: "Par statut", accepted: "Acceptée",
    pending_confirmation: "Issue à confirmer", rejected: "Rejet métier",
    failed: "Échec technique", sent: "Envoyée", pending: "En attente",
    cancelled: "Annulée", created: "Créée", max_auto_retries: "Reprises auto max",
  };

  /* ─────────────── 01 · vue d'ensemble ─────────────── */
  async function loadOverview() {
    let d;
    try { d = await api("/api/connectors"); } catch (e) { d = null; }
    const sum = d?.summary || {};
    const cards = [
      ["Adaptateurs disponibles", String(sum.adapters ?? "—"),
        "Façons de parler à un type de système. Les ajouter ne connecte à rien."],
      ["Connecteurs configurés", String(sum.configured ?? "—"),
        "Instances réelles, avec leur état et leur dernier test."],
      ["Opérationnels", String(sum.operational ?? "—"),
        "État acquis par un test réel, jamais par un interrupteur."],
      ["Intégrations réelles", String(sum.real_external_adapters ?? "—"),
        "0 ici : aucun accès externe autorisé n'est documenté."],
    ];
    $("cnxOverview").innerHTML =
      cards.map(([t, v, s]) => `<div class="cnx-card">
          <h4>${esc(t)}</h4>
          <div class="mono" style="font-size:26px;color:var(--accent)">${esc(v)}</div>
          <p>${esc(s)}</p></div>`).join("") +
      `<div class="cnx-card" style="grid-column:1/-1">
         <h4>Transmissions</h4>
         <div class="cnx-kv" id="cnxOvTx"></div>
       </div>
       <div class="cnx-card" style="grid-column:1/-1">
         <h4>Ce que cette rubrique ne fait pas</h4>
         <p>Elle ne contacte aucun organisme sans configuration et test explicites,
            ne devine aucun champ d'un système auquel elle n'a pas accès, et ne
            présente jamais le connecteur de démonstration comme une intégration réelle.</p>
       </div>`;
    try {
      const st = await api("/api/connectors/transmissions?limit=5");
      const s = st.stats || {};
      $("cnxOvTx").innerHTML =
        `<dt>Total</dt><dd>${s.total ?? 0}</dd>
         <dt>Acceptées</dt><dd>${s.accepted ?? 0}</dd>
         <dt>En attente de confirmation</dt><dd>${s.pending_confirmation ?? 0}</dd>
         <dt>Rejets métier</dt><dd>${s.rejected ?? 0}</dd>
         <dt>Échecs techniques</dt><dd>${s.failed ?? 0}</dd>
         <dt>Reprises automatiques max</dt><dd>${s.max_auto_retries ?? "—"}</dd>`;
    } catch { $("cnxOvTx").innerHTML = "<dt>Statut</dt><dd>indisponible</dd>"; }
  }

  /* ─────────────── 02 · catalogue ─────────────── */
  async function loadCatalog() {
    let rows = [];
    try { rows = await api("/api/connectors/catalog"); } catch { rows = []; }
    $("cnxCatalog").innerHTML = rows.length ? rows.map(c => `<div class="cnx-card">
        <h4>${esc(c.name || c.connector_id)}
          ${c.is_real_external_system ? badge("SYSTÈME RÉEL", "info") : badge("SIMULÉ", "off")}</h4>
        <p>${esc(c.description || "")}</p>
        <div class="cnx-kv">
          <dt>Identifiant</dt><dd class="mono">${esc(c.connector_id)}</dd>
          <dt>Mode</dt><dd class="mono">${esc(c.mode || "—")}</dd>
          <dt>Système</dt><dd class="mono">${esc(c.system_type || "—")}</dd>
          <dt>Capacités</dt><dd class="mono">${esc((c.capabilities || []).join(", ") || "—")}</dd>
        </div>
        <div class="cnx-acts">
          <button class="btn ghost" data-add="${esc(c.connector_id)}">Configurer…</button>
        </div></div>`).join("") : empty("Aucun adaptateur enregistré.");
    $("cnxCatalog").querySelectorAll("[data-add]").forEach(b =>
      b.addEventListener("click", () => { wizard = { connector_id: b.dataset.add };
        show("add"); }));
  }

  /* ─────────────── 03 · connecteurs configurés ─────────────── */
  async function loadActive() {
    let rows = [];
    try { rows = await api("/api/connectors/configured"); } catch { rows = []; }
    $("cnxActive").innerHTML = rows.length ? rows.map(c => `<div class="cnx-card">
        <h4>${esc(c.name || c.connector_id)} ${stateBadge(c.state)}</h4>
        <div class="cnx-kv">
          <dt>Dernier test</dt><dd>${c.last_test ? esc(c.last_test.detail || "—") + " (" +
            esc(c.last_test.ok ? "succès" : "échec") + ")" : "jamais testé"}</dd>
          <dt>Tests effectués</dt><dd>${c.test_count ?? 0}</dd>
          <dt>Erreurs</dt><dd>${c.error_count ?? 0}</dd>
        </div>
        <div class="cnx-acts">
          <button class="btn ghost" data-tst="${esc(c.connector_id)}">Tester la connexion</button>
          <button class="btn ghost" data-cfg="${esc(c.connector_id)}">Configuration</button>
          <button class="btn ghost" data-sec="${esc(c.connector_id)}">Secrets</button>
          ${c.state === "disabled"
            ? `<button class="btn ghost" data-ena="${esc(c.connector_id)}">Réactiver</button>`
            : `<button class="btn ghost" data-dis="${esc(c.connector_id)}">Désactiver</button>`}
        </div>
        <div class="mono" data-out="${esc(c.connector_id)}"></div>
      </div>`).join("") : empty("Aucun connecteur configuré. Passez par « Ajouter ».");
    const out = id => $(`cnxActive [data-out="${id}"]`);
    $("cnxActive").querySelectorAll("[data-tst]").forEach(b =>
      b.addEventListener("click", async () => {
        const id = b.dataset.tst;
        out(id).textContent = "Test en cours…";
        try {
          const r = await api(`/api/connectors/${encodeURIComponent(id)}/test`, { method: "POST", body: "{}" });
          out(id).innerHTML = `<span class="${r.ok ? "cnx-okbox" : "cnx-errbox"}" style="display:block">
            ${esc(r.detail || "")} · état : ${esc(r.state)} · ${Math.round(r.latency_ms || 0)} ms</span>`;
        } catch (e) { out(id).innerHTML = `<span class="cnx-errbox" style="display:block">${esc(e.message)}</span>`; }
        loadActive(); loadOverview();
      }));
    $("cnxActive").querySelectorAll("[data-cfg]").forEach(b =>
      b.addEventListener("click", () => { cfgTarget = b.dataset.cfg; show("config"); }));
    $("cnxActive").querySelectorAll("[data-sec]").forEach(b =>
      b.addEventListener("click", () => { secTarget = b.dataset.sec; show("security"); }));
    $("cnxActive").querySelectorAll("[data-dis]").forEach(b =>
      b.addEventListener("click", async () => {
        await api(`/api/connectors/${encodeURIComponent(b.dataset.dis)}/disable`, { method: "POST", body: "{}" });
        loadActive(); loadOverview();
      }));
    $("cnxActive").querySelectorAll("[data-ena]").forEach(b =>
      b.addEventListener("click", async () => {
        await api(`/api/connectors/${encodeURIComponent(b.dataset.ena)}/enable`, { method: "POST", body: "{}" });
        loadActive(); loadOverview();
      }));
  }

  /* ─────────────── 04 · assistant en 9 étapes ─────────────── */
  function renderWizard() {
    $("cnxSteps").innerHTML = WIZARD.map(([k, l], i) =>
      `<li class="${i === wizardStep ? "on" : ""}${i < wizardStep ? " done" : ""}">${esc(l)}</li>`).join("");
    const [k, title, help] = WIZARD[wizardStep];
    let body = "";
    if (k === "organisme") {
      body = `<p>${esc(help)}</p>
        <div class="cnx-form">
          <label>Adaptateur
            <select id="wzAdapter">
              <option value="demo_simulated">Simulateur local (démonstration)</option>
              <option value="assisted_export">Export assisté (CSV + correspondance)</option>
            </select></label>
          <label>Nom d'usage<input id="wzName" placeholder="ex. Démonstration interne"></label>
          <label>Note<textarea id="wzNote" rows="2"
            placeholder="À quoi sert ce connecteur ?"></textarea></label>
        </div>`;
    } else if (k === "mode") {
      body = `<p>${esc(help)}</p><div class="cnx-modes">
        <div class="cnx-mode"><h4>Mode A <span class="tag">API</span></h4>
          <p>API officielle. Exige un accès autorisé et documenté — aucun
             connecteur de ce type n'est livré ici.</p></div>
        <div class="cnx-mode"><h4>Mode B <span class="tag">Web</span></h4>
          <p>Préremplissage d'un formulaire autorisé, sans contournement des
             protections du site.</p></div>
        <div class="cnx-mode"><h4>Mode C <span class="tag">Export</span></h4>
          <p>Export structuré à importer manuellement. Le plus contrôlé.</p></div>
      </div>
      <div class="cnx-form" style="margin-top:12px">
        <label>Mode retenu
          <select id="wzMode">
            <option value="api">A — API officielle</option>
            <option value="web_form">B — Préremplissage web autorisé</option>
            <option value="assisted_export" selected>C — Export assisté</option>
            <option value="simulated">Simulation locale (démonstration)</option>
          </select></label>
        <label>Environnement
          <select id="wzEnv"><option value="test">Test</option>
            <option value="production">Production</option></select></label>
      </div>`;
    } else if (k === "acces") {
      body = `<p>${esc(help)}</p>
        <div class="cnx-form">
          <label>Identifiant d'accès (nom du secret, pas sa valeur)
            <input id="wzSecretName" placeholder="ex. api_key"></label>
          <div class="cnx-warnbox">La valeur du secret n'est jamais affichée ni
            stockée en clair : elle est chiffrée (AES-256-GCM) dans le coffre
            local, et seuls ses noms sont visibles.</div>
        </div>`;
    } else if (k === "test") {
      body = `<p>${esc(help)}</p>
        <div class="cnx-warnbox">L'état du connecteur ne change qu'après un test
          réel. Un simple enregistrement laisse le connecteur « à tester ».</div>
        <div class="mono" id="wzTestOut">Aucun test lancé.</div>`;
    } else if (k === "schema") {
      body = `<p>${esc(help)}</p>
        <p>Deux sources : les formulaires déclarés par un connecteur
           (<span class="mono">source=declared</span> ou
           <span class="mono">discovered</span>), et les modèles que vous créez
           dans « Modèles de formulaires ». Sans accès au système cible, aucune
           structure n'est devinée.</p>
        <div id="wzForms"></div>`;
    } else if (k === "mapping") {
      body = `<p>${esc(help)}</p>
        <div class="cnx-warnbox">Le moteur propose des correspondances par
          similarité mais ne les applique jamais seul : chaque règle reste
          explicite, versionnée et traçable.</div>
        <div id="wzMap"></div>`;
    } else if (k === "essai") {
      body = `<p>${esc(help)}</p>
        <div class="cnx-form">
          <label>Identifiant de document traité<input id="wzJob"
            placeholder="ex. job_ab12cd34"></label>
          <label>Formulaire cible<input id="wzForm" placeholder="ex. demo_declaration"></label>
        </div>
        <div id="wzPreview"></div>`;
    } else if (k === "validation") {
      body = `<p>${esc(help)}</p>
        <div class="cnx-warnbox">Rien n'est transmis sans confirmation explicite.
          Les champs obligatoires manquants, les erreurs de format et les
          suggestions non validées bloquent l'envoi.</div>`;
    } else {
      body = `<p>${esc(help)}</p>
        <div class="cnx-okbox">Le connecteur sera créé à l'état « à tester ».
          Lancez ensuite un test réel depuis « Connecteurs actifs » pour le
          rendre opérationnel.</div>`;
    }
    $("cnxWizard").innerHTML =
      `<h4>Étape ${wizardStep + 1}/9 — ${esc(title)}</h4>${body}
       <div class="cnx-wizacts">
         ${wizardStep > 0 ? '<button class="btn ghost" id="wzPrev">← Retour</button>' : ""}
         ${wizardStep < 8 ? '<button class="btn" id="wzNext">Suivant →</button>'
                          : '<button class="btn" id="wzDone">Créer le connecteur</button>'}
         <button class="btn ghost" id="wzCancel">Annuler</button>
       </div>`;
    $("wzPrev")?.addEventListener("click", () => { wizardStep--; renderWizard(); });
    $("wzCancel")?.addEventListener("click", () => show("overview"));
    $("wzNext")?.addEventListener("click", async () => {
      if (wizardStep === 0) {
        wizard.connector_id = $("wzAdapter").value;
        wizard.name = $("wzName").value || $("wzAdapter").value;
        wizard.note = $("wzNote").value || "";
      }
      if (wizardStep === 1) { wizard.mode = $("wzMode").value; wizard.env = $("wzEnv").value; }
      if (wizardStep === 2) wizard.secret_name = $("wzSecretName").value || "";
      // étapes à action : on lance l'action PUIS on avance (sinon le bouton
      // « Suivant » ne faisait pas avancer et l'assistant restait bloqué)
      if (wizardStep === 3) await runWizardTest();
      if (wizardStep === 6) await runWizardPreview();
      wizardStep++; renderWizard();
    });
    $("wzDone")?.addEventListener("click", createFromWizard);
    if (k === "schema") loadWizardForms();
    if (k === "mapping") loadWizardMapping();
  }

  async function runWizardTest() {
    const box = $("wzTestOut");
    if (!wizard.connector_id) {
      box.innerHTML = `<span class="cnx-errbox" style="display:block">
        Revenez à l'étape 1 pour choisir un adaptateur.</span>`;
      return;
    }
    box.textContent = "Test en cours…";
    try {
      const r = await api("/api/connectors/" + encodeURIComponent(wizard.connector_id) + "/test",
                          { method: "POST", body: "{}" });
      wizard.tested = r.ok;
      box.innerHTML = `<span class="${r.ok ? "cnx-okbox" : "cnx-errbox"}" style="display:block">
        ${esc(r.detail || "")} · état obtenu : ${esc(r.state)}</span>`;
    } catch (e) { box.innerHTML = `<span class="cnx-errbox" style="display:block">${esc(e.message)}</span>`; }
  }

  async function loadWizardForms() {
    let rows = [];
    try { rows = (await api("/api/connectors/" +
      encodeURIComponent(wizard.connector_id || "demo_simulated") + "/forms")).forms || []; }
    catch { rows = []; }
    $("wzForms").innerHTML = rows.length
      ? rows.map(f => `<div class="cnx-card">
          <h4>${esc(f.label || f.form_id)} ${badge(f.source || "declared", "info")}</h4>
          <div class="mono">${(f.fields || []).length} champ(s)</div></div>`).join("")
      : empty("Aucun schéma exposé par cet adaptateur.");
  }

  async function loadWizardMapping() {
    let rows = [];
    try { rows = (await api("/api/connectors/forms")).forms || []; } catch { rows = []; }
    $("wzMap").innerHTML = rows.length
      ? `<div class="cnx-table"><table><thead><tr><th>Formulaire</th><th>Champs</th>
           <th>Version</th><th>État</th></tr></thead><tbody>` +
        rows.map(f => `<tr><td>${esc(f.name || f.form_id)}</td><td>${f.fields}</td>
          <td class="mono">v${f.version}</td>
          <td>${f.active ? badge("actif", "ok") : badge("désactivé", "off")}</td></tr>`).join("") +
        "</tbody></table></div>"
      : empty("Aucun modèle de formulaire. Créez-en un dans « Modèles de formulaires ».");
  }

  async function runWizardPreview() {
    const job = $("wzJob").value.trim(), form = $("wzForm").value.trim();
    const box = $("wzPreview");
    if (!job || !form) { box.innerHTML = `<span class="cnx-errbox" style="display:block">
      Renseignez un document traité et un formulaire cible.</span>`; return; }
    box.innerHTML = `<div class="cnx-empty">Préremplissage en cours…</div>`;
    try {
      const r = await api("/api/connectors/preview", { method: "POST", body: JSON.stringify({
        job_id: job, form_id: form, rules: [], risk: "medium" }) });
      const v = r.validation || {};
      box.innerHTML = `<div class="${v.can_transmit ? "cnx-okbox" : "cnx-warnbox"}" style="display:block">
          ${v.can_transmit ? "Aucun blocage." : "Transmission bloquée."} ${esc(v.reason || "")}</div>
        <div class="cnx-table" style="margin-top:10px"><table><thead><tr>
          <th>Champ cible</th><th>Valeur</th><th>Origine</th></tr></thead><tbody>` +
        Object.values(r.values || {}).map(val =>
          `<tr><td>${esc(val.target_field)}</td><td class="mono">${esc(val.value ?? "—")}</td>
           <td>${esc(val.source_field || "—")}${val.transform && val.transform !== "none"
             ? " · " + esc(val.transform) : ""}${val.warning ? " · ⚠ " + esc(val.warning) : ""}</td>
           </tr>`).join("") + "</tbody></table></div>";
    } catch (e) { box.innerHTML = `<span class="cnx-errbox" style="display:block">${esc(e.message)}</span>`; }
  }

  async function createFromWizard() {
    if (!wizard.connector_id) {
      alert("Revenez à l'étape 1 pour choisir un adaptateur.");
      return;
    }
    try {
      await api("/api/connectors/" + encodeURIComponent(wizard.connector_id), {
        method: "POST", body: JSON.stringify({
          settings: { mode: wizard.mode || "simulated", env: wizard.env || "test" },
          note: wizard.note || "" }) });
      if (wizard.secret_name) {
        const val = prompt(`Valeur du secret « ${wizard.secret_name} » (chiffrée localement) :`);
        if (val) await api("/api/connectors/" + encodeURIComponent(wizard.connector_id) +
          "/secrets", { method: "PUT", body: JSON.stringify(
            { key: wizard.secret_name, value: val }) });
      }
      wizardStep = 0; wizard = {};
      show("active"); loadOverview();
    } catch (e) { alert("Création impossible : " + e.message); }
  }

  /* ─────────────── 05 · configuration ─────────────── */
  let cfgTarget = "";
  async function loadConfig() {
    let rows = [];
    try { rows = await api("/api/connectors/configured"); } catch { rows = []; }
    if (!cfgTarget && rows.length) cfgTarget = rows[0].connector_id;
    const cur = rows.find(c => c.connector_id === cfgTarget);
    $("cnxConfig").innerHTML = rows.length ? `
      <div class="cnx-form">
        <label>Connecteur
          <select id="cfSel">${rows.map(c =>
            `<option value="${esc(c.connector_id)}"${c.connector_id === cfgTarget ? " selected" : ""}>` +
            `${esc(c.name || c.connector_id)} — ${esc(c.state)}</option>`).join("")}</select></label>
        <div class="cnx-kv">
          <dt>État</dt><dd>${stateBadge(cur?.state || "unconfigured")}</dd>
          <dt>Dernier test</dt><dd>${cur?.last_test ? esc(cur.last_test.detail || "—") : "jamais testé"}</dd>
          <dt>Environnement</dt><dd class="mono">${esc(cur?.settings?.env || "—")}</dd>
          <dt>Mode</dt><dd class="mono">${esc(cur?.settings?.mode || "—")}</dd>
        </div>
        <label>Note d'usage<textarea id="cfNote" rows="2">${esc(cur?.note || "")}</textarea></label>
        <div class="cnx-wizacts">
          <button class="btn" id="cfSave">Enregistrer</button>
          <button class="btn ghost" id="cfTest">Tester maintenant</button>
          <button class="btn ghost" id="cfDelete">Supprimer</button>
        </div>
        <div class="mono" id="cfOut"></div>
      </div>` : empty("Aucun connecteur configuré.");
    if (!rows.length) return;
    $("cfSel")?.addEventListener("change", e => { cfgTarget = e.target.value; loadConfig(); });
    $("cfSave")?.addEventListener("click", async () => {
      await api("/api/connectors/" + encodeURIComponent(cfgTarget), { method: "POST",
        body: JSON.stringify({ note: $("cfNote").value }) });
      $("cfOut").innerHTML = `<span class="cnx-okbox" style="display:block">Enregistré.</span>`;
      loadActive();
    });
    $("cfTest")?.addEventListener("click", async () => {
      const r = await api(`/api/connectors/${encodeURIComponent(cfgTarget)}/test`,
        { method: "POST", body: "{}" });
      $("cfOut").innerHTML = `<span class="${r.ok ? "cnx-okbox" : "cnx-errbox"}" style="display:block">
        ${esc(r.detail || "")} · état : ${esc(r.state)}</span>`;
      loadConfig(); loadActive();
    });
    $("cfDelete")?.addEventListener("click", async () => {
      if (!confirm("Supprimer ce connecteur et ses secrets ?")) return;
      await api("/api/connectors/" + encodeURIComponent(cfgTarget), { method: "DELETE" });
      cfgTarget = ""; loadConfig(); loadActive();
    });
  }

  /* ─────────────── 06 · correspondance ─────────────── */
  async function loadMapping() {
    let forms = [], jobs = [];
    try {
      const fr = await api("/api/connectors/forms");
      forms = Array.isArray(fr) ? fr : (fr.forms || []);
      const jr = await api("/api/jobs?limit=25");
      jobs = Array.isArray(jr) ? jr : (jr.jobs || jr.items || []);
    } catch { /* hors ligne : on affiche l'explicatif */ }
    $("cnxMapping").innerHTML = `
      <div class="cnx-form">
        <label>Document traité
          <select id="mpJob">${jobs.length ? jobs.map(j =>
            `<option value="${esc(j.job_id)}">${esc(j.filename || j.job_id)}</option>`).join("")
            : '<option value="">— aucun document traité —</option>'}</select></label>
        <label>Formulaire cible
          <select id="mpForm">${forms.length ? forms.map(f =>
            `<option value="${esc(f.form_id)}">${esc(f.name || f.form_id)}</option>`).join("")
            : '<option value="">— aucun modèle —</option>'}</select></label>
        <label>Niveau de risque
          <select id="mpRisk"><option value="low">Faible</option>
            <option value="medium" selected>Moyen</option><option value="high">Élevé</option></select></label>
        <div class="cnx-wizacts">
          <button class="btn" id="mpRun">Préremplir et valider</button>
        </div>
      </div>
      <div id="mpOut" style="margin-top:14px">${empty(
        "Choisissez un document et un formulaire, puis lancez le préremplissage. " +
        "Aucune donnée n'est envoyée à cette étape.")}</div>`;
    $("mpRun")?.addEventListener("click", async () => {
      const out = $("mpOut");
      out.innerHTML = `<div class="cnx-empty">Analyse…</div>`;
      try {
        const r = await api("/api/connectors/preview", { method: "POST", body: JSON.stringify({
          job_id: $("mpJob").value, form_id: $("mpForm").value, rules: [],
          risk: $("mpRisk").value }) });
        const v = r.validation || {};
        out.innerHTML =
          `<div class="${v.can_transmit ? "cnx-okbox" : "cnx-warnbox"}" style="display:block">
             ${v.can_transmit ? "Prêt à transmettre." : "Transmission bloquée."}
             ${esc(v.reason || "")}</div>` +
          `<div class="cnx-table" style="margin-top:12px"><table><thead><tr>
             <th>Champ cible</th><th>Valeur</th><th>Type</th><th>Obligatoire</th>
             <th>Statut</th><th>Provenance</th></tr></thead><tbody>` +
          (r.form.fields || []).map(f => {
            const val = (r.values || {})[f.external_name];
            const st = val?.value ? badge("renseigné", "ok")
                     : f.required ? badge("manquant", "err") : badge("vide", "off");
            return `<tr><td>${esc(f.label || f.external_name)}</td>
              <td class="mono">${esc(val?.value ?? "—")}</td>
              <td class="mono">${esc(f.field_type)}</td>
              <td>${f.required ? "oui" : "non"}</td><td>${st}</td>
              <td class="mono">${esc(val?.source_field || "—")}${
                val?.warning ? " · ⚠ " + esc(val.warning) : ""}</td></tr>`;
          }).join("") + "</tbody></table></div>" +
          ((r.suggestions || []).length
            ? `<div class="cnx-note" style="margin-top:12px"><strong>Suggestions non appliquées</strong>
               (à valider manuellement) : ` +
              r.suggestions.map(s => esc(s.target_field) + " ← " + esc(s.source_field)).join(", ") +
              `</div>`
            : "");
      } catch (e) { out.innerHTML = `<span class="cnx-errbox" style="display:block">${esc(e.message)}</span>`; }
    });
  }

  /* ─────────────── 07 · modèles de formulaires ─────────────── */
  async function loadForms() {
    let rows = [], tpl = [];
    try {
      rows = (await api("/api/connectors/forms")).forms || [];
      tpl = await api("/api/connectors/forms/templates");
    } catch { rows = []; tpl = []; }
    $("cnxForms").innerHTML = `
      <div class="cnx-wizacts" style="margin-bottom:14px">
        ${tpl.map(t => `<button class="btn ghost" data-tpl="${esc(t.form_id)}">
          + ${esc(t.name)} (${t.fields} champs)</button>`).join("")}
        <button class="btn ghost" id="fmReload">Rafraîchir</button>
      </div>
      <div class="cnx-table"><table><thead><tr><th>Formulaire</th><th>Champs</th>
        <th>Obligatoires</th><th>Version</th><th>État</th><th></th></tr></thead><tbody>` +
        (rows.length ? rows.map(f => `<tr>
          <td>${esc(f.name || f.form_id)}</td><td>${f.fields}</td>
          <td>${f.required ?? "—"}</td><td class="mono">v${f.version}</td>
          <td>${f.active ? badge("actif", "ok") : badge("désactivé", "off")}</td>
          <td>${f.active ? `<button class="btn ghost" data-dis="${esc(f.form_id)}">Désactiver</button>` : ""}</td>
        </tr>`).join("") : `<tr><td colspan="6" class="muted">Aucun modèle. Les trames ci-dessus sont des propositions à adapter.</td></tr>`) +
      "</tbody></table></div>" +
      `<div class="cnx-note" style="margin-top:14px">Les trames « Déclaration en douane »
        et « Escale portuaire » sont des <strong>bases de travail</strong>, pas des
        formats officiels : à conformer à la spécification fournie par l'organisme.</div>`;
    $("fmReload")?.addEventListener("click", loadForms);
    $("cnxForms").querySelectorAll("[data-tpl]").forEach(b =>
      b.addEventListener("click", async () => {
        try {
          await api(`/api/connectors/forms/${encodeURIComponent(b.dataset.tpl)}/from-template`,
            { method: "POST", body: "{}" });
        } catch (e) { alert(e.message); }
        loadForms();
      }));
    $("cnxForms").querySelectorAll("[data-dis]").forEach(b =>
      b.addEventListener("click", async () => {
        await api(`/api/connectors/forms/${encodeURIComponent(b.dataset.dis)}/disable`,
          { method: "POST", body: "{}" });
        loadForms();
      }));
  }

  /* ─────────────── 08 · flux d'intégration ─────────────── */
  function loadModes() {
    $("cnxModes").innerHTML = [
      ["A", "API officielle", "info",
       "Dialogue direct avec l'API de l'organisme. Nécessite un accès autorisé, " +
       "documenté, et une clé d'idempotence si l'API la prend en charge. " +
       "Aucun adaptateur de ce type n'est livré ici."],
      ["B", "Préremplissage web autorisé", "warn",
       "Ouvre un formulaire prérempli sur un site qui l'autorise. Aucun " +
       "contournement de CAPTCHA ni de protection anti-automatisation."],
      ["C", "Export structuré assisté", "ok",
       "Produit un CSV anti-injection, un tableau de correspondance et un JSON " +
       "de traçabilité, à importer manuellement. Livré et testé."],
      ["D", "Simulation locale", "off",
       "Simulateur hors ligne pour répéter le parcours complet sans toucher à " +
       "un système réel. Ce n'est pas une intégration réelle."],
    ].map(([tag, title, kind, txt]) => `<div class="cnx-mode">
        <h4>${esc(title)} <span class="tag">${tag}</span></h4>
        <p>${esc(txt)}</p>${badge(tag === "C" ? "disponible" : tag === "D" ? "démonstration" : "à configurer", kind)}
      </div>`).join("");
  }

  /* ─────────────── 09 · historique ─────────────── */
  async function loadHistory() {
    let d = { stats: {}, transmissions: [] };
    try { d = await api("/api/connectors/transmissions?limit=100"); } catch { /* hors ligne */ }
    const TX = { accepted: ["Acceptée", "ok"], pending_confirmation: ["Issue à confirmer", "warn"],
      rejected: ["Rejet métier", "err"], failed: ["Échec technique", "err"],
      sending: ["Envoi…", "info"], cancelled: ["Annulée", "off"], created: ["Créée", "info"] };
    $("cnxHistory").innerHTML = `
      <div class="cnx-grid" style="margin-bottom:14px">
        ${Object.entries(d.stats || {})
          .filter(([k]) => k !== "max_auto_retries")
          .map(([k, v]) => `<div class="cnx-card"><h4>${esc(TX_LABEL[k] || k)}</h4>
            <div class="mono" style="font-size:22px;color:var(--accent)">${
              typeof v === "object" && v !== null
                ? Object.entries(v).map(([sk, sv]) =>
                    `${esc(TX_LABEL[sk] || sk)} : <b>${esc(String(sv))}</b>`).join("<br>")
                : esc(String(v))}</div></div>`).join("")}
      </div>
      <div class="cnx-table"><table><thead><tr><th>Référence</th><th>Connecteur</th>
        <th>Statut</th><th>Tentatives</th><th>Créée</th><th>Erreurs</th></tr></thead><tbody>` +
      ((d.transmissions || []).length ? (d.transmissions).map(t =>
        `<tr><td class="mono">${esc(t.reference || t.transmission_id)}</td>
         <td class="mono">${esc(t.connector_id)}</td>
         <td>${badge(...(TX[t.status] ? TX[t.status] : [t.status, "off"]))}</td>
         <td>${t.attempts ?? 0}</td>
         <td>${t.created_at ? new Date(t.created_at * 1000).toLocaleString("fr-FR") : "—"}</td>
         <td class="mono">${esc((t.errors || []).join(" ; ").slice(0, 90) || "—")}</td></tr>`).join("")
        : `<tr><td colspan="6" class="muted">Aucune transmission enregistrée.</td></tr>`) +
      "</tbody></table></div>";
  }

  /* ─────────────── 10 · erreurs et reprises ─────────────── */
  async function loadErrors() {
    let rows = [];
    try { rows = (await api("/api/connectors/transmissions?limit=100")).transmissions || []; }
    catch { rows = []; }
    const open = rows.filter(t => ["pending_confirmation", "failed", "rejected"].includes(t.status));
    $("cnxErrors").innerHTML = `
      <div class="cnx-warnbox" style="margin-bottom:14px">
        Avant de reprendre une transmission à l'issue inconnue, lancez un
        <strong>rapprochement</strong> : il vérifie si le système cible a déjà
        accepté la demande. Un rejet métier n'est jamais rejoué automatiquement.
      </div>
      <div class="cnx-table"><table><thead><tr><th>Référence</th><th>Statut</th>
        <th>Erreurs</th><th>Actions</th></tr></thead><tbody>` +
      (open.length ? open.map(t => `<tr>
        <td class="mono">${esc(t.reference || t.transmission_id)}</td>
        <td>${badge(t.status === "pending_confirmation" ? "Issue à confirmer"
          : t.status === "rejected" ? "Rejet métier" : "Échec technique",
          t.status === "rejected" ? "err" : "warn")}</td>
        <td class="mono">${esc((t.errors || []).join(" ; ").slice(0, 110) || "—")}</td>
        <td><div class="cnx-wizacts">
          <button class="btn ghost" data-rec="${esc(t.transmission_id)}">Rapprocher</button>
          <button class="btn ghost" data-ret="${esc(t.transmission_id)}">Reprendre</button>
          <button class="btn ghost" data-can="${esc(t.transmission_id)}">Annuler</button>
        </div></td></tr>`).join("")
        : `<tr><td colspan="4" class="muted">Aucune transmission en attente de décision.</td></tr>`) +
      '</tbody></table></div><div class="mono" id="erOut" style="margin-top:12px"></div>';
    const out = $("erOut");
    $("cnxErrors").querySelectorAll("[data-rec]").forEach(b =>
      b.addEventListener("click", async () => {
        try {
          const r = await api(`/api/connectors/transmissions/${encodeURIComponent(b.dataset.rec)}/reconcile`,
            { method: "POST", body: "{}" });
          out.innerHTML = `<span class="cnx-okbox" style="display:block">
            Rapprochement : ${esc(r.status)}${r.reference ? " · " + esc(r.reference) : ""}</span>`;
        } catch (e) { out.innerHTML = `<span class="cnx-errbox" style="display:block">${esc(e.message)}</span>`; }
        loadErrors(); loadHistory();
      }));
    $("cnxErrors").querySelectorAll("[data-ret]").forEach(b =>
      b.addEventListener("click", async () => {
        try {
          const r = await api(`/api/connectors/transmissions/${encodeURIComponent(b.dataset.ret)}/retry`,
            { method: "POST", body: JSON.stringify({ auto: false }) });
          out.innerHTML = `<span class="cnx-okbox" style="display:block">
            Reprise manuelle : ${esc(r.status)}</span>`;
        } catch (e) { out.innerHTML = `<span class="cnx-errbox" style="display:block">${esc(e.message)}</span>`; }
        loadErrors(); loadHistory();
      }));
    $("cnxErrors").querySelectorAll("[data-can]").forEach(b =>
      b.addEventListener("click", async () => {
        await api(`/api/connectors/transmissions/${encodeURIComponent(b.dataset.can)}/cancel`,
          { method: "POST", body: "{}" });
        loadErrors(); loadHistory();
      }));
  }

  /* ─────────────── 11 · sécurité ─────────────── */
  let secTarget = "";
  async function loadSecurity() {
    let status = {}, rows = [];
    try {
      status = await api("/api/connectors/secrets/status");
      rows = await api("/api/connectors/configured");
    } catch { /* hors ligne */ }
    if (!secTarget && rows.length) secTarget = rows[0].connector_id;
    const cur = rows.find(c => c.connector_id === secTarget);
    let keys = [];
    if (secTarget) { try { keys = (await api(
      `/api/connectors/${encodeURIComponent(secTarget)}/secrets`)).keys || []; } catch { keys = []; } }
    $("cnxSecurity").innerHTML = `
      <div class="cnx-cards" style="margin-bottom:16px">
        <div class="cnx-card"><h4>Coffre de secrets</h4>
          <div class="cnx-kv">
            <dt>Chiffrement</dt><dd>${status.encrypted ? badge("actif", "ok") : badge("inactif", "off")}</dd>
            <dt>Algorithme</dt><dd class="mono">${esc(status.algorithm || "—")}</dd>
            <dt>Dérivation</dt><dd class="mono">${esc(status.kdf || "—")}</dd>
            <dt>Clé</dt><dd class="mono">${esc(status.key_length_bits ? status.key_length_bits + " bits" : "—")}</dd>
          </div></div>
        <div class="cnx-card"><h4>Règles appliquées</h4>
          <div class="cnx-check"><input type="checkbox" checked disabled>
            <span>Aucun secret en clair dans le code, les journaux ou les réponses HTTP.</span></div>
          <div class="cnx-check"><input type="checkbox" checked disabled>
            <span>Permissions minimales, séparation test / production.</span></div>
          <div class="cnx-check"><input type="checkbox" checked disabled>
            <span>Aucun contournement de CAPTCHA ni de protection anti-automatisation.</span></div>
          <div class="cnx-check"><input type="checkbox" checked disabled>
            <span>Confirmation humaine explicite avant tout envoi à conséquences.</span></div>
        </div>
      </div>
      ${rows.length ? `<div class="cnx-form">
        <label>Connecteur<select id="scSel">${rows.map(c =>
          `<option value="${esc(c.connector_id)}"${c.connector_id === secTarget ? " selected" : ""}>` +
          `${esc(c.name || c.connector_id)}</option>`).join("")}</select></label>
        <label>Nom du nouveau secret<input id="scKey" placeholder="ex. api_key"></label>
        <label>Valeur<input id="scVal" type="password" placeholder="jamais affichée ensuite"></label>
        <div class="cnx-wizacts">
          <button class="btn" id="scSave">Enregistrer le secret</button>
        </div>
        <div class="cnx-table" style="margin-top:8px"><table><thead><tr>
          <th>Secrets définis (noms seulement)</th><th></th></tr></thead><tbody>` +
          (keys.length ? keys.map(k => `<tr><td class="mono">${esc(k)}</td>
            <td><button class="btn ghost" data-del="${esc(k)}">Supprimer</button></td></tr>`).join("")
            : `<tr><td class="muted" colspan="2">Aucun secret pour ce connecteur.</td></tr>`) +
        `</tbody></table></div>
        <div class="mono" id="scOut"></div>
      </div>` : empty("Aucun connecteur configuré.")}`;
    $("scSel")?.addEventListener("change", e => { secTarget = e.target.value; loadSecurity(); });
    $("scSave")?.addEventListener("click", async () => {
      const k = $("scKey").value.trim(), v = $("scVal").value;
      if (!k || !v) { $("scOut").innerHTML =
        `<span class="cnx-errbox" style="display:block">Nom et valeur requis.</span>`; return; }
      try {
        await api(`/api/connectors/${encodeURIComponent(secTarget)}/secrets`,
          { method: "PUT", body: JSON.stringify({ key: k, value: v }) });
        $("scVal").value = "";
        $("scOut").innerHTML = `<span class="cnx-okbox" style="display:block">
          Secret « ${esc(k)} » chiffré et enregistré.</span>`;
        loadSecurity();
      } catch (e) { $("scOut").innerHTML =
        `<span class="cnx-errbox" style="display:block">${esc(e.message)}</span>`; }
    });
    $("cnxSecurity").querySelectorAll("[data-del]").forEach(b =>
      b.addEventListener("click", async () => {
        await api(`/api/connectors/${encodeURIComponent(secTarget)}/secrets/${encodeURIComponent(b.dataset.del)}`,
          { method: "DELETE" });
        loadSecurity();
      }));
  }

  /* ─────────────── 12 · journaux d'audit ─────────────── */
  async function loadAudit() {
    let rows = [];
    try { rows = (await api("/api/audit?limit=200")).entries || []; } catch { rows = []; }
    // seules les actions du hub : le reste appartient aux autres rubriques
    const list = rows.filter(a =>
      /^(connector|transmission|secret)/.test(a.event || ""));
    $("cnxAudit").innerHTML = list.length
      ? `<div class="cnx-note">Journal en ajout seul : aucune ligne n'est
           modifiée ni reformatée. ${list.length} action(s) du hub affichée(s).</div>
         <div class="cnx-table"><table><thead><tr><th>Horodatage</th><th>Événement</th>
           <th>Détail</th></tr></thead><tbody>` +
          list.map(a => `<tr>
            <td class="mono">${a.ts ? new Date(a.ts * 1000).toLocaleString("fr-FR") : "—"}</td>
            <td class="mono">${esc(a.event || "—")}</td>
            <td>${esc(JSON.stringify(
              Object.fromEntries(Object.entries(a).filter(([k]) => !["ts", "event"].includes(k)))
            ).slice(0, 170))}</td></tr>`).join("") +
        "</tbody></table></div>"
      : empty("Aucune action du hub encore enregistrée dans le journal d'audit.");
  }

  function loadAll() { renderSubnav(); loadModes(); show(section); }

  return { loadAll, show, get section() { return section; } };
})();
