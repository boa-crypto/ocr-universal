"""Calibration des scores de confiance (A2).

**Le problème.** La confiance brute d'un moteur OCR n'est pas une probabilité :
Tesseract peut annoncer 0,85 pour une valeur fausse une fois sur trois. Les
seuils de révision (`min_confidence_review`) et les badges de l'interface
deviennent alors trompeurs.

**La solution implémentée ici.** Mapper la confiance brute vers une probabilité
estimée, apprise sur des données *étiquetées* (valeur extraite comparée à la
vérité terrain) :

- **Platt** (régression logistique sur une variable) : robuste avec peu
  d'échantillons, toujours défini ;
- **isotonic** (régression monotone par paliers) : plus fidèle quand il y a
  assez d'échantillons, activé automatiquement au-delà de `ISOTONIC_MIN`.

**Garde-fou d'honnêteté (non négociable).** Un ajustement appris sur des
échantillons *synthétiques* n'est pas validé sur des photos réelles. Il est
donc enregistré et appliqué, mais **jamais activé implicitement** : `active`
reste `False` tant que l'ajustement provient d'une suite synthétique. Il faut
`force=True` (ou un corpus réel) pour l'activer. La provenance (méthode, nombre
d'échantillons, caractère synthétique, date) est exposée par l'API afin que
l'interface puisse l'afficher.

Le module ne modifie jamais une valeur extraite : il ne produit qu'un score.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

from .logging_setup import get_logger

log = get_logger("calibration")

ISOTONIC_MIN = 200        # en dessous, Platt est plus fiable que l'isotonique
PLATT_MIN = 8             # en dessous, on refuse d'ajuster (pas de signal)
CALIBRATION_FILE = "calibration.json"


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


# ───────────────────────────── ajustement ─────────────────────────────

def fit_platt(pairs: list[tuple[float, bool]], iters: int = 300,
              lr: float = 0.5) -> tuple[float, float]:
    """Ajuste p = sigmoid(A·s + B) par descente de gradient (log-vraisemblance).

    `pairs` : [(score brut, est correct)]. Renvoie (A, B).
    Déterministe (pas d'aléa), donc testable.
    """
    if not pairs:
        return 1.0, 0.0
    A, B = 1.0, 0.0
    n = len(pairs)
    for _ in range(iters):
        gA = gB = 0.0
        for s, ok in pairs:
            p = _sigmoid(A * s + B)
            err = p - (1.0 if ok else 0.0)
            gA += err * s
            gB += err
        # pas inversement proportionnel à n pour rester stable
        A -= lr * gA / n
        B -= lr * gB / n
    return A, B


def fit_isotonic(pairs: list[tuple[float, bool]], bins: int = 10) -> list[tuple[float, float]]:
    """Régression isotonique par paliers (PAVA) → [(borne haute, proba)].

    Renvoie des paliers croissants en score, à probabilités non décroissantes.
    """
    if not pairs:
        return [(1.0, 0.5)]
    data = sorted(pairs)
    lo, hi = data[0][0], data[-1][0]
    if hi - lo < 1e-9:
        return [(hi, sum(1 for _, ok in data if ok) / len(data))]

    # 1. moyenne par palier de score
    buckets: list[list[int]] = [[] for _ in range(bins)]
    for s, ok in data:
        idx = int((s - lo) / (hi - lo) * bins)
        idx = max(0, min(bins - 1, idx))
        buckets[idx].append(1 if ok else 0)
    means = [(sum(b) / len(b), len(b)) for b in buckets if b]

    # 2. PAVA : fusion des paliers qui violent la monotonie
    stack: list[tuple[float, int]] = []
    for m, cnt in means:
        stack.append((m, cnt))
        while len(stack) > 1 and stack[-2][0] > stack[-1][0]:
            m2, c2 = stack.pop()
            m1, c1 = stack.pop()
            stack.append(((m1 * c1 + m2 * c2) / (c1 + c2), c1 + c2))

    edges, prev = [], 0.0
    for i in range(len(stack)):
        hi_edge = lo + (hi - lo) * (i + 1) / len(stack)
        prev = round(min(1.0, max(0.0, stack[i][0])), 4)
        edges.append((round(hi_edge, 4), prev))
    return edges


# ───────────────────────────── calibreur ─────────────────────────────

@dataclass
class Calibration:
    """Courbe de calibration persistée. Identité par défaut (sans effet)."""
    method: str = "identity"          # identity | platt | isotonic
    a: float = 1.0                    # Platt
    b: float = 0.0                    # Platt
    steps: list[tuple[float, float]] = field(default_factory=list)  # isotonique
    n_samples: int = 0
    n_positive: int = 0
    synthetic: bool = True            # True = pas de photos réelles
    active: bool = False              # appliqué seulement si True
    fitted_at: float = 0.0
    note: str = ""

    # ── application ──
    def apply(self, raw: float) -> float:
        """Probabilité estimée pour un score brut. Borne [0, 1]."""
        if not self.active:
            return max(0.0, min(1.0, raw))
        if self.method == "platt":
            p = _sigmoid(self.a * raw + self.b)
        elif self.method == "isotonic":
            p = 0.0
            for edge, proba in self.steps:
                p = proba
                if raw <= edge:
                    break
        else:
            p = raw
        return round(max(0.0, min(1.0, p)), 4)

    # ── ajustement ──
    def fit(self, pairs: list[tuple[float, bool]], force: bool = False,
            synthetic: bool = True) -> dict:
        """Ajuste la courbe. Renvoie un dictionnaire de diagnostic.

        Garde-fous : trop peu d'échantillons → identité ; suite synthétique →
        ajusté mais inactif sauf `force`.
        """
        n = len(pairs)
        if n < PLATT_MIN:
            self.method, self.active = "identity", False
            self.n_samples = n
            self.note = (f"{n} échantillon(s) étiqueté(s) : insuffisant "
                         f"(minimum {PLATT_MIN}) — calibration non appliquée")
            log.warning("calibration ignorée : %s", self.note)
            return {"method": "identity", "n_samples": n, "active": False,
                    "note": self.note}

        pos = sum(1 for _, ok in pairs if ok)
        self.n_samples, self.n_positive = n, pos
        self.fitted_at = time.time()
        self.synthetic = synthetic

        if n >= ISOTONIC_MIN:
            self.method = "isotonic"
            self.steps = fit_isotonic(pairs)
            self.note = (f"isotonique sur {n} échantillons "
                         f"({pos} corrects)")
        else:
            self.method = "platt"
            self.a, self.b = fit_platt(pairs)
            self.note = (f"Platt sur {n} échantillons ({pos} corrects)")

        if synthetic and not force:
            self.active = False
            self.note += (" — ajusté sur données SYNTHÉTIQUES : "
                          "désactivé par prudence (relancer avec force=True "
                          "ou fournir des photos réelles)")
            log.warning("calibration synthétique non activée : %s", self.note)
        else:
            self.active = True
        return self.diagnostic()

    # ── persistance ──
    def diagnostic(self) -> dict:
        return {"method": self.method, "active": self.active,
                "n_samples": self.n_samples, "n_positive": self.n_positive,
                "synthetic": self.synthetic, "note": self.note,
                "fitted_at": self.fitted_at}

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.__dict__, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "Calibration":
        p = Path(path)
        if not p.is_file():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            steps = [tuple(s) for s in data.pop("steps", [])]
            obj = cls(**{k: v for k, v in data.items()
                         if k in cls.__dataclass_fields__})
            obj.steps = steps
            return obj
        except (json.JSONDecodeError, TypeError, ValueError):
            log.exception("calibration illisible (%s) : identité utilisée", p)
            return cls()


# ─────────────────── collecte des paires étiquetées ───────────────────

def _norm(s: str) -> str:
    return " ".join((s or "").split())


def collect_pairs(samples_dir: Path, gt_path: Path,
                  quality_mode: str = "fast") -> tuple[list[tuple[float, bool]], dict]:
    """Extrait les champs des échantillons étiquetés et compare à la vérité.

    Renvoie (paires [(confiance brute, est exact)], métadonnées de la suite).
    Réutilise le pipeline complet : aucune valeur n'est inventée.
    """
    from .models import JobOptions
    from .pipeline import Pipeline

    gt = json.loads(Path(gt_path).read_text(encoding="utf-8"))
    pipeline = Pipeline()
    pairs: list[tuple[float, bool]] = []
    files = 0
    for fname, expect in sorted(gt.items()):
        path = Path(samples_dir) / fname
        if not path.is_file():
            continue
        files += 1
        try:
            res = pipeline.process_file(
                path, JobOptions(profile=expect.get("profile", "generic"),
                                 quality_mode=quality_mode))
        except Exception:
            log.exception("échec du traitement de %s", fname)
            continue
        for key, want in (expect.get("fields") or {}).items():
            fv = res.fields.get(key)
            got = _norm(fv.normalized_value or fv.raw_value or "") if fv else ""
            exact = got.replace(" ", "") == _norm(want).replace(" ", "")
            conf = (fv.engine_confidence if fv else 0.0) or 0.0
            pairs.append((round(conf, 4), exact))
    meta = {"suite": "synthétique" if gt and all(v.get("synthetic")
                                                 for v in gt.values()) else "réelle",
            "files": files, "pairs": len(pairs)}
    return pairs, meta
