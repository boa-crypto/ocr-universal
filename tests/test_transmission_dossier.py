"""Tests de la transmission d'un dossier entier (étape 14).

**Ce que ces tests prouvent.** Un dossier peut partir vers un connecteur
opérationnel, mais jamais à l'aveugle : sans formulaire cible ni règle de
correspondance la transmission est refusée, un dossier incomplet est refusé,
une valeur non validée par un humain est signalée, et « envoyé » n'est jamais
présenté comme « accepté ». Le verrou est dans le module, pas dans
l'interface.
"""
from __future__ import annotations

import pytest

from unocr.connectors.contract import OPERATIONAL_STATES
from unocr.connectors.mapping import MappingRule
from unocr.connectors.simulated import SIMULATED, SimulatedConnector
from unocr.connectors.transmission import TransmissionEngine, TransmissionStatus
from unocr.dossier import DossierStore
from unocr.formulaire import ChampFormulaire, FormulaireDossier, FormulaireStore
from unocr.transmission_dossier import (
    CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS,
    apercu_transmission_dossier,
    transmettre_dossier,
)


@pytest.fixture()
def store(tmp_path):
    return DossierStore(tmp_path / "dossiers", log_dir=tmp_path / "logs")


@pytest.fixture()
def engine(tmp_path):
    SIMULATED.healthy = True
    return TransmissionEngine(tmp_path / "transmissions", tmp_path / "logs")


@pytest.fixture()
def formulaires(tmp_path):
    return FormulaireStore(tmp_path / "formulaires", log_dir=tmp_path / "logs")


class FormStoreFactice:
    """Aucun formulaire déclaré localement : la cible vient du connecteur."""

    def get(self, form_id):
        return None


class HubFactice:
    """Hub minimal : un connecteur simulé opérationnel, ou aucun."""

    def __init__(self, connecteur=None):
        self._c = connecteur

    def list_configured(self):
        return [] if self._c is None else [{"connector_id": "demo_simulated"}]

    def get(self, cid):
        return self._c


def _connecteur_operationnel():
    """Un connecteur réellement opérationnel : configuré **et** testé.

    `configure()` laisse l'état à « à tester ». Un connecteur qui n'a pas
    passé son test de connexion n'est pas opérationnel, et la transmission
    doit le refuser — c'est tout l'enjeu de ce helper.
    """
    c = SimulatedConnector()
    c.configure({})
    c._record_test(c.test_connection())
    assert c.state in OPERATIONAL_STATES, f"non opérationnel : {c.state}"
    return c


def _dossier_complet(store, label="Import 2024-118"):
    """Dossier dont les pièces requises du profil sont présentes.

    Un dossier vide est légitimement refusé à la transmission (pièces
    requises manquantes) : pour tester l'envoi lui-même, il faut un dossier
    complet.
    """
    dossier = store.creer(label, "importation")
    store.ajouter_piece(dossier.id, "job_facture", "facture.pdf",
                        category="invoice")
    store.ajouter_piece(dossier.id, "job_bl", "bl.pdf", category="bill_of_lading")
    return dossier


def _formulaire(dossier_id, champs):
    return FormulaireDossier(formulaire_id=f"frm_{dossier_id}",
                             dossier_id=dossier_id, label="Formulaire",
                             champs=champs)


#: le formulaire que le connecteur simulé expose, et les règles qui y mènent
FORM_CIBLE_ID = "demo_declaration"
REGLES = [
    MappingRule("containerNo", "containerNo", "none"),
    MappingRule("bl_reference", "bl_reference", "none"),
    MappingRule("grossWeight", "grossWeight", "none"),
]


def _formulaire_cible(dossier_id):
    """Formulaire dont les champs couvrent le schéma du système simulé.

    Le connecteur de démonstration exige `containerNo`, `bl_reference` et
    `grossWeight` : un contenu qui ne les porte pas est rejeté — ce qui est
    le comportement attendu, pas un accident de test.
    """
    return _formulaire(dossier_id, [
        ChampFormulaire(key="containerNo", label="N° de conteneur",
                        valeur="TGHU1234567", valide=True),
        ChampFormulaire(key="bl_reference", label="Référence BL",
                        valeur="BL-2024-0456", valide=True),
        ChampFormulaire(key="grossWeight", label="Poids brut",
                        valeur="12000", valide=True),
    ])


def _form_cible():
    """Le schéma tel que le connecteur le expose vraiment."""
    return SimulatedConnector().discover_forms()[0]


# ───────────────── l'aperçu ne transmet rien, et vérifie tout ─────────────────

def test_apercu_ne_cree_aucune_transmission(store, engine):
    dossier = _dossier_complet(store)
    f = _formulaire_cible(dossier.id)
    ap = apercu_transmission_dossier(dossier, store.synthese(dossier), f,
                                     _form_cible(), REGLES)
    assert ap.transmissible
    assert ap.valeurs["containerNo"].value == "TGHU1234567"
    assert engine.list() == [], "construire un aperçu a créé une transmission"


