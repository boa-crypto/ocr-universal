"""Contrôles de cohérence **interdocumentaires** (étape 8 du parcours).

**Pourquoi ce module existe.** Le projet contrôlait déjà la cohérence *à
l'intérieur* d'un document (`profiles.*.relations`, `quality.anomalies`). Rien
ne comparait plusieurs documents d'un même dossier — or c'est là que se trouvent
les incohérences les plus coûteuses : une référence de facture absente du
connaissement, un conteneur déclaré d'un côté et pas de l'autre, un poids qui
diverge entre liste de colisage et BL.

**Ce qu'il fait.** Il compare les champs extraits de plusieurs documents et
renvoie une liste de constats, chacun avec sa règle, sa gravité, les documents
et champs concernés, les valeurs comparées, le résultat, une explication et un
statut permettant une décision humaine.

**Ce qu'il ne fait pas.** Il ne décide pas qu'une différence est une erreur.
Une divergence peut être légitime (deux factures partielles, un arrondi de
poids) : la gravité par défaut est donc `warning`, et `blocking` n'existe que
si une règle est explicitement configurée comme bloquante.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

# gravités — du moins grave au plus grave
INFO = "information"
WARNING = "avertissement"
ANOMALY = "anomalie"
BLOCKING = "blocage"

GRAVITES_ORDRE = {INFO: 0, WARNING: 1, ANOMALY: 2, BLOCKING: 3}


@dataclass
class ChampDocument:
    """Vue minimaliste d'un champ, découplée du modèle OCR.

    Permet de tester la cohérence sans fabriquer un DocumentResult complet.
    """
    job_id: str
    filename: str
    category: str
    key: str
    value: Optional[str]
    label: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"job_id": self.job_id, "filename": self.filename,
                "category": self.category, "key": self.key,
                "label": self.label, "value": self.value}


@dataclass
class Constat:
    """Un constat de cohérence — affichable et décidable par un humain."""
    rule: str
    severity: str
    documents: list[str] = field(default_factory=list)
    champs: list[dict[str, Any]] = field(default_factory=list)
    valeurs: list[Any] = field(default_factory=list)
    resultat: str = ""            # ok | absent | divergent | doublon
    explication: str = ""
    status: str = "a_trancher"    # a_trancher | accepte | corrige | ignore
    decision_par: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule, "severity": self.severity,
            "documents": self.documents, "champs": self.champs,
            "valeurs": self.valeurs, "resultat": self.resultat,
            "explication": self.explication, "status": self.status,
            "decision_par": self.decision_par,
        }

    @property
    def bloquant(self) -> bool:
        return self.severity == BLOCKING


def _norm(v: Optional[str]) -> str:
    """Normalisation de comparaison : casse, espaces, séparateurs."""
    if v is None:
        return ""
    return " ".join(str(v).upper().split()).replace("-", "").replace("/", "")


def _nombre(v: Optional[str]) -> Optional[float]:
    """Extrait un nombre d'une valeur textuelle, ou None."""
    if v is None:
        return None
    import re
    txt = str(v).replace("\u202f", " ").replace("\xa0", " ").strip()
    txt = txt.replace(" ", "")
    # 1.234,56 -> 1234.56   |   1,234.56 -> 1234.56
    if "," in txt and "." in txt:
        if txt.rfind(",") > txt.rfind("."):
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", "")
    elif "," in txt:
        partie = txt.split(",")
        if len(partie) == 2 and len(partie[1]) in (1, 2):
            txt = txt.replace(",", ".")
        else:
            txt = txt.replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", txt)
    return float(m.group(0)) if m else None


#: tolérances par défaut, appliquées si la configuration ne les précise pas.
#: Une différence n'est pas une erreur : arrondis de pesée, conversions et
#: écarts légitimes entre documents doivent être tolérés avant d'alerter.
#: Gravité par défaut : warning (avertissement), bloquante seulement si règle configurée.
TOLERANCES_DEFAUT = {
    "gross_weight": 0.02,
    "net_weight": 0.02,
    "quantity": 0.05,
    "packages_count": 0.05,
    "amount": 0.01,
    "total_ttc": 0.01,
    "invoice_number": 0,  # pas de tolérance numérique : les numéros de facture doivent correspondre exactement
    "container_number": 0,  # pas de tolérance : les numéros de conteneur doivent correspondre exactement
    "party_name": 0,  # pas de tolérance : les noms des parties doivent correspondre exactement
}

#: clés de référence cherchées par défaut dans les autres pièces
CLES_REFERENCE_DEFAUT = ("invoice_number",)


