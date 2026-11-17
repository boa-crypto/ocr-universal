"""Import bancaire, rapprochement et totaux multi-devises sans conversion implicite."""
from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from unocr.backup import creer_sauvegarde, restaurer_sauvegarde
from unocr.business_store import BusinessStore
from unocr.finance import OperationBancaire


def _facture(client, **champs):
    corps = {"dossier_id": "dos_test", "type_facture": "emisee", "numero_facture": "F-1",
             "date_facture": "2026-11-10", "montant_ttc": 100.0, "devise": "EUR"}
    corps.update(champs)
    rep = client.post("/api/frais/facture", json=corps)
    assert rep.status_code == 200, rep.text
    return rep.json()


def test_import_json_deduplique_et_rejette(client_factory):
    with client_factory() as client:
        ops = [
            {"date": "2026-11-11", "montant": "100,00", "devise": "eur", "reference": "VIR F-1",
             "identifiant_externe": "BANQ-1"},
            {"date": "2026-11-12", "montant": -50, "devise": "USD", "libelle": "Paiement fournisseur"},
            {"date": "pas-une-date", "montant": 1},
        ]
        rep = client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": ops})
        assert rep.status_code == 200, rep.text
        assert rep.json()["importees"] == 2
        assert len(rep.json()["rejetees"]) == 1
        again = client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": ops[:2]})
        assert again.json()["importees"] == 0
        assert again.json()["doublons"] == 2
        liste = client.get("/api/frais/banque/operations", params={"dossier_id": "dos_test"}).json()
        assert len(liste) == 2
        assert {op["devise"] for op in liste} == {"EUR", "USD"}


def test_import_csv(client_factory):
    csv = "date;montant;devise;reference;id_banque\n2026-11-11;100,00;EUR;VIR F-1;BANQ-1\n"
    with client_factory() as client:
        rep = client.post("/api/frais/banque/import-csv",
                          data={"dossier_id": "dos_test"},
                          files={"fichier": ("banque.csv", csv.encode("utf-8"), "text/csv")})
        assert rep.status_code == 200, rep.text
        assert rep.json()["importees"] == 1
        assert client.get("/api/frais/banque/operations").json()[0]["montant"] == 100.0


def test_rapprochement_auto_unique_ambigu_et_sans_import(client_factory):
    with client_factory() as client:
        facture = _facture(client)
        sans = client.post("/api/frais/rapprochement/auto", json={
            "dossier_id": "dos_test", "date_debut": "2026-11-01", "date_fin": "2026-11-30"})
        assert sans.status_code == 200
        assert sans.json()["taux_rapprochement"] == 0
        assert sans.json()["operations_disponibles"] == 0

        client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": [
            {"date": "2026-11-11", "montant": 100, "devise": "EUR", "reference": "VIR F-1",
             "identifiant_externe": "BANQ-1"}]})
        rep = client.post("/api/frais/rapprochement/auto", json={
            "dossier_id": "dos_test", "date_debut": "2026-11-01", "date_fin": "2026-11-30"})
        assert rep.json()["rapprochees"][0]["facture_id"] == facture["id"]
        relue = client.get("/api/frais/facture/" + facture["id"]).json()
        assert relue["rapprochee"] is True
        assert relue["statut_paiement"] == "payee"
        assert relue["date_paiement"] == "2026-11-11"

    with client_factory() as client:
        facture = _facture(client, numero_facture="F-2")
        client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": [
            {"date": "2026-11-11", "montant": 100, "devise": "EUR", "identifiant_externe": "BANQ-A"},
            {"date": "2026-11-11", "montant": 100, "devise": "EUR", "identifiant_externe": "BANQ-B"},
        ]})
        rep = client.post("/api/frais/rapprochement/auto", json={
            "dossier_id": "dos_test", "date_debut": "2026-11-01", "date_fin": "2026-11-30"})
        assert rep.json()["rapprochees"] == []
        assert rep.json()["non_rapprochees"][0]["raison"] == "multiples_correspondances"
        assert len(rep.json()["non_rapprochees"][0]["candidats"]) == 2
        assert client.get("/api/frais/facture/" + facture["id"]).json()["rapprochee"] is False