def test_sans_formulaire_cible_la_transmission_est_refusee(store):
    """On ne devine jamais la structure attendue par le système cible.

    Envoyer les clés du dossier telles quelles produirait un rejet, ou pire
    un enregistrement silencieusement faux.
    """
    dossier = _dossier_complet(store)
    f = _formulaire_cible(dossier.id)
    ap = apercu_transmission_dossier(dossier, store.synthese(dossier), f,
                                     None, REGLES)
    assert not ap.transmissible
    assert "formulaire cible" in ap.erreurs[0].message


def test_champ_sans_correspondance_est_refuse(store):
    """Un champ du dossier sans règle de mapping serait perdu en silence."""
    dossier = _dossier_complet(store)
    f = _formulaire_cible(dossier.id)
    ap = apercu_transmission_dossier(dossier, store.synthese(dossier), f,
                                     _form_cible(), REGLES[:1])
    assert not ap.transmissible
    perdus = [i for i in ap.erreurs if i.kind == "unknown_field"]
    assert len(perdus) == 2, "deux champs ne sont pas couverts par la règle"


def test_piece_requise_manquante_bloque(store):
    """Transmettre un dossier incomplet comme s'il était complet est le pire
    des silences : c'est bloqué ici, pas dans l'interface."""
    dossier = store.creer("Import", "importation")
    f = _formulaire_cible(dossier.id)
    ap = apercu_transmission_dossier(dossier, store.synthese(dossier), f,
                                     _form_cible(), REGLES)
    assert not ap.transmissible
    assert any(i.kind == "missing_required" and i.severity == "error"
               for i in ap.issues)


def test_champ_requis_non_rempli_bloque(store):
    dossier = _dossier_complet(store)
    f = _formulaire(dossier.id, [
        ChampFormulaire(key="containerNo", required=True),
        ChampFormulaire(key="bl_reference", valeur="BL-1", valide=True),
        ChampFormulaire(key="grossWeight", valeur="12000", valide=True)])
    ap = apercu_transmission_dossier(dossier, store.synthese(dossier), f,
                                     _form_cible(), REGLES)
    assert not ap.transmissible


def test_valeur_non_validee_avertit_sans_bloquer(store):
    """Une valeur extraite et non validée part, mais elle est signalée :
    l'utilisateur doit savoir qu'elle vient de l'OCR."""
    dossier = _dossier_complet(store)
    f = _formulaire(dossier.id, [
        ChampFormulaire(key="containerNo", valeur="TGHU1234567", valide=False),
        ChampFormulaire(key="bl_reference", valeur="BL-2024-0456", valide=True),
        ChampFormulaire(key="grossWeight", valeur="12000", valide=True)])
    ap = apercu_transmission_dossier(dossier, store.synthese(dossier), f,
                                     _form_cible(), REGLES)
    assert ap.transmissible
    assert any(i.kind == "unvalidated_suggestion" for i in ap.issues)
    # et la valeur est marquée comme non confirmée, donc exclue de l'envoi
    assert ap.valeurs["containerNo"].confidence == "suggested"
    assert ap.contenu["champs"].get("containerNo") is None


def test_anomalie_non_tranchee_avertit(store):
    dossier = _dossier_complet(store)
    f = _formulaire_cible(dossier.id)
    ap = apercu_transmission_dossier(
        dossier, store.synthese(dossier), f, _form_cible(), REGLES,
        anomalies=[{"champ": "grossWeight", "statut": "a_trancher",
                    "message": "12000 vs 11500"}])
    assert ap.transmissible
    assert any(i.kind == "contradiction" for i in ap.avertissements)


def test_dossier_sans_champ_est_refuse(store):
    """Un dossier sans rien à transmettre est refusé, pas envoyé vide."""
    dossier = _dossier_complet(store)
    ap = apercu_transmission_dossier(dossier, store.synthese(dossier), None,
                                     _form_cible(), REGLES)
    assert not ap.transmissible
    assert "aucun champ" in ap.issues[0].message


def test_contenu_ne_contient_pas_les_fichiers(store):
    """Le contenu transmis porte les données, jamais les pièces jointes."""
    dossier = _dossier_complet(store)
    f = _formulaire_cible(dossier.id)
    ap = apercu_transmission_dossier(dossier, store.synthese(dossier), f,
                                     _form_cible(), REGLES)
    assert ap.contenu["fichiers_joints"] is False
    assert ap.contenu["dossier"]["pieces"] == 2
    assert ap.contenu["champs"] == {"containerNo": "TGHU1234567",
                                    "bl_reference": "BL-2024-0456",
                                    "grossWeight": "12000"}


# ───────────────────────── transmission réelle ─────────────────────────

