"""Non-régression de la refonte UI premium (design system + routes d'interface).

Ces tests verrouillent trois choses :

1. la coque HTML charge le design system dans le bon ordre, sans CSS inline ;
2. les jetons de la palette imposée vivent dans un seul fichier ;
3. les routes ajoutées pour alimenter l'interface répondent avec des données
   réelles et des bornes explicites.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from unocr.api import app

RACINE = Path(__file__).parent.parent
WEB = RACINE / "web"


@pytest.fixture()
def client(tmp_cfg):
    return TestClient(app, raise_server_exceptions=False)


# ── Coque HTML ────────────────────────────────────────────────────────────

def test_design_system_charge_apres_les_feuilles_historiques() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert "/web/uniocr-ds.css" in index, "index.html doit lier le design system premium"
    assert "<style>" not in index, "aucun CSS inline ne doit revenir dans index.html"

    position_styles = index.index("/web/styles.css")
    position_refresh = index.index("/web/refresh.css")
    position_ds = index.index("/web/uniocr-ds.css")
    assert position_styles < position_refresh < position_ds, (
        "l'ordre de cascade doit rester styles.css → refresh.css → uniocr-ds.css"
    )


def test_coque_charge_les_modules_de_l_interface() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    for module in ("charts.js", "shell.js", "cockpit.js", "navigation.js"):
        assert f"/web/{module}" in index, f"{module} doit être chargé par la coque"
    # Les modules sont chargés en defer pour ne pas bloquer le rendu.
    assert '<script src="/web/shell.js" defer></script>' in index


def test_sidebar_expose_les_entrees_attendues() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    for identifiant in ("mainNav", "sidebarCollapse", "themeToggle", "dashboardBtn"):
        assert f'id="{identifiant}"' in index, f"#{identifiant} doit exister dans la barre latérale"


def test_topbar_expose_recherche_notifications_profil() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    for identifiant in ("globalSearch", "searchResults", "notifBtn", "notifMenu",
                        "helpBtn", "helpMenu", "profileBtn", "profileMenu",
                        "identChip", "enginesChip", "clockChip"):
        assert f'id="{identifiant}"' in index, f"#{identifiant} doit exister dans la barre supérieure"


def test_cockpit_expose_les_cinq_kpi_et_les_panneaux() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    for identifiant in ("kpi-actifs", "kpi-attente", "kpi-anomalies", "kpi-arrivees",
                        "kpi-livraisons", "cockpit-tasks", "cockpit-chart", "cockpit-donut",
                        "cockpit-progression", "cockpit-arrivals", "cockpit-alerts"):
        assert f'id="{identifiant}"' in index, f"#{identifiant} manque au cockpit"


def test_modules_affichent_des_indicateurs_reels() -> None:
    """Chaque page de module reçoit un bandeau de compteurs branché sur l'API."""
    index = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "modules.js").read_text(encoding="utf-8")
    assert '/web/modules.js' in index, "modules.js doit être chargé par la coque"

    sections = re.findall(r'"(tab-[a-z]+)": \{', js)
    assert len(sections) >= 7, "les principaux modules doivent exposer des indicateurs"
    for section in sections:
        assert f'id="{section}"' in index, f"la section {section} doit exister dans index.html"

    # Chaque indicateur pointe vers une route interne réelle (« #module/sous-page »).
    routes = re.findall(r'route: "#([a-z-]+)', js)
    assert routes, "chaque indicateur doit être un lien"
    for route in routes:
        assert route.split("/")[0] in index, f"la route #{route} doit correspondre à une rubrique"


def test_sous_pages_branchees_sur_des_endpoints_existants() -> None:
    """Chaque sous-page lit un endpoint réellement exposé par l'API."""
    index = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "souspages.js").read_text(encoding="utf-8")
    assert '/web/souspages.js' in index, "souspages.js doit être chargé"

    pages = re.findall(r'"(tab-[a-z-]+)": \{', js)
    assert len(pages) >= 12, "les sous-pages principales doivent être couvertes"
    for page in pages:
        assert f'id="{page}"' in index, f"la page {page} doit exister dans index.html"

    chemins = set(app.openapi()["paths"])
    urls = re.findall(r'url: "([^"]+)"', js)
    assert urls, "au moins une source doit être déclarée"
    for url in urls:
        chemin = url.split("?", 1)[0]  # les paramètres de requête ne font pas partie du contrat
        assert chemin in chemins, f"{url} doit exister dans le contrat OpenAPI"


def test_pages_historiques_toujours_accessibles() -> None:
    """La nouvelle coque ne doit pas rendre inaccessibles les pages livrées.

    L'ancienne barre latérale exposait des entrées `data-tab` ; les pages de
    l'atelier (résultat, qualité, révision, profils, connecteurs, configuration)
    doivent conserver une route et un pont côté JS.
    """
    js = (WEB / "app-extras.js").read_text(encoding="utf-8")
    nav = (WEB / "navigation.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")

    # Plus aucune dépendance à un élément de navigation disparu.
    assert 'data-tab="tab-result"' not in js
    assert ".nav-item[data-tab=" not in js

    routes = dict(re.findall(r'"(tab-[a-z]+)": "([a-z/-]+)"', js))
    assert len(routes) >= 9, "les pages historiques doivent avoir une route"
    for page, route in routes.items():
        assert f'id="{page}"' in index, f"la page {page} doit exister"
        assert f"'{route}': '{page}'" in nav, \
            f"la route #{route} doit afficher {page}"


