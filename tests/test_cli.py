"""Tests de la ligne de commande `unocr`.

**Pourquoi ce fichier existe.** Le CLI n'était couvert par aucun test : les
occurrences de « cli » dans les autres fichiers de tests correspondaient en fait
à `client` (le TestClient FastAPI). La commande `unocr process` — qui vient
d'être rebranchée sur le helper partagé `ingest.page_images()` — n'avait donc
jamais été exécutée par une suite.

Ces tests restent volontairement courts : un document PDF à texte natif
(rapide, sans OCR lourd) suffit à prouver que le chemin complet fonctionne.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SRC = RACINE / "src"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    # Pour Windows, on modifie PATH pour inclure le répertoire courant si nécessaire,
    # mais surtout on ajuste PYTHONPATH pour le système actuel.
    env = {
        "PYTHONPATH": str(SRC),
        "PATH": os.environ.get("PATH", "")
    }
    return subprocess.run(
        [sys.executable, "-m", "unocr.cli", *args],
        capture_output=True, text=True, cwd=RACINE, env=env, timeout=600,
    )


def test_process_genere_un_json_lisible(tmp_path: Path) -> None:
    """`unocr process` doit produire un JSON de synthèse sur la sortie standard."""
    pdf = FIXTURES / "text_pdf.pdf"
    assert pdf.exists(), f"fixture manquante : {pdf}"
    r = _run_cli("process", str(pdf), "--out", str(tmp_path), "--export", "json")
    assert r.returncode == 0, f"code {r.returncode}\n{r.stdout}\n{r.stderr}"
    resume = json.loads(r.stdout)
    assert resume["source"].endswith("text_pdf.pdf")
    assert resume["pages"] >= 1
    assert "exports" in resume and resume["exports"], "aucun export produit"
    # le fichier JSON existe réellement sur le disque
    for p in resume["exports"]:
        assert Path(p).exists(), f"export annoncé mais absent : {p}"


def test_process_utilise_le_helper_dimages_partage(tmp_path: Path) -> None:
    """L'export PDF doit être produit : il passe par `ingest.page_images()`.

    C'est le contrat du helper partagé — si le CLI ne l'appelle plus, l'export
    PDF perd ses pages image sans le dire.
    """
    pdf = FIXTURES / "text_pdf.pdf"
    r = _run_cli("process", str(pdf), "--out", str(tmp_path),
                 "--export", "json,pdf")
    assert r.returncode == 0, f"code {r.returncode}\n{r.stderr}"
    resume = json.loads(r.stdout)
    produits = [Path(p).name for p in resume["exports"]]
    assert any(n.endswith(".pdf") for n in produits), (
        f"aucun PDF produit, exports = {produits}"
    )


def test_process_refuse_un_fichier_absent(tmp_path: Path) -> None:
    """Un chemin inexistant doit échouer proprement, pas planter en traceback."""
    r = _run_cli("process", str(tmp_path / "inexistant.pdf"), "--out", str(tmp_path))
    assert r.returncode != 0
    assert "Traceback" not in r.stderr, "échec non géré : traceback brut"


def test_diagnose_renvoie_un_rapport_json() -> None:
    r = _run_cli("diagnose")
    assert r.returncode == 0, f"code {r.returncode}\n{r.stderr}"
    rapport = json.loads(r.stdout)
    assert "os" in rapport and "engines" in rapport
    assert isinstance(rapport["engines"], list)


def test_le_helper_page_images_est_robuste() -> None:
    """`page_images()` renvoie {} et ne lève pas sur un document illisible."""
    from unocr.ingest import page_images

    assert page_images(FIXTURES / "absent.pdf") == {}
    assert page_images(FIXTURES / "corrupt.pdf") == {}
