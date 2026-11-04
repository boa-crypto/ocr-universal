"""Form builder du dossier documentaire (étape 12).

**Ce que c'est.** Une façon de décrire la structure des données qu'un dossier
porte : quels champs, dans quel ordre, obligatoires ou non. Le formulaire sert
à deux choses — donner une vue lisible du contenu d'un dossier, et produire un
paquet dont la forme est déclarée plutôt que déduite au dernier moment.

**Ce que ce n'est pas.** Ce n'est pas un formulaire administratif et ce n'est
pas une soumission. Rien n'est envoyé à un organisme, aucun format officiel
n'est prétendu. Un champ n'existe ici que pour deux raisons :

1. il correspond à une valeur **réellement extraite** d'un document du dossier ;
2. ou un humain l'a **explicitement ajouté**.

Aucun champ n'est inventé pour « compléter » un formulaire. Un champ vide
reste vide et se signale comme tel.

**Distinction avec `connectors/forms.py`.** Ce module-là décrit des formulaires
destinés à des systèmes externes (transmission). Celui-ci décrit la structure
interne d'un dossier : pas de endpoint, pas de soumission, pas de connecteur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from .storage import audit

FORM_VERSION = "1.0"

# types de champ reconnus — les mêmes que les connecteurs, pour qu'un champ
# passe de l'un à l'autre sans traduction
TYPES_CHAMP = ("text", "identifier", "number", "amount", "date", "list", "boolean")

# origines possibles d'un champ du formulaire
ORIGINES = ("extrait", "ajoute", "calcule")

LIBELLES_ORIGINE = {
    "extrait": "extrait d'un document",
    "ajoute": "ajouté par un humain",
    "calcule": "calculé à partir d'autres champs",
}


@dataclass
class ChampFormulaire:
    """Un champ du formulaire — avec la preuve de sa provenance."""
    key: str
    label: str = ""
    type: str = "text"
    required: bool = False
    origine: str = "extrait"
    # d'où vient la valeur affichée : (job_id, nom du champ extrait)
    source_job: Optional[str] = None
    source_field: Optional[str] = None
    valeur: Any = None
    # la valeur a-t-elle été validée par un humain ?
    valide: bool = False
    # unité ou format indicatif (jamais une contrainte réglementaire)
    unite: str = ""
    aide: str = ""
    valeurs_possibles: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "label": self.label or self.key, "type": self.type,
            "required": self.required, "origine": self.origine,
            "source_job": self.source_job, "source_field": self.source_field,
            "valeur": self.valeur, "valide": self.valide,
            "unite": self.unite, "aide": self.aide,
            "valeurs_possibles": list(self.valeurs_possibles),
        }

    @property
    def est_rempli(self) -> bool:
        return self.valeur not in (None, "")


@dataclass
class FormulaireDossier:
    """Structure déclarée des données d'un dossier."""
    formulaire_id: str
    dossier_id: str
    label: str = ""
    description: str = ""
    version: str = FORM_VERSION
    champs: list[ChampFormulaire] = field(default_factory=list)

    def champ(self, key: str) -> Optional[ChampFormulaire]:
        for c in self.champs:
            if c.key == key:
                return c
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "formulaire_id": self.formulaire_id, "dossier_id": self.dossier_id,
            "label": self.label, "description": self.description,
            "version": self.version,
            "champs": [c.as_dict() for c in self.champs],
            "remplissage": self.remplissage(),
        }

    def remplissage(self) -> dict[str, Any]:
        """État de remplissage — compté, pas estimé."""
        total = len(self.champs)
        remplis = sum(1 for c in self.champs if c.est_rempli)
        valides = sum(1 for c in self.champs if c.valide)
        requis = [c for c in self.champs if c.required]
        requis_manquants = [c.key for c in requis if not c.est_rempli]
        return {
            "total": total, "remplis": remplis, "valides": valides,
            "requis": len(requis), "requis_manquants": requis_manquants,
            "complet": not requis_manquants,
        }


# ─────────────────────────────── construction ───────────────────────────────