def test_comparaison_inter_documents_dans_l_espace_dossier() -> None:
    """L'onglet OCR compare les mêmes champs entre documents et signale les écarts."""
    js = (WEB / "dossiers.js").read_text(encoding="utf-8")
    css = (WEB / "uniocr-ds.css").read_text(encoding="utf-8")

    assert "comparerExtractions" in js
    assert "/coherence" in js, "les constats du contrôle documentaire complètent la comparaison"
    assert 'documents.length < 2' in js, "la comparaison exige au moins deux documents"
    # Une divergence ne doit jamais être « corrigée » automatiquement.
    assert "à arbitrer" in js
    for marqueur in (".ocr-compare", ".ocr-matrix", "is-divergent"):
        assert marqueur in css, f"le style {marqueur} doit exister"

    # Les 11 onglets de l'espace dossier restent déclarés.
    for onglet in ("synthese", "informations", "documents", "ocr", "controle",
                   "anomalies", "maritime", "douane", "frais", "enlevement", "historique"):
        assert f'cle: "{onglet}"' in js, f"l'onglet {onglet} doit rester présent"


def test_accessibilite_de_base() -> None:
    """Lien d'évitement, cible de contenu, champs nommés, page courante."""
    index = (WEB / "index.html").read_text(encoding="utf-8")
    nav = (WEB / "navigation.js").read_text(encoding="utf-8")
    css = (WEB / "uniocr-ds.css").read_text(encoding="utf-8")

    assert 'class="skip-link"' in index and 'href="#contenu-principal"' in index
    assert 'id="contenu-principal"' in index
    assert '<html lang="fr"' in index
    assert ":focus-visible" in css

    for champ in ("dashboardPeriod", "dashboardClient", "dashboardPort",
                  "dashboardManager", "transitFileInput"):
        balise = re.search(r"<[^>]*id=\"" + champ + r"\"[^>]*>", index)
        assert balise, f"le champ {champ} doit exister"
        assert "aria-label" in balise.group(0), \
            f"{champ} doit porter un libellé accessible"

    assert "aria-current" in nav, "le lien courant doit être annoncé aux lecteurs d'écran"


def test_rapports_utilisent_les_graphiques_du_serveur() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "rapports.js").read_text(encoding="utf-8")
    charts = (WEB / "charts.js").read_text(encoding="utf-8")
    assert '/web/rapports.js' in index
    for primitive in ("line", "donut", "bars", "sparkline"):
        assert primitive + ":" in charts or primitive + ": function" in charts or f"function {primitive}" in charts, \
            f"charts.js doit exposer {primitive}"

    graphiques = re.findall(r'cle: "([a-z-]+)"', js)
    assert len(graphiques) >= 6
    chemins = set(app.openapi()["paths"])
    for graphique in graphiques:
        assert f"/api/dashboard/graphique/{graphique}" in chemins, \
            f"le graphique {graphique} doit exister côté serveur"


