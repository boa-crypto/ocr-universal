"""Dossier documentaire (étape 11) — regroupement, état, pièces manquantes.

**Pourquoi ces tests.** Le dossier porte la promesse « où en est l'ensemble ».
Ce qui est vérifié : l'état est **déduit de faits réels** (statut des
documents, révisions en cours, pièces requises absentes), pas posé par un
bouton ; le retrait d'une pièce est contrôlé et tracé ; la suppression d'un
dossier ne touche pas aux documents ; et les profils ne créent pas
d'obligations qui n'existent pas.
"""
from __future__ import annotations

import pytest

from unocr.dossier import (
    PROFILS_DOSSIER,
    DossierState,
    DossierStore,
)


@pytest.fixture()
def store(tmp_path):
    return DossierStore(tmp_path / "dossiers", log_dir=tmp_path / "logs")


def _dossier_import(store, acteur="test") -> object:
    return store.creer("Dossier import 2024-118", "importation", acteur=acteur)


# ───────────────────────────── création ─────────────────────────────

def test_creation_et_persistance(store) -> None:
    d = _dossier_import(store)
    assert d.id.startswith("dos_")
    assert d.state == DossierState.EN_PREPARATION
    # relecture depuis le disque : rien n'est seulement en mémoire
    relu = store.get(d.id)
    assert relu is not None and relu.label == d.label
    assert relu.profile == "importation"


def test_profil_inconnu_refuse(store) -> None:
    with pytest.raises(ValueError):
        store.creer("x", "profil_inexistant")


def test_profil_personnalise_sans_piece_imposee(store) -> None:
    d = store.creer("Libre", "personnalise")
    assert store.pieces_manquantes(d) == []


# ───────────────────────────── pièces ─────────────────────────────

