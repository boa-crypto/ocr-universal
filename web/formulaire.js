/* ═══ Form builder du dossier — module d'interface (source unique) ═══
   Chargé directement par web/index.html (<script src="formulaire.js" defer>).

   Étape 12 du parcours. Ce module décrit la structure interne d'un dossier :
   quels champs, d'où vient chaque valeur, ce qui reste à remplir.

   Ce qu'il n'est PAS : un formulaire administratif, une soumission, un
   endpoint vers un système externe. Aucun champ n'est inventé — chacun vient
   d'une valeur extraite ou d'un ajout humain explicite, et son origine est
   affichée à côté de lui.

   Aucune ressource externe.                                                        */

const FormulaireUI = (function () {
  "use strict";

  let formulaireActif = null;
  let occupation = false;

  function el(id) { return document.getElementById(id); }

  function origineBadge(origine) {
    const libelles = {
      extrait: "extrait",
      ajoute: "ajout humain",
      calcule: "calculé",
    };
    const cls = { extrait: "info", ajoute: "ok", calcule: "warning" }[origine] || "info";
    return '<span class="badge ' + cls + '">' +
      esc(libelles[origine] || origine) + "</span>";
  }

  function typeBadge(type) { return '<span class="pill">' + esc(type) + "</span>"; }

  /* ─────────────────────────── chargement ─────────────────────────── */

  async function charge(dossierId) {
    const box = el("dossierForm");
    if (!box) return;
    if (!dossierId) {
      box.innerHTML = '<div class="card-sub">Ouvrez d\'abord un dossier.</div>';
      return;
    }
    box.innerHTML = '<div class="card-sub">Construction du formulaire…</div>';
    try {
      const f = await api("/api/dossiers/" + encodeURIComponent(dossierId) + "/formulaire");
      formulaireActif = f;
      dessine(f);
    } catch (e) {
      box.innerHTML = '<div class="card-sub">Erreur : ' + esc(e.message) + "</div>";
    }
  }

  function dessine(f) {
    const box = el("dossierForm");
    if (!box) return;
    const r = f.remplissage || {};

    let html = '<div class="page-head"><div>' +
      '<div class="ph-kicker">Formulaire</div>' +
      '<h3 class="ph-title">' + esc(f.label || "Formulaire du dossier") + "</h3>" +
      '<p class="ph-sub">' + esc(f.description || "") + "</p>" +
      "</div>" +
      '<div class="ph-actions">' +
      '<span class="pill">v' + esc(f.version || "?") + "</span>" +
      '<span class="pill">' + (r.total || 0) + " champ(s)</span>" +
      (r.complet
        ? '<span class="badge ok">complet</span>'
        : '<span class="badge warning">' + (r.requis_manquants || []).length +
          " requis manquant(s)</span>") +
      '<button class="btn ghost sm" id="frmRafraichir">↻ Reconstruire</button>' +
      "</div></div>";

    /* rappel de ce qu'est ce formulaire — et de ce qu'il n'est pas */
    html += '<div class="card-sub" style="margin-bottom:10px">' +
      "Chaque champ indique d'où vient sa valeur. Rien n'est envoyé à un " +
      "organisme : ce formulaire décrit la structure du dossier, il ne la " +
      "transmet pas.</div>";

    if (!(f.champs || []).length) {
      html += '<div class="card"><div class="card-sub">' +
        "Aucun champ : aucun document de ce dossier n'a fourni de valeur " +
        "extractible. Un formulaire vide est affiché comme tel, jamais " +
        "rempli de champs inventés.</div></div>";
      box.innerHTML = html;
      el("frmRafraichir").addEventListener("click",
        () => charge(f.dossier_id));
      return;
    }

    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Champs</div>' +
      '<div class="card-sub">' + (r.remplis || 0) + " rempli(s), " +
      (r.valides || 0) + " validé(s) par un humain</div></div>";

    html += '<table class="tbl"><thead><tr><th>Champ</th><th>Clé</th>' +
      "<th>Valeur</th><th>Origine</th><th>État</th><th></th></tr></thead><tbody>";
    (f.champs || []).forEach(c => {
      const vide = c.valeur === null || c.valeur === undefined || c.valeur === "";
      html += "<tr>" +
        "<td>" + esc(c.label || c.key) +
        (c.required ? ' <span class="badge warning">requis</span>' : "") + "</td>" +
        '<td class="mono dim">' + esc(c.key) + "</td>" +
        '<td class="mono">' + (vide ? "—" : esc(String(c.valeur))) + "</td>" +
        "<td>" + origineBadge(c.origine) + " " + typeBadge(c.type) + "</td>" +
        "<td>" + (c.valide
          ? '<span class="badge ok">validé</span>'
          : (vide ? '<span class="badge info">vide</span>'
                  : '<span class="badge warning">à trancher</span>')) + "</td>" +
        '<td><button class="btn ghost sm" data-suppr="' + esc(c.key) +
        '" title="Retirer du formulaire (le document nest pas modifié)">✕</button></td>' +
        "</tr>";
    });
    html += "</tbody></table>";

    if (r.requis_manquants && r.requis_manquants.length) {
      html += '<div class="card-sub" style="margin-top:8px">Champs requis ' +
        "manquants : " + esc(r.requis_manquants.join(", ")) + "</div>";
    }
    html += "</div>";

    /* ajout humain explicite */
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Ajouter un champ</div>' +
      '<div class="card-sub">Un ajout est tracé comme tel, jamais présenté ' +
      "comme une valeur extraite</div></div>" +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end">' +
      '<label class="ph-field" for="frmNewKey">Clé</label>' +
      '<input class="inp" id="frmNewKey" placeholder="reference_dossier" ' +
      'style="width:180px">' +
      '<label class="ph-field" for="frmNewLabel">Libellé</label>' +
      '<input class="inp" id="frmNewLabel" placeholder="Référence dossier" ' +
      'style="flex:1;min-width:180px">' +
      '<label class="ph-check" for="frmNewReq"><input type="checkbox" id="frmNewReq">' +
      "<span>requis</span></label>" +
      '<button class="btn" id="frmAjouter">+ Ajouter</button>' +
      "</div></div>";

    box.innerHTML = html;

    el("frmRafraichir").addEventListener("click", () => charge(f.dossier_id));
    el("frmAjouter").addEventListener("click", () => ajoute(f));
    box.querySelectorAll("[data-suppr]").forEach(b => {
      b.addEventListener("click", () => retire(f, b.getAttribute("data-suppr")));
    });
  }

  /* ─────────────────────────── actions ─────────────────────────── */

  async function ajoute(f) {
    const key = (el("frmNewKey").value || "").trim();
    const label = (el("frmNewLabel").value || "").trim();
    if (!key) { toast("La clé du champ est obligatoire.", "error"); return; }
    if (occupation) return;
    occupation = true;
    try {
      const maj = await api("/api/formulaires/" + encodeURIComponent(f.formulaire_id) +
        "/champs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            key: key, label: label, type: "text",
            required: !!el("frmNewReq").checked,
          }),
        });
      el("frmNewKey").value = "";
      el("frmNewLabel").value = "";
      formulaireActif = maj;
      dessine(maj);
      toast("Champ ajouté, origine « ajout humain ».", "success");
    } catch (e) {
      toast("Ajout refusé : " + e.message, "error");
    } finally {
      occupation = false;
    }
  }

  async function retire(f, key) {
    try {
      const maj = await api("/api/formulaires/" + encodeURIComponent(f.formulaire_id) +
        "/champs/" + encodeURIComponent(key), { method: "DELETE" });
      formulaireActif = maj;
      dessine(maj);
      toast("Champ retiré du formulaire. Le document nest pas modifié.", "info");
    } catch (e) {
      toast("Retrait refusé : " + e.message, "error");
    }
  }

  return {
    charge: charge,
    dessine: dessine,
    ajoute: ajoute,
    retire: retire,
    get actif() { return formulaireActif; },
  };
})();