class CoherenceEngine:
    """Moteur de contrôles interdocumentaires, configurable.

    La configuration vient de la clé `coherence` de `config/default.json` :

    ```json
    "coherence": {
      "tolerances": {"gross_weight": 0.02},
      "regles_desactivees": ["document_en_double"],
      "regles_bloquantes": ["poids_divergent:gross_weight"],
      "cles_reference": ["invoice_number"]
    }
    ```

    Une règle désactivée ne produit **aucun** constat : la désactiver doit
    vouloir dire qu'on ne la veut pas, pas qu'on la veut muette. Une règle
    bloquante non tranchée interdit la transmission (`peut_transmettre`).
    """

    def __init__(self, configuration: Optional[dict] = None,
                 regles_bloquantes: Optional[Iterable[str]] = None) -> None:
        # un appel ancien passait la liste des règles bloquantes en premier
        # argument ; la comprendre évite de casser les appelants existants
        if isinstance(configuration, (list, tuple, set)):
            configuration, regles_bloquantes = None, configuration
        cfg = dict(configuration or {})
        # compatibilité : l'ancien appel positionnel reste accepté
        bloquantes = cfg.get("regles_bloquantes") or list(regles_bloquantes or [])
        self.regles_bloquantes = set(bloquantes)
        self.regles_desactivees = set(cfg.get("regles_desactivees") or [])
        tolerances = dict(TOLERANCES_DEFAUT)
        tolerances.update(cfg.get("tolerances") or {})
        self.tolerances: dict[str, float] = tolerances
        self.cles_reference = list(cfg.get("cles_reference")
                                   or CLES_REFERENCE_DEFAUT)

    def tolerance(self, cle: str) -> float:
        """Tolérance applicable à une clé, ou la valeur par défaut."""
        return float(self.tolerances.get(cle, 0.02))

    def active(self, regle: str) -> bool:
        """Une règle désactivée ne doit produire aucun constat."""
        return regle not in self.regles_desactivees

    def configuration_effective(self) -> dict:
        """Ce que le moteur applique réellement — lisible, pour diagnostiquer."""
        return {
            "tolerances": dict(self.tolerances),
            "regles_bloquantes": sorted(self.regles_bloquantes),
            "regles_desactivees": sorted(self.regles_desactivees),
            "cles_reference": list(self.cles_reference),
        }

    # ───────────────────────────── règles ──────────────────────────────

    def verifie_reference_commune(self, champs: list[ChampDocument],
                                  cle: str = "invoice_number") -> list[Constat]:
        """Une référence présente dans un document doit exister dans les autres.

        Ne conclut à une anomalie que si la référence est **absente** ailleurs,
        pas si elle diffère : deux numéros de facture peuvent coexister
        légitimement dans un dossier (facture proforma + facture finale).
        """
        if not self.active(f"reference_divergente:{cle}"):
            return []
        constats = []
        avec = [c for c in champs if c.key == cle and _norm(c.value)]
        if len(avec) < 2:
            return constats
        valeurs = {_norm(c.value) for c in avec}
        if len(valeurs) > 1:
            constats.append(Constat(
                rule=f"reference_divergente:{cle}",
                severity=self._gravite(f"reference_divergente:{cle}", WARNING),
                documents=sorted({c.filename for c in avec}),
                champs=[c.as_dict() for c in avec],
                valeurs=sorted(valeurs),
                resultat="divergent",
                explication=(
                    f"la référence « {cle} » prend {len(valeurs)} valeurs "
                    "différentes selon le document. À vérifier : plusieurs "
                    "factures peuvent légitimement coexister dans un dossier."
                ),
            ))
        return constats

    def verifie_reference_absente(self, champs: list[ChampDocument],
                                  cle: str, attendu_dans: Iterable[str]) -> list[Constat]:
        """Un document devrait porter une référence qui n'y est pas."""
        if not self.active(f"reference_absente:{cle}"):
            return []
        constats = []
        for categorie in attendu_dans:
            presents = [c for c in champs if c.key == cle and _norm(c.value)]
            if not presents:
                continue
            for categorie_vue in {c.category for c in champs if c.category == categorie}:
                doc = [c for c in champs if c.category == categorie_vue]
                if not any(c.key == cle and _norm(c.value) for c in doc):
                    constats.append(Constat(
                        rule=f"reference_absente:{cle}->{categorie_vue}",
                        severity=self._gravite(f"reference_absente:{cle}->{categorie_vue}", WARNING),
                        documents=sorted({c.filename for c in doc}),
                        champs=[c.as_dict() for c in presents],
                        valeurs=sorted({_norm(c.value) for c in presents}),
                        resultat="absent",
                        explication=(
                            f"la référence « {cle} » figure dans "
                            f"{sorted({c.filename for c in presents})} mais pas "
                            f"dans le document « {categorie_vue} ». Le rapprochement "
                            "entre pièces est donc incomplet."
                        ),
                    ))
        return constats

    def verifie_conteneurs(self, champs: list[ChampDocument],
                           cle: str = "container_number") -> list[Constat]:
        """Conteneurs déclarés d'un côté et absents de l'autre."""
        if not self.active("conteneur_absent"):
            return []
        constats = []
        par_doc: dict[str, set[str]] = {}
        for c in champs:
            if c.key != cle:
                continue
            # « | » est le séparateur multi-valeurs des profils (multiline)
            for valeur in re.split(r"[;,|]", str(c.value or "")):
                v = _norm(valeur)
                if v:
                    par_doc.setdefault(c.category, set()).add(v)
        if len(par_doc) < 2:
            return constats
        tous = set().union(*par_doc.values())
        for categorie, conteneurs in par_doc.items():
            manquants = tous - conteneurs
            if manquants:
                constats.append(Constat(
                    rule=f"conteneur_absent:{cle}->{categorie}",
                    severity=self._gravite(f"conteneur_absent:{cle}->{categorie}", WARNING),
                    documents=sorted({c.filename for c in champs if c.category == categorie}),
                    champs=[c.as_dict() for c in champs if c.key == cle],
                    valeurs=sorted(manquants),
                    resultat="absent",
                    explication=(
                        f"{len(manquants)} conteneur(s) déclaré(s) ailleurs "
                        f"n'apparaissent pas dans « {categorie} » : "
                        f"{', '.join(sorted(manquants))}."
                    ),
                ))
        return constats

    def verifie_poids(self, champs: list[ChampDocument],
                      cle: str = "gross_weight",
                      tolerance: Optional[float] = None) -> list[Constat]:
        """Divergence de poids entre documents, au-delà d'une tolérance.

        La tolérance évite de signaler un simple arrondi de pesée comme une
        anomalie : 2 % par défaut, valeur documentée et configurable.
        """
        if not self.active("poids_divergent"):
            return []
        constats = []
        valeurs = [(c, _nombre(c.value)) for c in champs
                   if c.key == cle and _nombre(c.value) is not None]
        if len(valeurs) < 2:
            return constats
        nombres = [n for _, n in valeurs]
        ecart = max(nombres) - min(nombres)
        moyenne = sum(nombres) / len(nombres)
        if moyenne <= 0:
            return constats
        seuil = self.tolerance(cle) if tolerance is None else tolerance
        if ecart / moyenne > seuil:
            constats.append(Constat(
                rule=f"poids_divergent:{cle}",
                severity=self._gravite(f"poids_divergent:{cle}", ANOMALY),
                documents=sorted({c.filename for c, _ in valeurs}),
                champs=[c.as_dict() for c, _ in valeurs],
                valeurs=[{"document": c.filename, "valeur": n} for c, n in valeurs],
                resultat="divergent",
                explication=(
                    f"écart de {ecart:.2f} sur une moyenne de {moyenne:.2f} "
                    f"({ecart / moyenne * 100:.1f} %), au-delà de la tolérance "
                    f"de {seuil * 100:.0f} %. Un arrondi de pesée est "
                    "possible ; une divergence réelle doit être tranchée."
                ),
            ))
        return constats

    def verifie_doublons_documentaires(self, champs: list[ChampDocument],
                                       empreintes: Optional[dict[str, str]] = None
                                       ) -> list[Constat]:
        """Deux fois le même document (même empreinte) dans le même dossier."""
        if not self.active("document_en_double"):
            return []
        empreintes = empreintes or {}
        vus: dict[str, list[str]] = {}
        for job_id, empreinte in empreintes.items():
            if empreinte:
                vus.setdefault(empreinte, []).append(job_id)
        constats = []
        for empreinte, jobs in vus.items():
            if len(jobs) > 1:
                constats.append(Constat(
                    rule="document_en_double",
                    severity=WARNING,
                    documents=sorted(jobs),
                    champs=[],
                    valeurs=[{"sha256": empreinte[:16] + "…", "job_ids": jobs}],
                    resultat="doublon",
                    explication=(
                        "même empreinte SHA-256 pour plusieurs documents du "
                        "dossier. Aucune suppression automatique n'est faite : "
                        "c'est à l'utilisateur de décider."
                    ),
                ))
        return constats

    # ───────────────────────────── agrégat ─────────────────────────────

    def _gravite(self, regle: str, defaut: str) -> str:
        return BLOCKING if regle in self.regles_bloquantes else defaut

    def analyser(self, champs: list[ChampDocument],
                 attendus: Optional[dict[str, Iterable[str]]] = None,
                 empreintes: Optional[dict[str, str]] = None) -> list[Constat]:
        """Lance tous les contrôles et renvoie les constats, triés par gravité."""
        constats: list[Constat] = []
        # Chaque règle se garde elle-même (`self.active`), donc une règle
        # désactivée se taît quel que soit l'appelant — pas seulement ici.
        # L'agrégat ne décide plus que *quelles clés* parcourir.
        constats += self.verifie_doublons_documentaires(champs, empreintes)
        for cle in self.cles_reference:
            constats += self.verifie_reference_commune(champs, cle=cle)
        constats += self.verifie_conteneurs(champs)
        constats += self.verifie_poids(champs)
        if attendus:
            for cle, categories in attendus.items():
                constats += self.verifie_reference_absente(champs, cle, categories)
        constats.sort(key=lambda c: -GRAVITES_ORDRE.get(c.severity, 0))
        return constats

    def peut_transmettre(self, constats: list[Constat]) -> tuple[bool, str]:
        """Un constat bloquant non tranché interdit la transmission."""
        for c in constats:
            if c.bloquant and c.status == "a_trancher":
                return False, f"constat bloquant non tranché : {c.rule}"
        return True, ""