def test_routage_des_sous_pages_vers_leurs_pages() -> None:
    js = (WEB / "navigation.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    correspondances = re.findall(r"'([a-z-]+/[a-z-]+)': '(tab-[a-z-]+)'", js)
    assert len(correspondances) >= 15, "le routage fin des sous-rubriques doit être déclaré"
    for route, page in correspondances:
        assert f'id="{page}"' in index, f"{route} pointe vers {page} qui doit exister"


def test_aucune_grille_inline_pour_le_responsive() -> None:
    """Les grilles multi-colonnes passent par des classes (elles se replient)."""
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert "grid-template-columns" not in index, (
        "les grilles doivent utiliser .cols-half/.cols-third/.cols-source "
        "pour bénéficier des points de rupture"
    )


def test_atelier_ocr_rappelle_la_portee_des_extractions() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert index.count("note-reglementaire") >= 2
    assert "ne constituent pas une validation" in index
    assert "Validation humaine" in index


# ── Design system ─────────────────────────────────────────────────────────

def test_palette_imposee_centralisee_dans_le_design_system() -> None:
    """La palette de la mission est déclarée une seule fois, dans le DS."""
    import re

    css = (WEB / "uniocr-ds.css").read_text(encoding="utf-8")
    # Le premier bloc `:root` porte la palette de référence ; les blocs de
    # thème clair qui suivent redéfinissent volontairement certaines valeurs.
    debut = css.index(":root {")
    racine = css[debut:css.index("}", debut)]
    jetons = dict(re.findall(r"(--ds-[a-z0-9-]+)\s*:\s*([^;]+);", racine))
    jetons = {cle: valeur.strip().upper() for cle, valeur in jetons.items()}

    palette = {
        "--ds-night": "#020817",
        "--ds-sidebar": "#061329",
        "--ds-surface": "#0B1B35",
        "--ds-surface-2": "#102644",
        "--ds-blue": "#1677FF",
        "--ds-cyan": "#00D9FF",
        "--ds-teal": "#00CBA8",
        "--ds-text": "#F1F5FF",
        "--ds-text-muted": "#94A9C7",
        "--ds-red": "#F04452",
        "--ds-amber": "#F59E0B",
        "--ds-violet": "#9466F5",
    }
    for jeton, valeur in palette.items():
        assert jetons.get(jeton) == valeur, (
            f"{jeton} doit valoir {valeur} dans uniocr-ds.css (lu : {jetons.get(jeton)})"
        )


def test_jetons_historiques_conserves_pour_les_tests_existants() -> None:
    index_css = (WEB / "styles.css").read_text(encoding="utf-8")
    for jeton in ("--blue-accent", "--ink-dark", "--ink-light", "--ink-neutral",
                  "--font-display", "--font-ui", "--font-mono"):
        assert jeton in index_css, f"{jeton} doit rester défini (compatibilité des tests)"


def test_design_system_annule_les_animations_si_demande() -> None:
    css = (WEB / "uniocr-ds.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in css
    assert "@media print" in css


def test_navigation_declare_douze_rubriques() -> None:
    js = (WEB / "navigation.js").read_text(encoding="utf-8")
    # 12 rubriques : cockpit + 11 modules (dont administration & sécurité).
    assert js.count("requiredRole:") >= 12
    for cle in ("cockpit", "workspace", "dossiers", "documents", "controle", "maritime",
                "douane", "enlevissement", "finance", "reports", "referentiels", "admin"):
        assert f"key: '{cle}'" in js, f"la rubrique {cle} doit rester déclarée"


def test_sidebar_repliee_et_infobulles_gerees() -> None:
    css = (WEB / "uniocr-ds.css").read_text(encoding="utf-8")
    js = (WEB / "navigation.js").read_text(encoding="utf-8")
    assert ".app.collapsed" in css, "l'état replié doit être stylé"
    assert "data-tip" in js, "chaque entrée doit porter une infobulle pour le mode replié"
    assert "uniocr_nav_" in js, "l'état des groupes doit être mémorisé"


# ── Routes d'interface ────────────────────────────────────────────────────

def test_bootstrap_interface(client) -> None:
    reponse = client.get("/api/ui/bootstrap")
    assert reponse.status_code == 200, reponse.text
    donnees = reponse.json()
    assert "utilisateur" in donnees
    assert "compteurs" in donnees
    compteurs = donnees["compteurs"]
    for cle in ("dossiers", "dossiers_en_cours", "dossiers_a_valider",
                "dossiers_clos", "dossiers_bloques", "notifications_non_lues"):
        assert cle in compteurs, f"compteur {cle} attendu"
        assert isinstance(compteurs[cle], int)


def test_serie_dossiers_bornee(client) -> None:
    reponse = client.get("/api/dashboard/serie-dossiers", params={"jours": 7})
    assert reponse.status_code == 200, reponse.text
    donnees = reponse.json()
    assert donnees["periode_jours"] == 7
    assert len(donnees["series"]) == 7
    assert set(donnees["series"][0]) == {"date", "crees", "traites", "clotures"}
    assert set(donnees["totaux"]) == {"crees", "traites", "clotures"}

    # Les bornes sont appliquées côté serveur (pas de fenêtre absurde).
    assert client.get("/api/dashboard/serie-dossiers", params={"jours": 0}).json()["periode_jours"] == 1
    assert client.get("/api/dashboard/serie-dossiers", params={"jours": 5000}).json()["periode_jours"] == 365


def test_recherche_globale_multi_entites(client) -> None:
    dossier = client.post("/api/dossiers", json={
        "label": "Recherche premium", "profile": "importation",
    })
    assert dossier.status_code in (200, 201), dossier.text

    reponse = client.get("/api/search/global", params={"q": "premium"})
    assert reponse.status_code == 200, reponse.text
    donnees = reponse.json()
    assert set(donnees["groupes"]) == {"dossiers", "clients", "connaissements",
                                       "conteneurs", "documents"}
    assert donnees["total"] >= 1
    hit = donnees["groupes"]["dossiers"][0]
    for cle in ("kind", "id", "label", "route"):
        assert cle in hit

    vide = client.get("/api/search/global", params={"q": "zzzz-introuvable-zzzz"}).json()
    assert vide["total"] == 0


def test_recherche_globale_refuse_une_requete_vide(client) -> None:
    # `q` est obligatoire : une recherche vide est une erreur d'appel, pas un
    # « tout retourner ». L'interface ne l'envoie jamais (seuil de 2 caractères).
    assert client.get("/api/search/global", params={"q": ""}).status_code == 422


def test_aucune_couleur_dispersee_dans_les_rendus_js() -> None:
    """La palette vit dans `uniocr-ds.css` ; les rendus SVG lisent `palette.js`.

    Un code couleur écrit dans un composant casse la cohérence du design
    system (et le thème clair). Le test balaie les modules de rendu et refuse
    tout littéral hexadécimal à six chiffres.
    """
    racine = Path(__file__).resolve().parent.parent
    rendus = ["charts.js", "cockpit.js", "rapports.js", "modules.js",
              "souspages.js", "dossiers.js", "workspace.js", "navigation.js",
              "shell.js", "app-extras.js", "palette.js"]
    coupables = []
    for nom in rendus:
        fichier = racine / "web" / nom
        assert fichier.is_file(), f"module attendu absent : {nom}"
        for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
            code = ligne.split("//", 1)[0]
            if re.search(r"#[0-9A-Fa-f]{6}\b", code) or re.search(r"rgba?\(", code):
                coupables.append(f"{nom}:{numero}")
    assert not coupables, "couleurs codées en dur hors du design system : " + ", ".join(coupables)

    # La passerelle lit bien les jetons du design system.
    css = (racine / "web" / "uniocr-ds.css").read_text(encoding="utf-8")
    passerelle = (racine / "web" / "palette.js").read_text(encoding="utf-8")
    assert "--ds-neutral:" in css
    for jeton in ("--ds-blue", "--ds-cyan", "--ds-teal", "--ds-violet",
                  "--ds-amber", "--ds-red", "--ds-neutral"):
        assert jeton in passerelle, f"jeton non exposé par palette.js : {jeton}"

    # Et elle est chargée avant les modules qui dessinent.
    index = (racine / "web" / "index.html").read_text(encoding="utf-8")
    assert index.index("/web/palette.js") < index.index("/web/charts.js")
    assert index.index("/web/palette.js") < index.index("/web/cockpit.js")


def _analyser_html(source: str) -> tuple[list[str], list[str], dict[str, int]]:
    """Analyse le balisage : erreurs de nesting, ids dupliqués."""
    from html.parser import HTMLParser

    void = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
            "meta", "param", "source", "track", "wbr"}

    class Analyseur(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.pile: list[tuple[str, int]] = []
            self.erreurs: list[str] = []
            self.ids: dict[str, int] = {}

        def handle_starttag(self, tag, attrs):
            attributs = dict(attrs)
            if "id" in attributs:
                self.ids[attributs["id"]] = self.ids.get(attributs["id"], 0) + 1
            if tag in void:
                return
            self.pile.append((tag, self.getpos()[0]))

        def handle_endtag(self, tag):
            if tag in void:
                return
            if not self.pile:
                self.erreurs.append(f"</{tag}> orpheline ligne {self.getpos()[0]}")
                return
            if self.pile[-1][0] != tag:
                self.erreurs.append(
                    f"</{tag}> ligne {self.getpos()[0]} alors que "
                    f"<{self.pile[-1][0]}> (ligne {self.pile[-1][1]}) est ouvert"
                )
                for index in range(len(self.pile) - 1, -1, -1):
                    if self.pile[index][0] == tag:
                        del self.pile[index:]
                        return
                return
            self.pile.pop()

        def handle_data(self, data):
            texte = data.strip()
            # Un balisage recopié en texte (balise ouvrante amputée) est un bug
            # de rendu : le navigateur affiche alors le code à l'écran.
            if texte.startswith("<") and len(texte) < 80:
                self.erreurs.append(f"balise affichée en texte ligne {self.getpos()[0]} : {texte[:40]}")

    analyseur = Analyseur()
    analyseur.feed(source)
    for tag, ligne in analyseur.pile:
        analyseur.erreurs.append(f"<{tag}> ligne {ligne} jamais fermé")
    return analyseur.erreurs, [], analyseur.ids


def test_le_document_html_est_structurellement_sain() -> None:
    """Le balisage ne doit jamais laisser du code s'afficher dans la page.

    Une balise ouvrante amputée (`section id="…"`) fait sortir les sections
    suivantes de `<main>` : elles s'empilent alors sous la coque et la
    navigation paraît inerte.
    """
    racine = Path(__file__).resolve().parent.parent
    index = (racine / "web" / "index.html").read_text(encoding="utf-8")

    erreurs, _, ids = _analyser_html(index)
    assert not erreurs, "balisage déséquilibré :\n" + "\n".join(erreurs)
    doublons = {cle: nombre for cle, nombre in ids.items() if nombre > 1}
    assert not doublons, f"identifiants dupliqués : {doublons}"

    # Toutes les pages restent dans la zone de travail : sinon elles
    # s'affichent les unes sous les autres, hors de la mise en page.
    assert index.count('<section id="tab-') == index.count('class="page"') - index.count('section.page')
    assert '<section id="tab-docs" class="page">' in index


def test_barre_laterale_utilisable_quand_elle_est_repliee() -> None:
    """En mode rail (≤ 1024 px), un clic doit toujours produire un effet."""
    racine = Path(__file__).resolve().parent.parent
    css = (racine / "web" / "uniocr-ds.css").read_text(encoding="utf-8")
    navigation = (racine / "web" / "navigation.js").read_text(encoding="utf-8")
    shell = (racine / "web" / "shell.js").read_text(encoding="utf-8")

    debut = css.index("@media (max-width: 1024px)")
    bloc = css[debut:css.index("@media (max-width: 820px)", debut)]
    assert ".nav-burger { display: inline-flex; }" in bloc, \
        "le bouton d'ouverture doit être visible dès le mode rail"
    assert ".app.nav-open .sidebar" in bloc, "le panneau complet doit pouvoir s'ouvrir"
    assert ".app.nav-open .sidebar .nav-subitem { display: flex; }" in bloc
    assert ".app.nav-open .sidebar .nav-label" in bloc

    # La largeur de la barre vient de la grille, pas du CSS hérité.
    assert ".sidebar { width: auto; }" in css

    # Le clic sur un groupe ouvre le panneau avant de déplier le groupe.
    assert "function basculerTiroir" in navigation
    assert "basculerTiroir(true)" in navigation
    assert "nav-open" in navigation and "nav-open" in shell
    assert "Fermer le menu" in shell or "Fermer le menu" in navigation


def test_service_worker_ne_sert_jamais_une_interface_perimee() -> None:
    """La coquille est servie réseau d'abord : une correction s'applique aussitôt."""
    racine = Path(__file__).resolve().parent.parent
    sw = (racine / "web" / "sw.js").read_text(encoding="utf-8")

    # Le nom du cache est versionné : toute refonte de la coquille l'incrémente,
    # ce qui purge les anciennes copies installées chez les postes.
    assert re.search(r'const CACHE = "unocr-shell-v\d+-', sw)
    assert '"/web/ecrans.js"' in sw
    assert "function reseauDAbord" in sw and "function estCoquille" in sw
    assert "reseauDAbord(req)" in sw
    # Les API ne passent jamais par le cache.
    assert 'url.pathname.startsWith("/api/")' in sw


def test_theme_sombre_par_defaut() -> None:
    """Le poste est sombre : une préférence système claire ne l'impose plus."""
    racine = Path(__file__).resolve().parent.parent
    extras = (racine / "web" / "app-extras.js").read_text(encoding="utf-8")

    assert 'root.setAttribute("data-theme", saved === "light" ? "light" : "dark")' in extras
    assert "prefers-color-scheme: light" not in extras
    # La bascule manuelle reste disponible.
    assert 'localStorage.setItem("unocr_theme", next)' in extras


def test_comparaison_inter_documents_dans_l_atelier() -> None:
    """L'atelier confronte l'extraction courante à d'autres documents réels."""
    racine = Path(__file__).resolve().parent.parent
    index = (racine / "web" / "index.html").read_text(encoding="utf-8")
    extras = (racine / "web" / "app-extras.js").read_text(encoding="utf-8")
    css = (racine / "web" / "uniocr-ds.css").read_text(encoding="utf-8")

    # Le panneau vit dans la page « Résultat d'analyse », pas dans une copie.
    section = index[index.index('<section id="tab-result"'):]
    section = section[:section.index("<!-- ─────────── 04 · QUALITÉ")]
    assert 'id="compareToggle"' in section
    assert 'id="compareHost"' in section
    assert 'aria-controls="compareHost"' in section
    assert "Comparaison inter-documents" in section
    # La portée est rappelée : une extraction n'est pas une validation.
    assert "validation" in section and "réglementaire" in section

    # Les documents proposés viennent de l'API, jamais d'une liste figée.
    assert 'fetchJson("/api/jobs?limit=500")' in extras
    assert 'j.status === "done"' in extras
    assert '"/api/jobs/" + id + "/result"' in extras
    assert "COMPARE_MAX = 3" in extras
    assert "matriceComparaison" in extras
    assert "source_file" in extras
    assert "is-divergent" in extras
    assert "aucune valeur" in extras.lower() or "n'est corrigée" in extras

    # Le rendu réutilise la matrice du design system (styles existants).
    assert ".ocr-matrix tr.is-divergent" in css
    assert ".ocr-compare__liste" in css
    assert ".ocr-matrix__type" in css


def test_chaque_liste_de_sous_page_appelle_une_route_reelle() -> None:
    """Aucune sous-page ne doit interroger un endpoint inexistant.

    Une URL fantôme produirait une liste vide impossible à distinguer d'un
    « aucune donnée » — exactement ce que la mission interdit.
    """
    chemins = set(app.openapi()["paths"])
    racine = Path(__file__).resolve().parent.parent
    fichiers = ["souspages.js", "modules.js", "rapports.js", "workspace.js"]

    fautifs: list[str] = []
    total = 0
    for nom in fichiers:
        source = (racine / "web" / nom).read_text(encoding="utf-8")
        for url in set(re.findall(r'"(/api/[^"?#]*)[^"]*"', source)):
            total += 1
            if url in chemins:
                continue
            # Un chemin paramétré côté client peut n'être qu'un préfixe.
            if any(chemin.startswith(url.rstrip("/") + "/") for chemin in chemins):
                continue
            fautifs.append(f"{nom} → {url}")
    assert total > 15
    assert not fautifs, "endpoints inexistants appelés par l'interface : " + ", ".join(fautifs)


def test_vues_d_ensemble_de_module_menent_a_des_ecrans_reels() -> None:
    """Les anciennes cartes « en préparation » sont remplacées par de vrais liens."""
    racine = Path(__file__).resolve().parent.parent
    modules = (racine / "web" / "modules.js").read_text(encoding="utf-8")
    css = (racine / "web" / "uniocr-ds.css").read_text(encoding="utf-8")

    assert "function construireHubs" in modules
    assert "window.Navigation.getConfig" in modules
    assert 'button.btn-block:not([id]):not([data-nav])' in modules
    assert "carte.hidden = true" in modules
    assert ".hub-link" in css and ".hub-links__grid" in css
    # Chaque vue d'ensemble déclarée correspond à une section qui existe.
    index = (racine / "web" / "index.html").read_text(encoding="utf-8")
    blocs = re.findall(r'"(tab-[a-z-]+)":\s*"[a-z-]+"', modules[modules.index("var HUBS"):])
    assert len(blocs) >= 8
    for identifiant in blocs:
        assert f'id="{identifiant}"' in index, f"page de module absente : {identifiant}"


def test_pages_sorties_de_la_zone_morte_sont_branchees() -> None:
    """Centre documentaire, GED, classification, ETA, mainlevées, planning."""
    racine = Path(__file__).resolve().parent.parent
    sous = (racine / "web" / "souspages.js").read_text(encoding="utf-8")

    attendus = {
        "tab-center": "/api/jobs",
        "tab-ged": "/api/dossiers",
        "tab-classif": "/api/document-types",
        "tab-eta-etd": "/api/dossiers",
        "tab-mainleves": "/api/terminal",
        "tab-planification": "/api/terminal",
    }
    for page, endpoint in attendus.items():
        assert f'"{page}": {{' in sous, f"page non branchée : {page}"
        bloc = sous[sous.index(f'"{page}": {{'):]
        # La dernière entrée de PAGES n'a pas de virgule finale.
        fin = re.search(r"\n    \}", bloc)
        assert fin, f"bloc illisible : {page}"
        bloc = bloc[:fin.start()]
        assert endpoint in bloc, f"{page} n'appelle pas {endpoint}"
        assert "vide:" in bloc, f"{page} n'a pas d'état vide explicite"


def test_sous_rubrique_sans_ecran_est_annoncee() -> None:
    """Retomber sur la vue d'ensemble du module doit être expliqué, pas subi."""
    racine = Path(__file__).resolve().parent.parent
    nav = (racine / "web" / "navigation.js").read_text(encoding="utf-8")
    css = (racine / "web" / "uniocr-ds.css").read_text(encoding="utf-8")

    assert "const SOUS_ROUTES = {}" in nav
    assert "replace(/^#/, '')" in nav, "les routes sont mémorisées sans dièse"
    assert "function signalerEcranAbsent" in nav
    assert "aSaProprePage" in nav, "un écran dédié ne doit pas déclencher l'avis"
    assert "n\\'a pas encore d\\'écran dédié" in nav
    assert "data-avis-route" in nav
    assert ".avis-route" in css
    # L'avis est retiré avant d'en poser un autre : jamais deux bandeaux.
    assert "document.querySelectorAll('[data-avis-route]').forEach" in nav


# ──────────────────────────────────────────────────────────────────────────
# Écrans métier déclaratifs (web/ecrans.js)
# ──────────────────────────────────────────────────────────────────────────

def _routes_ecrans() -> set[str]:
    """Routes d'écran déclarées dans le moteur (`#section/sous-ecran`)."""
    racine = Path(__file__).resolve().parent.parent
    source = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")
    routes = set(re.findall(r'^\s{4}"([a-z-]+/[a-z-]+)":\s*\{', source, re.M))
    routes |= set(re.findall(r'route:\s*"([a-z-]+/[a-z-]+)"', source))
    # Écrans construits par fabrique ou affectés après le littéral.
    routes |= set(re.findall(r'ecranDossiers\("([a-z-]+/[a-z-]+)"', source))
    routes |= set(re.findall(r'ECRANS\["([a-z-]+/[a-z-]+)"\]', source))
    return routes


def _route_pages() -> dict[str, str]:
    """Table `routePages` de navigation.js : route d'écran → section hôte."""
    racine = Path(__file__).resolve().parent.parent
    source = (racine / "web" / "navigation.js").read_text(encoding="utf-8")
    return dict(re.findall(r"'([a-z-]+/[a-z-]+)':\s*'(tab-[a-z-]+)'", source))


def test_chaque_ecran_declaratif_est_relie_a_une_section_reelle() -> None:
    """Aucun écran du catalogue ne doit être orphelin dans le routeur."""
    racine = Path(__file__).resolve().parent.parent
    html = (racine / "web" / "index.html").read_text(encoding="utf-8")
    pages = _route_pages()

    assert '<section id="tab-ecran" class="page">' in html
    assert "/web/ecrans.js" in html

    orphelins = sorted(r for r in _routes_ecrans() if pages.get(r) != "tab-ecran")
    assert orphelins == [], f"écrans sans section hôte : {orphelins}"


def test_chaque_ecran_est_atteignable_depuis_le_menu() -> None:
    """Un écran qui existe mais qu'aucun menu n'ouvre n'est pas livré."""
    racine = Path(__file__).resolve().parent.parent
    navigation = (racine / "web" / "navigation.js").read_text(encoding="utf-8")
    menu = set(re.findall(r"route:\s*'(#[a-z-]+/[a-z-]+)'", navigation))
    menu = {route.lstrip("#") for route in menu}

    inaccessibles = sorted(_routes_ecrans() - menu)

    assert inaccessibles == [], f"écrans sans entrée de menu : {inaccessibles}"


def test_les_urls_appelees_par_les_ecrans_existent_cote_serveur() -> None:
    """Toute URL `/api/…` du moteur d'écrans doit correspondre à une route réelle."""
    from tests._routes import iterer_routes, signature
    from unocr.api import app as application

    racine = Path(__file__).resolve().parent.parent
    source = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")
    urls = set(re.findall(r'["\'](/api/[A-Za-z0-9_\-/{}.]*)["\']', source))

    existantes = [(methode, signature(chemin)) for chemin, methode in iterer_routes(application)]

    inconnues: list[str] = []
    for url in sorted(urls):
        segments = signature(url)
        if url.endswith("/"):
            segments = segments + ["*"]
        if not any(
            len(candidat) == len(segments)
            and all(a == "*" or a == b for a, b in zip(candidat, segments))
            for _, candidat in existantes
        ):
            inconnues.append(url)

    assert inconnues == [], f"URL sans route serveur : {inconnues}"


def test_le_moteur_d_ecrans_a_son_stylesheet() -> None:
    """Les classes produites par le moteur existent réellement dans le design system."""
    racine = Path(__file__).resolve().parent.parent
    source = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")
    css = (racine / "web" / "uniocr-ds.css").read_text(encoding="utf-8")

    classes = {"ecran", "ecran__titre", "ecran__card", "ecran__voile", "ecran__boite",
               "ecran__form", "ecran__etat", "ecran__tableau", "ecran__skeleton"}
    produites = set(re.findall(r'elt\("[a-z]+",\s*"([a-z][a-z-]*)"', source))
    manquantes = sorted(c for c in classes if c not in produites and c not in css)
    assert manquantes == []
    for classe in sorted(classes):
        assert f".{classe}" in css, classe


def test_aucune_entree_de_menu_ne_retombe_sur_un_bandeau() -> None:
    """Chaque route du menu ouvre un écran : plus aucune redirection annoncée.

    Le bandeau « pas encore d'écran dédié » apparaît quand une route n'est ni
    mappée dans `routePages` ni servie par un écran de `web/ecrans.js`. Ce test
    échoue si une entrée de menu revient dans cet état.
    """
    racine = Path(__file__).resolve().parent.parent
    navigation = (racine / "web" / "navigation.js").read_text(encoding="utf-8")

    debut = navigation.index("const NAV_CONFIG")
    # Les routes de section (`#dossiers`, `#finance`…) ouvrent leur propre page
    # de module : seules les sous-rubriques peuvent retomber sur un bandeau.
    menu = {
        route.lstrip("#")
        for route in re.findall(r"route:\s*'(#[a-z-]+(?:/[a-z-]+)?)'", navigation[debut:])
        if "/" in route
    }
    couvertes = set(_route_pages()) | _routes_ecrans()

    orphelines = sorted(menu - couvertes)

    assert orphelines == [], f"entrées de menu sans écran : {orphelines}"


def test_file_de_revision_se_charge_a_l_ouverture() -> None:
    """La page Révision est atteinte par le hash : elle doit s'auto-charger.

    Sans ce déclencheur, la file restait vide jusqu'au clic sur « Actualiser ».
    Le test verrouille aussi le garde-fou `scrollIntoView`, dont l'absence ne
    doit jamais casser l'affichage de la file.
    """
    racine = Path(__file__).resolve().parent.parent
    extras = (racine / "web" / "app-extras.js").read_text(encoding="utf-8")

    assert ".addEventListener(\"hashchange\"" in extras
    assert "chargerRevueSiAffichee" in extras
    assert 'route === "documents/revue"' in extras
    assert 'typeof rows[focusIdx].scrollIntoView === "function"' in extras
    # L'erreur de rendu ne doit plus être présentée comme une API absente.
    assert "console.error(\"file de révision :\", e)" in extras


def test_actions_a_parametres_utilisent_la_query_string() -> None:
    """Les routes d'écriture à scalaires attendent des paramètres d'URL.

    Envoyer un corps JSON à ces routes produisait un 422 systématique
    (sortie portuaire, transitions de livraison). Le moteur construit donc
    l'URL quand l'action déclare `emplacement: "query"`.
    """
    racine = Path(__file__).resolve().parent.parent
    moteur = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")

    assert 'action.emplacement === "query"' in moteur
    assert "encodeURIComponent(cle)" in moteur
    for route in ("enlevissement/sortie-port", "enlevissement/livraison"):
        assert f'"{route}"' in moteur
    # Chaque action de ces deux écrans passe ses paramètres en query.
    assert moteur.count('emplacement: "query"') >= 5
    # Les transitions déclarent leurs champs (date, booléens, justificatif).
    for cle in ("justificatif_sortie", "date_sortie", "date_depart", "date_reelle",
                "preuve_signee", "date_signature"):
        assert f'cle: "{cle}"' in moteur


def test_administration_sans_controle_mort() -> None:
    """Les pages d'administration ne doivent pas afficher de boutons inertes.

    « + Nouveau workflow » existait sans gestionnaire ; la barre du journal
    d'audit et son bac « Chargement… » n'étaient pilotés par aucun script.
    """
    racine = Path(__file__).resolve().parent.parent
    html = (racine / "web" / "index.html").read_text(encoding="utf-8")
    extras = (racine / "web" / "app-extras.js").read_text(encoding="utf-8")
    nav = (racine / "web" / "navigation.js").read_text(encoding="utf-8")

    assert 'id="addWorkflow"' in html
    assert '$("addWorkflow")' in extras or "getElementById(\"addWorkflow\")" in extras
    assert "/api/rbac/workflows" in extras
    # Les contrôles d'audit morts ont été retirés au profit de la liste réelle.
    for mort in ("auditAdminRefresh", "auditAdminQuery", "auditAdminLog"):
        assert mort not in html
    # La route des moteurs OCR doit exister pour les deux libellés.
    assert "'admin/moteurs': 'tab-moteurs'" in nav
    assert "'admin/moteurs-ocr': 'tab-moteurs'" in nav


def test_rapports_sans_bouton_inerte() -> None:
    """La page Rapports ne doit plus afficher de boutons sans effet.

    Trois boutons (« Voir les statistiques », « Voir les graphiques »,
    « Exporter les données ») n'avaient aucun gestionnaire ; les graphiques
    réels, eux, sont produits par `web/rapports.js`.
    """
    racine = Path(__file__).resolve().parent.parent
    html = (racine / "web" / "index.html").read_text(encoding="utf-8")
    rapports = (racine / "web" / "rapports.js").read_text(encoding="utf-8")

    for mort in ("Voir les statistiques", "Voir les graphiques", "Exporter les données"):
        assert mort not in html
    # La navigation de la page pointe vers des écrans existants.
    assert 'href="#rapports/statistiques"' in html
    assert 'href="#rapports/exports"' in html
    # L'attribut cassé `classpage-header__meta` est corrigé.
    assert "classpage-header__meta" not in html
    assert 'data-rapports' in rapports


def test_ecran_fournisseurs_aligne_sur_le_contrat_api() -> None:
    """L'écran Fournisseurs doit envoyer les clés attendues par le serveur.

    Il envoyait `name`/`country`/`status` alors que l'API attend
    `nom`/`nom_commercial`/`pays` : toute création renvoyait 422.
    """
    racine = Path(__file__).resolve().parent.parent
    moteur = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")
    debut = moteur.index('"referentiels/fournisseurs"')
    bloc = moteur[debut:debut + 2600]

    for cle in ("nom", "nom_commercial", "pays", "nif", "rc", "contact"):
        assert f'cle: "{cle}"' in bloc
    for absente in ('cle: "name"', 'cle: "country"', 'cle: "status"'):
        assert absente not in bloc


def test_champ_pays_limite_a_deux_caracteres() -> None:
    """Le champ pays des formulaires est un code ISO : il est bridé à 2 signes."""
    racine = Path(__file__).resolve().parent.parent
    moteur = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")

    assert "longueurMax" in moteur
    assert "controle.maxLength = champ.longueurMax" in moteur


def test_resultat_et_qualite_ont_un_point_d_entree() -> None:
    """« Résultat d'analyse » et « Contrôle qualité » affichent le document courant.

    Atteintes par le routage au hash, elles restaient vides faute de sélection.
    L'ouverture se fait désormais depuis la liste des documents traités, et
    l'absence de document est expliquée au lieu d'afficher des tirets.
    """
    racine = Path(__file__).resolve().parent.parent
    extras = (racine / "web" / "app-extras.js").read_text(encoding="utf-8")
    moteur = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")

    assert "window.UniOCRResultats" in extras
    assert "ouvrir: function (id)" in extras
    assert "documents/resultat" in extras and "documents/qualite" in extras
    assert "data-vide-resultat" in extras
    # L'action n'est proposée que pour un document réellement traité.
    assert 'libelle: "Ouvrir le résultat"' in moteur
    assert 'String(ligne.status || "") !== "done"' in moteur


def test_ecran_utilisateurs_permet_de_creer_le_premier_compte() -> None:
    """La page « Utilisateurs » doit permettre de créer un compte.

    Le cloisonnement RBAC est inactif tant qu'aucun utilisateur n'existe ; la
    page ne proposait aucun moyen d'en créer un. Elle expose maintenant un
    écran déclaratif avec création (rôles et dossiers saisis en listes), édition
    et suppression, et affiche le jeton **une seule fois** à la création.
    """
    racine = Path(__file__).resolve().parent.parent
    moteur = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")
    nav = (racine / "web" / "navigation.js").read_text(encoding="utf-8")
    html = (racine / "web" / "index.html").read_text(encoding="utf-8")

    debut = moteur.index('"admin/utilisateurs"')
    bloc = moteur[debut:debut + 2600]
    assert 'url: "/api/rbac/utilisateurs"' in bloc
    assert 'sourceCle: "utilisateurs"' in bloc
    assert 'type: "liste"' in bloc
    assert "afficherResultat(\"Jeton d'accès" in bloc

    # La liste ne dépend plus de la page historique retirée.
    assert "'admin/utilisateurs': 'tab-ecran'" in nav
    assert 'id="tab-utilisateurs"' not in html
    # Le type « liste » convertit la saisie en tableau pour l'API.
    assert 'entree.definition.type === "liste"' in moteur


def test_ecran_roles_distingue_livres_et_personnalises() -> None:
    """Les rôles livrés ne sont pas modifiables, les rôles locaux le sont.

    La page « Rôles et permissions » affichait un catalogue en lecture seule et
    ne permettait aucune création. Elle liste maintenant les deux origines et
    masque les actions sur les rôles fournis avec l'application.
    """
    racine = Path(__file__).resolve().parent.parent
    moteur = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")
    nav = (racine / "web" / "navigation.js").read_text(encoding="utf-8")
    html = (racine / "web" / "index.html").read_text(encoding="utf-8")

    debut = moteur.index('"admin/roles"')
    bloc = moteur[debut:debut + 4600]
    assert 'url: "/api/rbac/roles"' in bloc
    assert "roles_disponibles" in bloc
    assert "masquer: function (ligne) { return !ligne.role_id; }" in bloc
    assert "masquer" in moteur  # le moteur sait masquer une action par ligne

    assert "'admin/roles': 'tab-ecran'" in nav
    assert 'id="tab-roles"' not in html


def test_ecran_parametres_generaux_ecrit_vraiment() -> None:
    """La page « Paramètres généraux » écrit dans une API qui persiste.

    La version précédente affichait un formulaire pré-rempli sans jamais
    enregistrer. L'écran actuel lit `/api/parametres`, modifie par PUT et
    rétablit le défaut par DELETE — on vérifie ici le câblage, le serveur étant
    couvert par `tests/test_parametres.py`.
    """
    racine = Path(__file__).resolve().parent.parent
    moteur = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")
    nav = (racine / "web" / "navigation.js").read_text(encoding="utf-8")
    serveur = (racine / "src" / "unocr" / "routes" / "parametres.py").read_text(
        encoding="utf-8")

    debut = moteur.index('ECRANS["referentiels/parametres"]')
    bloc = moteur[debut:debut + 1800]
    assert 'source: { url: "/api/parametres" }' in bloc
    assert 'sourceCle: "parametres"' in bloc
    assert 'url: "/api/parametres/{id}"' in bloc
    assert 'methode: "DELETE"' in bloc          # « Rétablir le défaut »
    assert "masquer: function (ligne) { return !ligne.modifie; }" in bloc

    # la route n'est plus une page morte : elle est branchée sur le moteur
    assert "{ key: 'settings', title: 'Paramètres généraux', route: '#referentiels/parametres'" in nav
    assert "'referentiels/parametres': 'tab-ecran'" in nav

    # le serveur valide en nommant le champ et persiste hors de config/
    assert '"champ": self.cle' in serveur
    assert "parametres.json" in serveur or "parametres_path" in serveur


def test_formulaires_proposent_les_referentiels_et_disent_quand_ils_sont_vides() -> None:
    """Les champs « pays » et « ports » s'appuient sur les référentiels réels.

    Un référentiel vide ne doit pas bloquer une saisie : le champ reste libre
    et l'interface explique où ajouter les entrées. Ce test vérifie le câblage
    (moteur + dialogue de création de dossier) ; le contenu vient de l'API.
    """
    racine = Path(__file__).resolve().parent.parent
    moteur = (racine / "web" / "ecrans.js").read_text(encoding="utf-8")
    dossiers = (racine / "web" / "dossiers.js").read_text(encoding="utf-8")
    html = (racine / "web" / "index.html").read_text(encoding="utf-8")

    # moteur générique : datalist alimentée par /api/referentiels/<nom>
    assert "function suggestionsReferentiel(nom)" in moteur
    assert 'lire("/api/referentiels/" + encodeURIComponent(nom))' in moteur
    assert "Référentiel « \" + champ.referentiel + \" » vide : " in moteur
    assert "datalist" in moteur

    # champs reliés : clients, fournisseurs, navires
    assert moteur.count('referentiel: "pays"') >= 3

    # dialogue de création de dossier : ports servis par le référentiel
    assert 'list="dos-ports-chargement"' in html
    assert 'id="dos-ports-aide"' in html
    assert 'fetch("/api/referentiels/ports"' in dossiers
    assert "Référentiel des ports vide : saisie libre" in dossiers
