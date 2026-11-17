"""Garde-fous contre l'injection de script dans l'interface (XSS).

**Pourquoi ce test existe.** L'interface servait le nom d'un champ métier
dans un gestionnaire en ligne (`onclick="confirmField('…')"`). Ce nom
provient d'un **profil d'extraction**, donc d'une donnée que l'utilisateur
peut contrôler. Or l'échappement HTML ne rend pas une valeur sûre dans
du JavaScript : le navigateur décode les entités *avant* d'évaluer le
gestionnaire. Une apostrophe suffisait à fermer la chaîne et à injecter
du code.

Ce test verrouille deux choses :
1. plus aucun gestionnaire en ligne dans les modules servis ;
2. les valeurs issues de l'API sont écrites par des API DOM sûres
   (`textContent`, `dataset`) et non par concaténation dans du HTML.

Ce test est **statique** : il analyse le code servi. Aucun navigateur
n'est requis, et il ne se dégrade pas dans un environnement sans node.
"""
from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"

#: Attribut de gestionnaire en ligne dans du **HTML** : toute présence est
#: un risque. On exige que l'attribut soit réellement dans une balise,
#: c'est-à-dire précédé d'une espace ou d'un chevron — ce qui exclut une
#: affectation JavaScript (`img.onerror = …`), qui est sans danger.
GESTIONNAIRES_EN_LIGNE = re.compile(
    r"""(?:<[^<>]*?|\s)"""
    r"""\bon(?:click|change|input|submit|error|load|mouseover|mouseout|"""
    r"""focus|blur|keydown|keyup|keypress|dblclick|contextmenu|"""
    r"""pointerover|toggle|animationstart)\s*=\s*["']""",
    re.IGNORECASE,
)


def _fichiers_web() -> list[Path]:
    return sorted(
        p for p in WEB.rglob("*")
        if p.is_file() and p.suffix in {".html", ".js", ".css"}
    )


def test_aucun_gestionnaire_en_ligne_dans_les_modules_servis() -> None:
    """Aucun `onclick="…"` dans le code réellement servi.

    Les gestionnaires en ligne sont le vecteur classique : la valeur
    insérée dans la chaîne est décodée puis évaluée. Tout ce qui est
    piloté par l'utilisateur doit passer par `dataset` + `addEventListener`.
    """
    coupables: list[str] = []
    for chemin in _fichiers_web():
        texte = chemin.read_text(encoding="utf-8")
        # on ignore les commentaires : ils ne sont jamais exécutés
        sans_commentaires = re.sub(r"/\*.*?\*/", "", texte, flags=re.S)
        sans_commentaires = re.sub(r"<!--.*?-->", "", sans_commentaires, flags=re.S)
        sans_commentaires = re.sub(r"^\s*//.*$", "", sans_commentaires, flags=re.M)
        for numero, ligne in enumerate(sans_commentaires.splitlines(), 1):
            if GESTIONNAIRES_EN_LIGNE.search(ligne):
                coupables.append(f"{chemin.name}:{numero}: {ligne.strip()[:120]}")
    assert not coupables, (
        "gestionnaires en ligne interdits (injection de script possible) :\n"
        + "\n".join(coupables)
    )


def test_le_nom_de_champ_ne_rentre_plus_dans_un_gestionnaire() -> None:
    """Le nom d'un champ ne doit plus apparaître dans du JavaScript inline.

    C'était la faille exacte : `onclick="confirmField('${esc(name)}')"`.
    Le nom passe désormais par un attribut `data-*`.
    """
    # Le code concerné a été extrait dans web/app-extras.js : on controle
    # l'ensemble des sources servie par l'application, pas seulement le shell.
    sources = list(WEB.glob("*.html")) + list(WEB.glob("*.js")) + \
        list((WEB / "modules").glob("**/*.js"))
    textes = {chemin.name: chemin.read_text(encoding="utf-8") for chemin in sources}
    for nom, texte in textes.items():
        assert "confirmField('" not in texte, (
            f"le nom de champ est de nouveau injecté dans un gestionnaire "
            f"en ligne ({nom})"
        )
    # le nom de champ transite bien par un attribut de données
    assert any("data-confirm=" in texte for texte in textes.values()), (
        "le bouton de validation devrait porter l'identifiant du champ "
        "dans un attribut data-*"
    )


def test_les_valeurs_issues_de_l_api_ne_sont_pas_concatenees_en_html() -> None:
    """Les valeurs de l'API ne doivent pas être injectées en HTML brut.

    `esc()` échappe pour un contexte HTML. Insérer une valeur **dans**
    une balise (`<b>${valeur}</b>`) est correct ; l'insérer **dans un
    attribut** ou dans du JavaScript ne l'est pas. On vérifie ici que les
    chemins sensibles passent par `textContent` ou `dataset`.
    """
    index = (WEB / "index.html").read_text(encoding="utf-8")
    # le texte brut des résultats est écrit par textContent
    assert ".textContent =" in index, "les résultats devraient être écrits via textContent"
    # la recherche de champ confirmable ne passe plus par un sélecteur interpolé
    assert "querySelector(`input[data-field=" not in index, (
        "la recherche du champ confirmable ne doit plus utiliser un "
        "sélecteur interpolé avec une donnée"
    )


def test_les_variables_css_utilisees_sont_definies() -> None:
    """Toute variable CSS utilisée sans repli doit être définie.

    Une variable absente ne lève aucune erreur : la propriété retombe
    silencieusement sur sa valeur initiale. Un `color: var(--fg)` non
    défini donne un texte de la couleur par défaut — un défaut visuel
    invisible dans les tests, et jamais signalé par la console.

    Trois cas sont acceptés :
    * la variable est définie en CSS ;
    * l'usage fournit un repli : `var(--x, valeur)` ;
    * la variable est posée dynamiquement : `style.setProperty("--x", …)`.
    """
    defs: set[str] = set()
    poses: set[str] = set()
    sans_repli: dict[str, set[str]] = {}

    for chemin in _fichiers_web():
        texte = chemin.read_text(encoding="utf-8")
        defs.update(re.findall(r"--([a-zA-Z0-9_-]+)\s*:", texte))
        poses.update(re.findall(r"setProperty\(\s*[\"']--([a-zA-Z0-9_-]+)", texte))
        for nom, repli in re.findall(r"var\(\s*--([a-zA-Z0-9_-]+)\s*(,)?", texte):
            if not repli:  # pas de valeur de repli → la variable est obligatoire
                sans_repli.setdefault(nom, set()).add(chemin.name)

    manquantes = {
        nom: fichiers for nom, fichiers in sans_repli.items()
        if nom not in defs and nom not in poses
    }
    assert not manquantes, (
        "variables CSS utilisées sans repli et jamais définies : "
        + ", ".join(f"--{nom} ({', '.join(sorted(f))})"
                    for nom, f in sorted(manquantes.items()))
    )

