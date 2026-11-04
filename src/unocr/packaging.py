"""Génération du paquet de données (étape 13 du parcours).

**Pourquoi ce module existe.** `exporters.export_all()` produit les exports d'un
document **seul**. Le parcours exige un paquet de **dossier** : plusieurs
documents, une feuille de synthèse, une feuille par catégorie, les champs
validés séparés des champs en attente, les anomalies, les métadonnées — et un
manifeste qui dise exactement ce qui est dedans et ce qui manque.

**Ce qu'il fait.** Il produit, à partir des résultats déjà calculés :
- `paquet.xlsx` : synthèse + une feuille par catégorie + validés + en attente +
  anomalies + métadonnées ;
- `paquet.json` : la même chose, structurée, pour une machine ;
- `paquet.zip` : les deux + un `manifeste.json` + les documents originaux
  autorisés (option explicite, jamais par défaut).

**Ce qu'il ne fait pas.** Il ne mélange **jamais** une valeur validée par un
humain avec une proposition automatique : deux feuilles distinctes, et une
colonne `origine` qui dit d'où vient la valeur. Il ne convertit pas les
identifiants en nombres (zéro initial préservé), et il n'inclut aucun document
dans le ZIP si l'appelant ne l'a pas demandé explicitement.
"""
from __future__ import annotations

import json
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .logging_setup import audit, get_logger

log = get_logger("packaging")

#: version du schéma du paquet — à incrémenter à toute rupture de format
SCHEMA_VERSION = "1.0"


@dataclass
class DocumentPaquet:
    """Ce qu'un document apporte au paquet (déjà calculé en amont)."""
    job_id: str
    filename: str
    category: str = "unknown"
    category_label: str = ""
    champs: dict[str, dict[str, Any]] = field(default_factory=dict)
    # chaque champ : {"valeur": ..., "origine": "confirme|corrige|normalise|brut",
    #                 "valide": bool, "page": int, "confiance": float}
    fichiers: list[Path] = field(default_factory=list)   # documents originaux
    sha256: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id, "filename": self.filename,
            "category": self.category, "category_label": self.category_label,
            "champs": {k: {kk: vv for kk, vv in v.items() if kk != "fichiers"}
                       for k, v in self.champs.items()},
            "sha256": self.sha256,
            "fichiers": [f.name for f in self.fichiers],
        }


def _texte(v: Any) -> str:
    """Valeur écrite dans le tableur — toujours du texte.

    Les identifiants et codes (numéro de conteneur, code SH, référence) doivent
    rester des chaînes : `007` ne doit pas devenir `7`.
    """
    if v is None:
        return ""
    return str(v)


def _feuille_champs(ws, documents: list[DocumentPaquet], seulement_valides: bool,
                    seulement_attente: bool) -> int:
    """Écrit une feuille de champs. Renvoie le nombre de lignes écrites."""
    entetes = ["document", "catégorie", "champ", "libellé", "valeur", "origine",
               "validé", "page", "confiance"]
    ws.append(entetes)
    from openpyxl.styles import Font
    for c in ws[1]:
        c.font = Font(bold=True)
    n = 0
    for doc in documents:
        for cle, info in doc.champs.items():
            valide = bool(info.get("valide"))
            if seulement_valides and not valide:
                continue
            if seulement_attente and valide:
                continue
            ws.append([
                _texte(doc.filename), _texte(doc.category_label or doc.category),
                _texte(cle), _texte(info.get("label", "")),
                _texte(info.get("valeur")), _texte(info.get("origine", "")),
                "oui" if valide else "non",
                info.get("page"), info.get("confiance"),
            ])
            n += 1
    return n


def _horodatage(ts) -> str:
    """Timestamp epoch -> date lisible. Un chiffre nu n'informe personne."""
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts)))
    except (TypeError, ValueError):
        return ""


