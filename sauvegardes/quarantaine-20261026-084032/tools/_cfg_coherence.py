import io

p = "/home/user/ocr-universal/src/unocr/coherence.py"
src = io.open(p, encoding="utf-8").read()

# ── 1. le moteur reçoit une configuration complète ──
ancien = '''class CoherenceEngine:
    """Moteur de contrôles interdocumentaires, configurable."""

    def __init__(self, regles_bloquantes: Optional[Iterable[str]] = None) -> None:
        self.regles_bloquantes = set(regles_bloquantes or ())
'''
nouveau = '''#: tolérances par défaut, appliquées si la configuration ne les précise pas.
#: Une différence n'est pas une erreur : arrondis de pesée, conversions et
#: écarts légitimes entre documents doivent être tolérés avant d'alerter.
TOLERANCES_DEFAUT = {
    "gross_weight": 0.02,
    "net_weight": 0.02,
    "quantity": 0.05,
    "packages_count": 0.05,
    "amount": 0.01,
    "total_ttc": 0.01,
}

#: clés de référence cherchées par défaut dans les autres pièces
CLES_REFERENCE_DEFAUT = ("invoice_number",)


class CoherenceEngine:
    """Moteur de contrôles interdocumentaires, configurable.

    La configuration vient de `coherence` dans `config/default.json` :

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
'''
assert src.count(ancien) == 1, src.count(ancien)
src = src.replace(ancien, nouveau, 1)
io.open(p, "w", encoding="utf-8").write(src)
print("moteur : configuration complète")
