"""Un rôle « lecteur » ne doit écrire nulle part — et le refus est tracé.

**Pourquoi ce fichier existe.** La politique centrale (`_role_requis`) exige au
moins `operateur` sur toute écriture, et `administrateur` sur l'administration.
Cette règle n'était vérifiée qu'à la main, sur un serveur isolé : une
réutilisation pourrait la faire tomber sans que rien ne le signale. Ici, on
l'exerce **famille d'écriture par famille d'écriture**.

Deux principes de mesure :

* les charges envoyées sont **invalides** (ou les identifiants inexistants) :
  un refus de validation (4xx autre que 403) prouve que l'autorisation est
  passée **sans rien écrire** ;
* le registre RBAC vit dans un répertoire temporaire : le poste de travail
  n'est jamais cloisonné par ces tests.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from unocr import api as api_module
from unocr.api import app

JETON_LECTEUR = "jeton-lecteur"
JETON_OPERATEUR = "jeton-operateur"


@pytest.fixture()
def cloisonne(tmp_path, monkeypatch):
    """Registre RBAC actif dans un répertoire de données jetable."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "rbac.json").write_text(json.dumps({
        "utilisateurs": [
            {"nom": "lectrice", "jeton": JETON_LECTEUR, "roles": ["lecteur"],
             "dossiers": ["*"]},
            {"nom": "operateur", "jeton": JETON_OPERATEUR, "roles": ["operateur"],
             "dossiers": ["*"]},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("UNOCR_DATA_DIR", str(data))
    monkeypatch.setenv("UNOCR_LOG_DIR", str(tmp_path / "logs"))
    api_module._recharge_rbac()
    assert api_module._rbac.actif is True
    yield TestClient(app), tmp_path / "logs"
    monkeypatch.delenv("UNOCR_DATA_DIR", raising=False)
    monkeypatch.delenv("UNOCR_LOG_DIR", raising=False)
    api_module._recharge_rbac()


#: (méthode, url, corps) — une écriture par famille d'écran.
ECRITURES = [
    ("POST", "/api/clients", {"name": "Test RBAC"}),
    ("DELETE", "/api/clients/cli_inexistant", None),
    ("POST", "/api/fournisseurs", {"nom": "Fournisseur RBAC",
                                   "nom_commercial": "FR" }),
    ("POST", "/api/referentiels/pays", {"libelle": "Pays RBAC", "code": "ZZ"}),
    ("PUT", "/api/parametres/max_pages", {"valeur": 10}),
    ("POST", "/api/dossiers", {"label": "Dossier RBAC"}),
    ("POST", "/api/frais", {"dossier_id": "dos_x", "libelle": "Frais RBAC"}),
    ("PATCH", "/api/jobs/job_x/fields/date", {"confirmed_value": "2024-01-01"}),
    ("POST", "/api/jobs/job_x/retry", None),
    ("POST", "/api/rbac/utilisateurs", {"nom": "intrus", "roles": ["lecteur"]}),
    ("DELETE", "/api/rbac/utilisateurs/lectrice", None),
    ("POST", "/api/admin/cleanup", None),
    ("POST", "/api/connectors/demo_simulated/test", None),
    ("POST", "/api/backups", None),
]


@pytest.mark.parametrize("methode,url,corps", ECRITURES)
def test_lecteur_ne_peut_pas_ecrire(cloisonne, methode, url, corps):
    client, journal = cloisonne
    reponse = client.request(methode, url, json=corps,
                             headers={"Authorization": f"Bearer {JETON_LECTEUR}"})
    assert reponse.status_code == 403, (url, reponse.status_code, reponse.text[:120])
    assert "rôle" in reponse.json()["detail"].lower()

    # le refus est tracé : un refus muet ne se distingue pas d'un bug
    contenu = (journal / "audit.log").read_text(encoding="utf-8")
    assert "acces_refuse_role" in contenu
    assert "lectrice" in contenu


def test_lecteur_peut_lire(cloisonne):
    client, _ = cloisonne
    for url in ("/api/health", "/api/stats", "/api/clients", "/api/parametres"):
        reponse = client.get(url, headers={"Authorization": f"Bearer {JETON_LECTEUR}"})
        assert reponse.status_code == 200, url


def test_operateur_ecrit_mais_reste_refuse_sur_l_administration(cloisonne):
    """L'opérateur passe l'autorisation d'écriture, pas celle d'administration.

    La charge est volontairement invalide : un 422 (validation) montre que le
    contrôle de rôle a laissé passer, sans écrire quoi que ce soit.
    """
    client, _ = cloisonne
    entete = {"Authorization": f"Bearer {JETON_OPERATEUR}"}

    valide = client.put("/api/parametres/max_pages", json={"valeur": 10},
                        headers=entete)
    # paramètres = administration ; refus attendu même pour un opérateur
    assert valide.status_code == 403

    champs = client.patch("/api/jobs/job_x/fields/date",
                          json={"confirmed_value": "2024-01-01"}, headers=entete)
    assert champs.status_code != 403, champs.text[:120]

    admin = client.post("/api/rbac/utilisateurs", json={"nom": "x"},
                        headers=entete)
    assert admin.status_code == 403


def test_jeton_inconnu_renvoie_401(cloisonne):
    client, _ = cloisonne
    reponse = client.get("/api/clients", headers={"Authorization": "Bearer inconnu"})
    assert reponse.status_code == 401
    assert "jeton inconnu" in reponse.json()["detail"]


def test_hors_rbac_les_ecritures_ne_sont_pas_fermees():
    """Comportement historique : sans fichier de rôles, rien ne se ferme.

    C'est la garantie de compatibilité — et c'est aussi pourquoi ces tests
    installent leur propre registre plutôt que de compter sur le poste.
    """
    assert api_module._rbac.actif is False
    client = TestClient(app)
    reponse = client.put("/api/parametres/max_pages", json={"valeur": "pas un entier"})
    assert reponse.status_code == 422          # validé, pas refusé