def test_rapprochement_manuel_annulation_et_incompatibilite(client_factory):
    with client_factory() as client:
        facture = _facture(client, type_facture="recue", numero_facture="F-FOU",
                           montant_ttc=50, devise="USD")
        ops = client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": [
            {"date": "2026-11-11", "montant": -50, "devise": "USD", "identifiant_externe": "BANQ-U"},
            {"date": "2026-11-11", "montant": -50, "devise": "EUR", "identifiant_externe": "BANQ-E"},
        ]}).json()["operations"]
        mauvais = client.post("/api/frais/rapprochement/manuel", json={
            "dossier_id": "dos_test", "facture_id": facture["id"], "operation_id": ops[1]})
        assert mauvais.status_code == 422
        ok = client.post("/api/frais/rapprochement/manuel", json={
            "dossier_id": "dos_test", "facture_id": facture["id"], "operation_id": ops[0],
            "motif": "Pointage manuel"})
        assert ok.status_code == 200, ok.text
        assert client.post("/api/frais/rapprochement/manuel", json={
            "dossier_id": "dos_test", "facture_id": facture["id"], "operation_id": ops[0]}).status_code == 409
        annule = client.post("/api/frais/rapprochement/annuler", json={
            "dossier_id": "dos_test", "facture_id": facture["id"], "motif": "Erreur de pointage"})
        assert annule.status_code == 200
        relue = client.get("/api/frais/facture/" + facture["id"]).json()
        assert relue["rapprochee"] is False
        assert relue["statut_paiement"] == "en_attente"


def test_resume_multi_devises_non_consolide(client_factory):
    with client_factory() as client:
        client.post("/api/frais", json={"dossier_id": "dos_test", "montant": 10, "devise": "EUR"})
        client.post("/api/frais", json={"dossier_id": "dos_test", "montant": 20, "devise": "USD"})
        client.post("/api/frais/facture", json={"dossier_id": "dos_test", "type_facture": "emisee",
                                                "montant_ttc": 100, "devise": "EUR"})
        resume = client.get("/api/frais/dossier/dos_test/resume").json()
        assert resume["consolide"] is False
        assert resume["total_frais"] is None
        assert resume["par_devise"]["EUR"]["total_frais"] == 10
        assert resume["par_devise"]["USD"]["total_frais"] == 20
        assert "avertissement" in resume


def test_resume_mono_devise_arrondi_decimal(client_factory):
    with client_factory() as client:
        client.post("/api/frais", json={"dossier_id": "dos_test", "montant": 0.1, "devise": "EUR"})
        client.post("/api/frais", json={"dossier_id": "dos_test", "montant": 0.2, "devise": "EUR"})
        resume = client.get("/api/frais/dossier/dos_test/resume").json()
        assert resume["consolide"] is True
        assert resume["total_frais"] == 0.3
        assert resume["devise"] == "EUR"


@pytest.mark.parametrize("montant", [None, True, "NaN", "Infinity", "-Infinity", "1e3",
                                     "1,234", "12.345", "1.2.3", "1,2,3", "", "12,34,56"])
def test_import_rejette_montants_invalides_sans_rien_ecrire(client_factory, montant):
    with client_factory() as client:
        rep = client.post("/api/frais/banque/import", json={
            "dossier_id": "dos_test", "operations": [
                {"date": "2026-11-11", "montant": montant, "identifiant_externe": "BAD"}]})
        assert rep.status_code == 200, rep.text
        assert rep.json()["importees"] == 0
        assert rep.json()["rejetees"][0]["ligne"] == 0
        assert client.get("/api/frais/banque/operations").json() == []


@pytest.mark.parametrize("montant,attendu", [
    ("1 234,56", 1234.56), ("1\u202f234,56", 1234.56), ("1,234.56", 1234.56),
    ("1.234,56", 1234.56), ("(50,25)", -50.25), ("0", 0),
])
def test_import_formats_montants_non_ambigus(client_factory, montant, attendu):
    with client_factory() as client:
        rep = client.post("/api/frais/banque/import", json={
            "dossier_id": "dos_test", "operations": [
                {"date": "2026-11-11", "montant": montant, "identifiant_externe": "FMT"}]})
        assert rep.status_code == 200 and rep.json()["importees"] == 1, rep.text
        assert client.get("/api/frais/banque/operations").json()[0]["montant"] == attendu