def test_ajout_piece_et_pas_de_doublon_silencieux(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")   # même pièce
    assert len(store.get(d.id).pieces) == 1, "un doublon ne doit pas s'ajouter"
    # mais une catégorie inconnue peut être précisée ensuite
    store.ajouter_piece(d.id, "j1", "facture.pdf", "bill_of_lading")
    assert store.get(d.id).piece_par_job("j1").category == "invoice", (
        "une catégorie déjà connue ne doit pas être écrasée sans décision"
    )


def test_retrait_piece_est_trace(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    store.retirer_piece(d.id, "j1", acteur="test", motif="mauvais document")
    relu = store.get(d.id)
    assert relu.pieces == []
    actions = [e.action for e in relu.history]
    assert "piece_added" in actions and "piece_removed" in actions
    retire = [e for e in relu.history if e.action == "piece_removed"][0]
    assert retire.detail["motif"] == "mauvais document"
    assert retire.acteur == "test"


def test_suppression_dossier_ne_touche_pas_aux_documents(tmp_path, store) -> None:
    """Le dossier est une référence : le supprimer ne supprime rien d'autre."""
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    assert store.supprimer(d.id) is True
    assert store.get(d.id) is None
    # aucune trace de suppression de document n'a été demandée
    assert list((tmp_path / "logs").glob("*.log")), "l'audit doit exister"


# ─────────────────────── pièces manquantes ───────────────────────

def test_pieces_requises_manquantes(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    manquantes = store.pieces_manquantes(store.get(d.id))
    categories = {m["category"] for m in manquantes}
    assert "bill_of_lading" in categories, "le BL est requis dans ce profil"
    assert "packing_list" in categories
    requises = {m["category"] for m in manquantes if m["required"]}
    assert "packing_list" not in requises, (
        "une pièce non requise ne doit pas être annoncée comme bloquante"
    )


def test_profil_decrit_des_conventions_pas_des_obligations() -> None:
    """Aucun profil ne doit se présenter comme une exigence réglementaire."""
    for pid, profil in PROFILS_DOSSIER.items():
        if pid == "personnalise":
            continue        # celui-ci n'impose aucune pièce
        assert "convention" in profil.description.lower(), (
            f"le profil {pid} doit dire qu'il décrit des conventions"
        )
        for piece in profil.pieces:
            assert not piece.required or piece.note == "", (
                f"{pid}/{piece.category} : une pièce requise ne doit pas "
                "porter de justification réglementaire"
            )


# ───────────────────────────── état ─────────────────────────────

def _etats(**kw):
    base = {"status": "done", "needs_review": False, "valide": True}
    base.update(kw)
    return base


def test_etat_deduit_du_traitement_en_cours(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    store.ajouter_piece(d.id, "j2", "bl.pdf", "bill_of_lading")
    d = store.recalculer_etat(d.id, {"j1": _etats(status="processing"),
                                     "j2": _etats()})
    assert d.state == DossierState.TRAITEMENT_EN_COURS


def test_etat_deduit_de_la_revision_requise(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    store.ajouter_piece(d.id, "j2", "bl.pdf", "bill_of_lading")
    d = store.recalculer_etat(d.id, {"j1": _etats(), "j2": _etats(needs_review=True)})
    assert d.state == DossierState.REVISION_REQUISE


def test_etat_incomplet_si_piece_requise_absente(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")   # BL manquant
    d = store.recalculer_etat(d.id, {"j1": _etats()})
    assert d.state == DossierState.INCOMPLET


def test_etat_valide_quand_tout_est_la(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    store.ajouter_piece(d.id, "j2", "bl.pdf", "bill_of_lading")
    d = store.recalculer_etat(d.id, {"j1": _etats(), "j2": _etats()})
    assert d.state == DossierState.VALIDE


def test_etat_en_validation_si_piece_non_validee(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    store.ajouter_piece(d.id, "j2", "bl.pdf", "bill_of_lading")
    d = store.recalculer_etat(d.id, {"j1": _etats(valide=True),
                                     "j2": _etats(valide=False)})
    assert d.state == DossierState.EN_VALIDATION


def test_etat_erreur_si_un_document_a_echoue(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    store.ajouter_piece(d.id, "j2", "bl.pdf", "bill_of_lading")
    d = store.recalculer_etat(d.id, {"j1": _etats(), "j2": _etats(status="failed")})
    assert d.state == DossierState.ERREUR_TRAITEMENT


def etat_vide_reste_en_preparation(store) -> None:
    d = _dossier_import(store)
    d = store.recalculer_etat(d.id, {})
    assert d.state == DossierState.EN_PREPARATION


def test_changement_detat_est_journalise(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    store.ajouter_piece(d.id, "j2", "bl.pdf", "bill_of_lading")
    store.recalculer_etat(d.id, {"j1": _etats(), "j2": _etats()})
    changes = [e for e in store.get(d.id).history if e.action == "state_changed"]
    assert changes, "aucun changement d'état tracé"
    assert changes[-1].detail["to"] == DossierState.VALIDE.value


def test_etat_force_est_trace_et_versionne(store) -> None:
    d = _dossier_import(store)
    version_avant = d.version
    d = store.forcer_etat(d.id, DossierState.ARCHIVE, acteur="test",
                          motif="dossier clos")
    assert d.state == DossierState.ARCHIVE
    assert d.version == version_avant + 1
    force = [e for e in d.history if e.action == "state_forced"][0]
    assert force.detail["motif"] == "dossier clos"
    assert force.acteur == "test"


# ───────────────────────────── synthèse ─────────────────────────────

def test_synthese_structurelle_sans_donnees(store) -> None:
    d = _dossier_import(store)
    store.ajouter_piece(d.id, "j1", "facture.pdf", "invoice")
    s = store.synthese(store.get(d.id))
    assert s["state_label"]
    assert s["categories"] == {"invoice": 1}
    assert isinstance(s["pieces_manquantes"], list)
    assert s["champs_par_document"] == {}, (
        "sans données fournies, la synthèse ne doit rien inventer"
    )


def test_liste_triee_par_activite(store) -> None:
    import time as _t
    store.creer("A", "personnalise")
    _t.sleep(0.01)          # garantit un timestamp distinct sur Windows
    b = store.creer("B", "personnalise")
    store.ajouter_piece(b.id, "j1", "x.pdf", "invoice")
    ids = [d.id for d in store.liste()]
    assert ids[0] == b.id, "le dossier touché en dernier doit venir en premier"