def construit_depuis_dossier(dossier, documents: Iterable[dict],
                             formulaire_id: str = "") -> FormulaireDossier:
    """Construit le formulaire d'un dossier à partir de ses documents.

    `documents` est une liste de dictionnaires décrivant chaque pièce :
    `{"job_id", "filename", "category", "champs": {nom: {...}}}`.

    **Règle absolue :** un champ n'est créé que si une valeur a réellement été
    extraite. Un document sans champ reconnu n'ajoute rien au formulaire.
    L'ordre suit l'ordre des pièces du dossier, puis l'ordre des champs.
    """
    formulaire = FormulaireDossier(
        formulaire_id=formulaire_id or f"frm_{dossier.id}",
        dossier_id=dossier.id,
        label=f"Formulaire — {dossier.label}",
        description=("Structure déduite des documents du dossier. "
                     "Aucun champ n'est inventé : chacun provient d'une "
                     "valeur extraite ou d'un ajout humain explicite."),
    )

    vus: dict[str, ChampFormulaire] = {}
    for doc in documents:
        job_id = doc.get("job_id", "")
        for nom, fv in (doc.get("champs") or {}).items():
            valeur = (fv.get("confirmed_value") or fv.get("corrected_value")
                      or fv.get("normalized_value") or fv.get("raw_value"))
            if valeur in (None, ""):
                continue        # rien à déclarer : le champ reste absent
            statut = fv.get("status")
            champ = ChampFormulaire(
                key=nom,
                label=fv.get("label") or nom,
                type=_devine_type(nom, valeur),
                required=False,       # « requis » est un choix humain
                origine="extrait",
                source_job=job_id,
                source_field=nom,
                valeur=valeur,
                valide=statut in ("validated", "corrected"),
                aide=f"extrait de {doc.get('filename') or job_id}",
            )
            existant = vus.get(nom)
            if existant is None:
                vus[nom] = champ
                formulaire.champs.append(champ)
            else:
                # même champ sur plusieurs documents : on garde les deux
                # valeurs plutôt que d'en choisir une en silence
                existant.aide += f" ; aussi dans {doc.get('filename') or job_id}"
                if not existant.est_rempli and champ.est_rempli:
                    existant.valeur = champ.valeur
                    existant.source_job = job_id

    return formulaire


def _devine_type(key: str, valeur: Any) -> str:
    """Type indicatif d'un champ, d'après son nom et sa valeur.

    Ce n'est qu'une aide à l'affichage : aucune validation n'en dépend.
    """
    k = key.lower()
    if any(m in k for m in ("date", "echeance", "due")):
        return "date"
    if any(m in k for m in ("weight", "poids", "amount", "montant", "total",
                            "price", "prix", "qty", "quantity", "quantite")):
        return "amount" if any(m in k for m in ("amount", "montant", "total",
                                                "price", "prix")) else "number"
    if any(m in k for m in ("number", "no", "ref", "code", "numero", "bl",
                            "invoice", "container", "serial", "iban", "vat",
                            "hs_code")):
        return "identifier"
    if isinstance(valeur, bool):
        return "boolean"
    return "text"


def ajoute_champ(formulaire: FormulaireDossier, key: str, label: str = "",
                 type: str = "text", required: bool = False, valeur: Any = None,
                 aide: str = "", acteur: str = "utilisateur") -> ChampFormulaire:
    """Ajout humain explicite d'un champ. Traçable, jamais silencieux."""
    key = (key or "").strip()
    if not key:
        raise ValueError("clé de champ vide")
    if type not in TYPES_CHAMP:
        raise ValueError(f"type inconnu : {type} (autorisés : {', '.join(TYPES_CHAMP)})")
    if formulaire.champ(key) is not None:
        raise ValueError(f"champ déjà présent : {key}")
    champ = ChampFormulaire(
        key=key, label=label or key, type=type, required=required,
        origine="ajoute", valeur=valeur, aide=aide,
    )
    formulaire.champs.append(champ)
    return champ


def retire_champ(formulaire: FormulaireDossier, key: str,
                 acteur: str = "utilisateur") -> bool:
    """Retire un champ **du formulaire** — jamais du document source."""
    avant = len(formulaire.champs)
    formulaire.champs = [c for c in formulaire.champs if c.key != key]
    return len(formulaire.champs) != avant


def renseigne(formulaire: FormulaireDossier, key: str, valeur: Any,
              valide: bool = False, acteur: str = "utilisateur") -> ChampFormulaire:
    """Renseigne un champ existant. Un champ inconnu est refusé.

    Refuser plutôt que créer évite qu'une faute de frappe fasse apparaître un
    champ qui n'existe nulle part ailleurs.
    """
    champ = formulaire.champ(key)
    if champ is None:
        raise ValueError(f"champ inconnu : {key}")
    champ.valeur = valeur
    champ.valide = bool(valide)
    return champ


# ─────────────────────────────── persistance ───────────────────────────────