def test_identifiant_externe_conflitant_rejette_pas_doublon_silencieux(client_factory):
    with client_factory() as client:
        premiere = client.post("/api/frais/banque/import", json={
            "dossier_id": "dos_test", "operations": [
                {"date": "2026-11-11", "montant": 100, "identifiant_externe": "BANQ-1"}]})
        assert premiere.json()["importees"] == 1
        conflit = client.post("/api/frais/banque/import", json={
            "dossier_id": "dos_test", "operations": [
                {"date": "2026-11-11", "montant": 999, "identifiant_externe": "BANQ-1"}]})
        assert conflit.json()["importees"] == 0 and conflit.json()["doublons"] == 0
        assert conflit.json()["rejetees"][0]["statut"] == 409
        assert client.get("/api/frais/banque/operations").json()[0]["montant"] == 100


def test_csv_colonnes_dupliquees_et_surnumeraires_refusees(client_factory):
    with client_factory() as client:
        dup = client.post("/api/frais/banque/import-csv", data={"dossier_id": "dos_test"},
                          files={"fichier": ("b.csv", b"date;montant;amount\n2026-11-11;1;2\n", "text/csv")})
        assert dup.status_code == 422
        trop = client.post("/api/frais/banque/import-csv", data={"dossier_id": "dos_test"},
                           files={"fichier": ("b.csv", b"date,montant\n2026-11-11,1,2\n", "text/csv")})
        assert trop.status_code == 422
        assert client.get("/api/frais/banque/operations").json() == []


def _pointer(client, statut="envoyee", reference="REF-ANTERIEURE", date="2026-11-09"):
    facture = _facture(client, statut_paiement=statut)
    # L'API de création historique ne porte pas ces champs : on les pose via PUT.
    assert client.put("/api/frais/facture/" + facture["id"], json={
        "statut_paiement": statut}).status_code == 200
    ops = client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": [
        {"date": "2026-11-11", "montant": 100, "devise": "EUR", "reference": "VIR F-1",
         "identifiant_externe": "BANQ-1"}]}).json()["operations"]
    lie = client.post("/api/frais/rapprochement/manuel", json={
        "dossier_id": "dos_test", "facture_id": facture["id"], "operation_id": ops[0]})
    assert lie.status_code == 200, lie.text
    return facture["id"], ops[0]


def test_facture_pointee_protegee_puis_annulation_restaure(client_factory):
    with client_factory() as client:
        facture_id, operation_id = _pointer(client)
        url = "/api/frais/facture/" + facture_id
        for champs in ({"montant_ttc": 200}, {"devise": "USD"}, {"dossier_id": "dos_autre"},
                       {"type_facture": "recue"}, {"statut_paiement": "annulee"},
                       {"numero_facture": "F-AUTRE"}, {"date_facture": "2026-11-12"}):
            assert client.put(url, json=champs).status_code == 409, champs
        assert client.delete(url).status_code == 409
        assert client.put(url, json={"notes": "Note libre"}).status_code == 200
        relue = client.get(url).json()
        assert relue["montant_ttc"] == 100 and relue["dossier_id"] == "dos_test"
        assert relue["rapprochee"] is True
        annule = client.post("/api/frais/rapprochement/annuler", json={
            "dossier_id": "dos_test", "facture_id": facture_id, "motif": "Erreur"})
        assert annule.status_code == 200
        relue = client.get(url).json()
        assert relue["statut_paiement"] == "envoyee"
        assert relue["reference_paiement"] == ""
        assert relue["date_paiement"] is None
        assert relue["operation_bancaire_id"] is None
        operation = client.get("/api/frais/banque/operations").json()[0]
        assert operation["statut"] == "non_rapprochee" and operation["facture_id"] is None
        assert operation["paiement_facture_avant"] is None
        assert client.put(url, json={"montant_ttc": 120}).status_code == 200
        assert client.delete(url).status_code == 200