def _transmet(store, engine, formulaires, dossier, risque="low", **kw):
    formulaires.sauve(_formulaire_cible(dossier.id))
    return transmettre_dossier(
        store, engine, HubFactice(_connecteur_operationnel()), dossier.id,
        lambda d: [], formulaires, FormStoreFactice(), form_id=FORM_CIBLE_ID,
        rules=REGLES, risque=risque, confirme=True, **kw)


def test_transmission_reelle_est_envoyee_pas_acceptee(store, engine, formulaires):
    """`SENT` n'est pas `ACCEPTED` : la règle absolue du Connecteur Hub."""
    dossier = _dossier_complet(store)
    res = _transmet(store, engine, formulaires, dossier)
    tx = res["transmission"]
    assert tx["status"] in (TransmissionStatus.SENT.value,
                            TransmissionStatus.ACCEPTED.value)
    assert res["renvoye_evite"] is False
    # le statut reflète la preuve obtenue : pas d'acceptation sans référence
    if tx["status"] == TransmissionStatus.ACCEPTED.value:
        assert tx["reference"]
    assert res["transmission"]["dossier_id"] == dossier.id


def test_transmission_est_tracee_dans_le_dossier(store, engine, formulaires):
    dossier = _dossier_complet(store)
    _transmet(store, engine, formulaires, dossier)
    evenements = [e.action for e in store.get(dossier.id).history]
    assert "transmitted" in evenements
    detail = [e.detail for e in store.get(dossier.id).history
              if e.action == "transmitted"][0]
    assert detail["connector"] == "demo_simulated"
    assert detail["formulaire"] == FORM_CIBLE_ID
    # l'événement porte le rappel : envoyé n'est pas accepté
    assert "accepté" in detail["ne_garantit_pas"]


def test_second_envoi_du_meme_contenu_est_evite(store, engine, formulaires):
    """Idempotence : le second envoi du même contenu n'est pas renvoyé."""
    dossier = _dossier_complet(store)
    r1 = _transmet(store, engine, formulaires, dossier)
    r2 = _transmet(store, engine, formulaires, dossier)
    assert r1["renvoye_evite"] is False
    assert r2["renvoye_evite"] is True
    assert (r1["transmission"]["transmission_id"]
            == r2["transmission"]["transmission_id"])


def test_deux_dossiers_au_contenu_identique_ne_se_confondent_pas(
        store, engine, formulaires):
    """Deux dossiers au contenu identique ont malgré tout des clés distinctes."""
    a = _dossier_complet(store, "Dossier A")
    b = _dossier_complet(store, "Dossier B")
    ra = _transmet(store, engine, formulaires, a)
    rb = _transmet(store, engine, formulaires, b)
    assert (ra["transmission"]["transmission_id"]
            != rb["transmission"]["transmission_id"])
    assert len(engine.list_for_dossier(a.id)) == 1
    assert len(engine.list_for_dossier(b.id)) == 1


def test_aucun_connecteur_operationnel_est_refuse(store, engine, formulaires):
    dossier = _dossier_complet(store)
    formulaires.sauve(_formulaire_cible(dossier.id))
    with pytest.raises(ValueError, match="opérationnel"):
        transmettre_dossier(store, engine, HubFactice(None), dossier.id,
                            lambda d: [], formulaires, FormStoreFactice(),
                            form_id=FORM_CIBLE_ID, rules=REGLES)


def test_dossier_inconnu_est_refuse(store, engine, formulaires):
    with pytest.raises(KeyError):
        transmettre_dossier(store, engine, HubFactice(_connecteur_operationnel()),
                            "dossier_absent", lambda d: [], formulaires,
                            FormStoreFactice(), form_id=FORM_CIBLE_ID,
                            rules=REGLES)


def test_contenu_non_transmissible_est_refuse_par_le_moteur(store, engine,
                                                            formulaires):
    """Le verrou est aussi dans `TransmissionEngine.create()`."""
    dossier = _dossier_complet(store)
    formulaires.sauve(_formulaire_cible(dossier.id))
    # risque moyen sans confirmation → refus attendu
    with pytest.raises(ValueError, match="refusée"):
        transmettre_dossier(store, engine, HubFactice(_connecteur_operationnel()),
                            dossier.id, lambda d: [], formulaires,
                            FormStoreFactice(), form_id=FORM_CIBLE_ID,
                            rules=REGLES, risque="medium", confirme=False)


def test_reponse_porte_ce_que_la_transmission_ne_garantit_pas(store, engine,
                                                              formulaires):
    dossier = _dossier_complet(store)
    res = _transmet(store, engine, formulaires, dossier)
    assert res["ne_garantit_pas"] == CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS
    assert any("accepté" in g for g in res["ne_garantit_pas"])


def test_aucune_garantie_ne_promet_l_acceptation() -> None:
    """Test de vocabulaire : ce qui est listé doit rester des limites."""
    texte = " ".join(CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS).lower()
    assert "garantit l'acceptation" not in texte
    assert "prouve que le dossier a été accepté" not in texte
    assert "n'est pas « accepté »" in texte