class FormulaireStore:
    """Formulaires de dossier persistés en JSON, écriture atomique."""

    def __init__(self, root: Path, log_dir: Optional[Path] = None) -> None:
        self.root = Path(root)
        self.log_dir = Path(log_dir) if log_dir else None
        self.root.mkdir(parents=True, exist_ok=True)

    def _chemin(self, formulaire_id: str) -> Path:
        sur = formulaire_id.replace("/", "_").replace("\\", "_")
        if sur in (".", ".."):
            raise ValueError(f"identifiant de formulaire invalide : {formulaire_id}")
        return self.root / f"{sur}.json"

    def sauve(self, formulaire: FormulaireDossier,
              acteur: str = "utilisateur") -> Path:
        cible = self._chemin(formulaire.formulaire_id)
        tmp = cible.with_suffix(".tmp")
        tmp.write_text(_json_dumps(formulaire.as_dict()), encoding="utf-8")
        tmp.replace(cible)
        if self.log_dir:
            audit(self.log_dir, "dossier_form_saved",
                  formulaire_id=formulaire.formulaire_id,
                  dossier_id=formulaire.dossier_id,
                  champs=len(formulaire.champs), acteur=acteur)
        return cible

    def charge(self, formulaire_id: str) -> Optional[FormulaireDossier]:
        p = self._chemin(formulaire_id)
        if not p.is_file():
            return None
        return _depuis_dict(_json_loads(p.read_text(encoding="utf-8")))

    def liste(self) -> list[FormulaireDossier]:
        sortie = []
        for p in sorted(self.root.glob("*.json")):
            try:
                sortie.append(_depuis_dict(_json_loads(p.read_text(encoding="utf-8"))))
            except (ValueError, KeyError):
                continue
        return sortie

    def supprime(self, formulaire_id: str) -> bool:
        p = self._chemin(formulaire_id)
        if not p.is_file():
            return False
        p.unlink()
        if self.log_dir:
            audit(self.log_dir, "dossier_form_deleted",
                  formulaire_id=formulaire_id)
        return True


def _json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def _json_loads(texte: str) -> Any:
    import json
    return json.loads(texte)


def _depuis_dict(d: dict) -> FormulaireDossier:
    champs = []
    for c in d.get("champs") or []:
        champs.append(ChampFormulaire(
            key=c["key"], label=c.get("label", ""), type=c.get("type", "text"),
            required=bool(c.get("required")), origine=c.get("origine", "extrait"),
            source_job=c.get("source_job"), source_field=c.get("source_field"),
            valeur=c.get("valeur"), valide=bool(c.get("valide")),
            unite=c.get("unite", ""), aide=c.get("aide", ""),
            valeurs_possibles=c.get("valeurs_possibles") or [],
        ))
    return FormulaireDossier(
        formulaire_id=d["formulaire_id"], dossier_id=d.get("dossier_id", ""),
        label=d.get("label", ""), description=d.get("description", ""),
        version=d.get("version", FORM_VERSION), champs=champs,
    )


# ─────────────────────────────── aperçu ───────────────────────────────

def apercu_textuel(formulaire: FormulaireDossier) -> str:
    """Rendu texte du formulaire — lisible sans aucune dépendance graphique."""
    lignes = [formulaire.label, "=" * min(70, len(formulaire.label)), ""]
    if formulaire.description:
        lignes.append(formulaire.description)
        lignes.append("")
    if not formulaire.champs:
        lignes.append("(aucun champ : aucun document du dossier n'a fourni "
                      "de valeur extractible)")
        return "\n".join(lignes)

    for c in formulaire.champs:
        marque = "✓" if c.valide else ("•" if c.est_rempli else "○")
        requis = " [requis]" if c.required else ""
        valeur = "—" if not c.est_rempli else str(c.valeur)
        unite = f" {c.unite}" if c.unite else ""
        lignes.append(f"{marque} {c.label}{requis}")
        lignes.append(f"    {c.key} ({c.type}) : {valeur}{unite}")
        lignes.append(f"    {LIBELLES_ORIGINE.get(c.origine, c.origine)}")
        if c.aide:
            lignes.append(f"    {c.aide}")
        lignes.append("")

    r = formulaire.remplissage()
    lignes.append(f"{r['remplis']}/{r['total']} champs remplis, "
                  f"{r['valides']} validés, {len(r['requis_manquants'])} "
                  f"champ(s) requis manquant(s)")
    return "\n".join(lignes)