def test_auto_score_insuffisant_et_taux_sur_toutes_factures(client_factory):
    with client_factory() as client:
        faible = _facture(client, numero_facture="F-LOW", date_facture="2026-01-01")
        client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": [
            {"date": "2026-11-11", "montant": 100, "devise": "EUR", "identifiant_externe": "LOW"}]})
        rep = client.post("/api/frais/rapprochement/auto", json={
            "dossier_id": "dos_test", "date_debut": "2026-11-01", "date_fin": "2026-11-30"}).json()
        assert rep["rapprochees"] == []
        assert rep["non_rapprochees"][0]["raison"] == "indice_insuffisant"
        assert client.get("/api/frais/facture/" + faible["id"]).json()["rapprochee"] is False
        forte = _facture(client, numero_facture="F-HIGH")
        client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": [
            {"date": "2026-11-11", "montant": 100, "devise": "EUR", "reference": "F-HIGH",
             "identifiant_externe": "HIGH"}]})
        rep = client.post("/api/frais/rapprochement/auto", json={
            "dossier_id": "dos_test", "date_debut": "2026-11-01", "date_fin": "2026-11-30"}).json()
        assert [x["facture_id"] for x in rep["rapprochees"]] == [forte["id"]]
        assert rep["total_factures"] == 2 and rep["taux_rapprochement"] == 0.5
        again = client.post("/api/frais/rapprochement/auto", json={
            "dossier_id": "dos_test", "date_debut": "2026-11-01", "date_fin": "2026-11-30"}).json()
        assert again["deja_rapprochees"] == 1 and again["taux_rapprochement"] == 0.5


def test_resume_dossier_vide_explicite(client_factory):
    with client_factory() as client:
        resume = client.get("/api/frais/dossier/dos_test/resume").json()
        assert resume["vide"] is True and resume["devises"] == []
        assert resume["consolide"] is False and resume["total_frais"] is None
        assert resume["devise"] is None
        assert "Aucun frais" in resume["avertissement"]


def test_rollback_panier_si_ecriture_operation_echoue(client_factory, tmp_path, monkeypatch):
    with client_factory() as client:
        facture = _facture(client)
        ops = client.post("/api/frais/banque/import", json={"dossier_id": "dos_test", "operations": [
            {"date": "2026-11-11", "montant": 100, "reference": "F-1", "identifiant_externe": "B1"}]
        }).json()["operations"]
        original = BusinessStore.__setitem__

        def panne(self, cle, valeur):
            if self.collection == "operation_bancaire":
                raise sqlite3.OperationalError("panne simulée")
            return original(self, cle, valeur)

        monkeypatch.setattr(BusinessStore, "__setitem__", panne)
        with pytest.raises(sqlite3.OperationalError, match="panne simulée"):
            client.post("/api/frais/rapprochement/manuel", json={
                "dossier_id": "dos_test", "facture_id": facture["id"], "operation_id": ops[0]})
        assert client.get("/api/frais/facture/" + facture["id"]).json()["rapprochee"] is False
        assert client.get("/api/frais/banque/operations").json()[0]["statut"] == "non_rapprochee"


def test_sauvegarde_restore_pointage_et_snapshot(client_factory, tmp_path):
    cfg = SimpleNamespace(data_dir=tmp_path, log_dir=tmp_path / "logs")
    with client_factory() as client:
        facture_id, operation_id = _pointer(client, statut="payee")
        sauvegarde = creer_sauvegarde(cfg, destination=tmp_path / "sauvegardes")
        assert client.post("/api/frais/rapprochement/annuler", json={
            "dossier_id": "dos_test", "facture_id": facture_id, "motif": "Test"}).status_code == 200
        restaurer_sauvegarde(cfg, sauvegarde.chemin, force=True)
    with client_factory() as client:
        facture = client.get("/api/frais/facture/" + facture_id).json()
        assert facture["rapprochee"] is True and facture["operation_bancaire_id"] == operation_id
        operation = client.get("/api/frais/banque/operations").json()[0]
        assert operation["facture_id"] == facture_id
        assert operation["paiement_facture_avant"]["statut_paiement"] == "payee"
        assert client.delete("/api/frais/facture/" + facture_id).status_code == 409
    restaure = BusinessStore(tmp_path / "metier.sqlite3", "operation_bancaire", OperationBancaire)
    assert restaure[operation_id].paiement_facture_avant is not None
