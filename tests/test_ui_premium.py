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
        assert url in chemins, f"{url} doit exister dans le contrat OpenAPI"


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