def genere_xlsx(documents: list[DocumentPaquet], out: Path,
                dossier_id: str = "", dossier_label: str = "",
                anomalies: Optional[list[dict]] = None,
                manquants: Optional[list[dict]] = None,
                arbitrages: Optional[list[dict]] = None) -> Path:
    """Paquet Excel : synthèse, une feuille par catégorie, validés, attente,
    anomalies, arbitrages, métadonnées."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    anomalies = anomalies or []
    manquants = manquants or []
    wb = Workbook()

    # ── feuille de synthèse ──
    ws = wb.active
    ws.title = "Synthèse"
    ws.append(["Dossier", dossier_label or dossier_id])
    ws.append(["Identifiant", dossier_id])
    ws.append(["Généré le", time.strftime("%Y-%m-%d %H:%M:%S")])
    ws.append(["Version du schéma", SCHEMA_VERSION])
    ws.append(["Documents", len(documents)])
    valides = sum(1 for d in documents for i in d.champs.values() if i.get("valide"))
    total = sum(len(d.champs) for d in documents)
    ws.append(["Champs validés", f"{valides} / {total}"])
    ws.append(["Pièces manquantes", len(manquants)])
    ws.append(["Anomalies", len(anomalies)])
    for c in ws["A"]:
        c.font = Font(bold=True)

    # ── une feuille par catégorie ──
    par_categorie: dict[str, list[DocumentPaquet]] = {}
    for doc in documents:
        par_categorie.setdefault(doc.category_label or doc.category or "Inconnu",
                                 []).append(doc)
    for categorie, docs in sorted(par_categorie.items()):
        feuille = wb.create_sheet(categorie[:31])
        _feuille_champs(feuille, docs, seulement_valides=False,
                        seulement_attente=False)

    # ── validés / en attente, séparés ──
    feuille_valides = wb.create_sheet("Champs validés")
    _feuille_champs(feuille_valides, documents, seulement_valides=True,
                                seulement_attente=False)
    feuille_attente = wb.create_sheet("Champs en attente")
    n_attente = _feuille_champs(feuille_attente, documents, seulement_valides=False,
                                seulement_attente=True)

    # ── anomalies ──
    feuille_anomalies = wb.create_sheet("Anomalies")
    if anomalies:
        feuille_anomalies.append(["règle", "gravité", "documents", "champs",
                                  "valeurs", "résultat", "explication", "statut"])
        for c in feuille_anomalies[1]:
            c.font = Font(bold=True)
        for a in anomalies:
            feuille_anomalies.append([
                _texte(a.get("rule")), _texte(a.get("severity")),
                _texte(", ".join(a.get("documents", []))),
                _texte(", ".join(str(c.get("key")) for c in a.get("champs", []))),
                _texte(json.dumps(a.get("valeurs"), ensure_ascii=False)),
                _texte(a.get("resultat")), _texte(a.get("explication")),
                _texte(a.get("status")),
            ])
    elif not arbitrages:
        feuille_anomalies.append(["Aucune anomalie détectée."])
    else:
        # Rien ne reste a trancher, mais des anomalies ont existe et un
        # humain les a arbitrées : le classeur doit le dire, sinon
        # l'historique des corrections disparaît du livrable.
        feuille_anomalies.append(
            ["Aucune anomalie non résolue — %d anomalie(s) tranchée(s) par "
             "un humain (feuille « Arbitrages »)." % len(arbitrages)])

    # ── arbitrages humains ──
    feuille_arb = wb.create_sheet("Arbitrages")
    if arbitrages:
        feuille_arb.append(["règle", "statut", "acteur", "motif",
                            "remplace", "horodatage"])
        for c in feuille_arb[1]:
            c.font = Font(bold=True)
        for arb in arbitrages:
            feuille_arb.append([
                _texte(arb.get("rule")), _texte(arb.get("status")),
                _texte(arb.get("acteur")), _texte(arb.get("motif")),
                _texte(arb.get("remplace")), _horodatage(arb.get("ts"))])
    else:
        feuille_arb.append(["Aucun arbitrage humain enregistré."])

    # ── pièces manquantes ──
    feuille_manquantes = wb.create_sheet("Pièces manquantes")
    if manquants:
        feuille_manquantes.append(["catégorie", "libellé", "requise",
                                   "attendues", "présentes"])
        for c in feuille_manquantes[1]:
            c.font = Font(bold=True)
        for m in manquants:
            feuille_manquantes.append([
                _texte(m.get("category")), _texte(m.get("label")),
                "oui" if m.get("required") else "non",
                m.get("expected"), m.get("present"),
            ])
    else:
        feuille_manquantes.append(["Aucune pièce manquante."])

    # ── métadonnées ──
    feuille_meta = wb.create_sheet("Métadonnées")
    feuille_meta.append(["clé", "valeur"])
    for c in feuille_meta[1]:
        c.font = Font(bold=True)
    meta = {
        "dossier_id": dossier_id,
        "dossier_label": dossier_label,
        "genere_le": time.strftime("%Y-%m-%d %H:%M:%S"),
        "schema_version": SCHEMA_VERSION,
        "documents": len(documents),
        "champs_total": total,
        "champs_valides": valides,
        "champs_en_attente": n_attente,
        "anomalies": len(anomalies),
        "pieces_manquantes": len(manquants),
    }
    for k, v in meta.items():
        feuille_meta.append([_texte(k), _texte(v)])

    # largeurs lisibles
    for feuille in wb.worksheets:
        for colonne in range(1, min(feuille.max_column, 10) + 1):
            feuille.column_dimensions[get_column_letter(colonne)].width = 22

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    log.info("paquet Excel généré : %s (%d documents)", out.name, len(documents))
    return out


def genere_json(documents: list[DocumentPaquet], out: Path,
                dossier_id: str = "", dossier_label: str = "",
                anomalies: Optional[list[dict]] = None,
                manquants: Optional[list[dict]] = None,
                arbitrages: Optional[list[dict]] = None) -> Path:
    """Paquet JSON — même contenu que l'Excel, pour une machine."""
    anomalies = anomalies or []
    manquants = manquants or []
    arbitrages = arbitrages or []
    total = sum(len(d.champs) for d in documents)
    valides = sum(1 for d in documents for i in d.champs.values() if i.get("valide"))
    paquet = {
        "schema_version": SCHEMA_VERSION,
        "dossier": {"id": dossier_id, "label": dossier_label},
        "genere_le": time.strftime("%Y-%m-%d %H:%M:%S"),
        "documents": [d.as_dict() for d in documents],
        "champs_valides": valides,
        "champs_total": total,
        "anomalies": anomalies,
        "pieces_manquantes": manquants,
        "arbitrages": arbitrages,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(paquet, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def genere_zip(documents: list[DocumentPaquet], out: Path,
               dossier_id: str = "", dossier_label: str = "",
               anomalies: Optional[list[dict]] = None,
               manquants: Optional[list[dict]] = None,
               inclure_documents: bool = False,
               arbitrages: Optional[list[dict]] = None) -> Path:
    """ZIP = xlsx + json + manifeste (+ documents originaux si demandé).

    `inclure_documents` est **faux par défaut** : embarquer les originaux est
    une décision, pas un effet de bord.
    """
    tmp = out.parent / f".{out.stem}_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        xlsx = genere_xlsx(documents, tmp / "paquet.xlsx", dossier_id,
                           dossier_label, anomalies, manquants, arbitrages)
        jsn = genere_json(documents, tmp / "paquet.json", dossier_id,
                          dossier_label, anomalies, manquants, arbitrages)
        manifeste = {
            "schema_version": SCHEMA_VERSION,
            "dossier": {"id": dossier_id, "label": dossier_label},
            "genere_le": time.strftime("%Y-%m-%d %H:%M:%S"),
            "documents_inclus": [d.as_dict() for d in documents],
            "fichiers": [xlsx.name, jsn.name, "manifeste.json"],
            "documents_originaux_inclus": inclure_documents,
            "anomalies": anomalies,
            "pieces_manquantes": manquants,
            "arbitrages": arbitrages or [],
        }
        (tmp / "manifeste.json").write_text(
            json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")

        fichiers = [xlsx, jsn, tmp / "manifeste.json"]
        if inclure_documents:
            for doc in documents:
                fichiers.extend(doc.fichiers)

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in fichiers:
                if f.is_file():
                    zf.write(f, arcname=f.name)
        return out
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def consigne_paquet(log_dir: Path, dossier_id: str, chemin: Path,
                    nb_documents: int, acteur: str = "systeme") -> None:
    audit(log_dir, "data_package_generated", dossier_id=dossier_id,
          fichier=chemin.name, documents=nb_documents, acteur=acteur)
