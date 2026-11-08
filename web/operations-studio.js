/* Contextual assistance and native form guidance. No business requests or persistence. */
(function () {
  "use strict";
  function init() {
    if (document.querySelector(".studio-guide")) return;
    function family() {
      document.documentElement.dataset.studioFamily = (
        location.hash || "#cockpit"
      )
        .slice(1)
        .split("/")[0];
    }
    family();
    function node(tag, cls, text) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text !== undefined) n.textContent = text;
      return n;
    }
    var advice = {
      cockpit: [
        "Choisissez votre prochaine opération",
        "Importez une pièce, relisez l’extraction ou ouvrez un dossier. Les compteurs proviennent de l’API ; un tiret signifie une information non disponible.",
      ],
      workspace: [
        "Travaillez à partir de votre file",
        "Combinez recherche, priorité et statut, puis ouvrez le dossier. Les filtres portent sur les dossiers chargés par l’espace de travail.",
      ],
      dossiers: [
        "Du portefeuille à la pièce source",
        "La liste et le pilotage par état partagent la même recherche et les mêmes filtres. Sélectionnez un dossier pour explorer ses pièces, ses extractions, ses anomalies et sa chronologie. Les colonnes ne modifient aucun statut.",
      ],
      documents: [
        "Une extraction n’est pas une validation",
        "Conservez la pièce source comme référence. Comparez les champs extraits avec le document avant toute validation ou transmission.",
      ],
      controle: [
        "Examinez les écarts, pas seulement les scores",
        "Consultez les pièces manquantes et anomalies. L’absence de donnée ou un échec réseau n’établit jamais la conformité.",
      ],
      douane: [
        "Une décision doit rester traçable",
        "Distinguez donnée extraite, contrôle documentaire et décision réglementaire. Les sources en quarantaine restent non validées et non publiées.",
      ],
      finance: [
        "Reliez chaque montant à son dossier",
        "Consultez les frais et justificatifs avant d’agir. Un montant absent n’est pas un montant nul ; conservez la devise et la provenance.",
      ],
      maritime: [
        "Suivez le transport depuis le dossier",
        "Rapprochez navire, connaissement et conteneurs. Les informations non renseignées ne constituent pas des prévisions d’arrivée.",
      ],
      enlevissement: [
        "Préparez la suite de l’opération",
        "Vérifiez le dossier et les informations de transport avant d’organiser l’enlèvement. Aucun mouvement physique n’est déduit d’un simple affichage.",
      ],
      reports: [
        "Lisez le périmètre avant le résultat",
        "Vérifiez les filtres, la période et les données disponibles. Une visualisation ne remplace pas les pièces justificatives.",
      ],
      referentiels: [
        "Le contexte donne son sens à la donnée",
        "Consultez les valeurs et leur provenance avant toute modification. Ne confondez pas référentiel de travail et publication officielle.",
      ],
      admin: [
        "Paramétrer sans compromettre les preuves",
        "Consultez les droits, contrôles et journaux associés. Une modification d’administration doit respecter les habilitations et les procédures existantes.",
      ],
    };
    var dialog = node("dialog", "studio-guide");
    dialog.setAttribute("aria-labelledby", "studio-guide-title");
    var close = node("button", "studio-guide__close", "Fermer · Échap");
    close.type = "button";
    var eyebrow = node("p", "studio-eyebrow", "REPÈRES CONTEXTUELS"),
      title = node("h2", "", ""),
      intro = node("p", "studio-guide__intro", ""),
      routes = node("nav", "studio-guide__routes"),
      foot = node(
        "p",
        "studio-guide__foot",
        "Navigation : Ctrl / ⌘ J · Recherche métier : Ctrl K. Les opérations restent soumises aux droits existants.",
      );
    title.id = "studio-guide-title";
    routes.setAttribute("aria-label", "Écrans liés disponibles");
    dialog.append(close, eyebrow, title, intro, routes, foot);
    document.body.append(dialog);
    var previous;
    function paint() {
      var hash = location.hash || "#cockpit",
        family = hash.slice(1).split("/")[0];
      var links = Array.from(
        document.querySelectorAll('#mainNav a[href^="#"]'),
      );
      var current = links.find(function (a) {
        return a.hash === hash;
      });
      var context = advice[family];
      title.textContent = context
        ? context[0]
        : "Repères · " +
          ((document.getElementById("pageTitle") || {}).textContent ||
            "Poste de travail");
      intro.textContent = context
        ? context[1]
        : "Explorez les écrans disponibles de cette rubrique. Les informations affichées gardent leur provenance et leurs règles métier existantes.";
      routes.replaceChildren();
      var group = current && current.closest(".nav-group");
      var available = group
        ? Array.from(group.querySelectorAll('a[href^="#"]'))
        : links.filter(function (a) {
            return a.hash === "#cockpit";
          });
      available
        .filter(function (a) {
          return a.hash !== hash;
        })
        .forEach(function (a) {
          var link = node("a", "studio-guide__route", a.textContent.trim());
          link.href = a.hash;
          link.addEventListener("click", function () {
            dialog.close();
          });
          routes.append(link);
        });
      if (!routes.children.length)
        routes.append(
          node(
            "p",
            "",
            "Les autres destinations sont disponibles dans le menu ou la palette, selon vos droits.",
          ),
        );
    }
    document.addEventListener("click", function (event) {
      var trigger =
        event.target.closest && event.target.closest(".context-guide");
      if (!trigger) return;
      previous = trigger;
      paint();
      dialog.showModal();
      close.focus();
    });
    close.addEventListener("click", function () {
      dialog.close();
    });
    dialog.addEventListener("close", function () {
      if (previous && previous.isConnected) previous.focus();
    });
    window.addEventListener("hashchange", function () {
      family();
      if (dialog.open) dialog.close();
    });
    var nav = document.getElementById("mainNav");
    if (nav)
      new MutationObserver(function () {
        if (dialog.open) paint();
      }).observe(nav, { childList: true, subtree: true });

    var prepared = new WeakSet();
    function forms() {
      document.querySelectorAll("form").forEach(function (form) {
        if (prepared.has(form)) return;
        prepared.add(form);
        var required = Array.from(form.elements).filter(function (input) {
          return input.required && input.willValidate;
        });
        if (!required.length) return;
        var status = node("p", "studio-form-progress"),
          errors = node("div", "studio-form-errors");
        errors.hidden = true;
        errors.setAttribute("role", "alert");
        form.prepend(status);
        form.append(errors);
        function update() {
          var filled = required.filter(function (input) {
            return input.validity.valid;
          }).length;
          status.textContent =
            filled +
            " / " +
            required.length +
            " champ(s) obligatoire(s) renseigné(s). La validation métier reste distincte.";
          if (!errors.hidden) summary();
        }
        function summary() {
          errors.replaceChildren();
          var invalid = Array.from(form.elements).filter(function (input) {
            return input.willValidate && !input.validity.valid;
          });
          errors.hidden = !invalid.length;
          if (!invalid.length) return;
          errors.append(
            node("strong", "", "Vérifiez les champs avant de poursuivre"),
          );
          invalid.forEach(function (input) {
            var label = input.labels && input.labels[0];
            var link = node(
              "button",
              "studio-form-error-link",
              (label ? label.textContent.trim() : input.name || "Champ") +
                " : " +
                input.validationMessage,
            );
            link.type = "button";
            link.addEventListener("click", function () {
              input.focus();
            });
            errors.append(link);
          });
        }
        form.addEventListener("input", update);
        form.addEventListener("change", update);
        form.addEventListener("reset", function () {
          requestAnimationFrame(update);
        });
        form.addEventListener(
          "invalid",
          function () {
            requestAnimationFrame(summary);
          },
          true,
        );
        update();
      });
    }
    forms();
    var scheduled = false;
    new MutationObserver(function () {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(function () {
        scheduled = false;
        forms();
      });
    }).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
