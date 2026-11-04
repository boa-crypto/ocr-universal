"""Archivage et traçabilité — étape 15 du parcours.

**Ce que ces tests protègent.** Deux choses. D'abord que l'archivage ne
supprime rien : c'est un état, pas une mise au placard. Ensuite que la trace
dit toujours ce qu'elle est — un journal applicatif — et ne se présente jamais
comme une preuve inviolable.
"""
from __future__ import annotations

import pytest

from unocr.dossier import DossierState, DossierStore
from unocr.tracabilite import (
    AVERTISSEMENT_TRACABILITE,
    GARANTIES_ARCHIVAGE,
    LIMITES_ARCHIVAGE,
    archiver_dossier,
    lit_journal,
    synthese_tracabilite,
    trace_dossier,
)


@pytest.fixture()
def store(tmp_path):
    s = DossierStore(tmp_path / "dossiers", log_dir=tmp_path / "logs")
    d = s.creer("Import trace", "importation")
    s.ajouter_piece(d.id, "job_a", "facture.pdf", category="invoice")
    s.ajouter_piece(d.id, "job_b", "bl.pdf", category="bill_of_lading")
    return s


# ─────────────────────────── archivage ───────────────────────────

def test_archivage_ne_supprime_rien(store) -> None:
    d = store.liste()[0]
    avant = store.synthese(d)
    synthese = archiver_dossier(store, d.id, motif="dossier clos")
    # les pièces sont toujours là
    assert len(synthese["pieces"]) == len(avant["pieces"]) == 2
    # et l'état est bien archivé
    assert synthese["state"] == "archive"
    # le dossier existe toujours sur disque
    relu = store.get(d.id)
    assert relu is not None
    assert relu.state == DossierState.ARCHIVE
    assert len(relu.pieces) == 2


def test_archivage_est_trace(store) -> None:
    d = store.liste()[0]
    archiver_dossier(store, d.id, motif="dossier clos")
    evenements = [e["event"] for e in lit_journal(store.log_dir)]
    assert "dossier_archived" in evenements
    ligne = next(e for e in lit_journal(store.log_dir)
                 if e["event"] == "dossier_archived")
    assert ligne["motif"] == "dossier clos"


def test_double_archivage_est_refuse(store) -> None:
    d = store.liste()[0]
    archiver_dossier(store, d.id)
    with pytest.raises(ValueError, match="déjà archivé"):
        archiver_dossier(store, d.id)


def test_archivage_d_un_dossier_incomplet_le_dit(store) -> None:
    """Archiver un dossier incomplet ne le rend pas complet — et le signale."""
    d = store.liste()[0]
    synthese = archiver_dossier(store, d.id)
    # le profil importation attend des pièces absentes
    assert synthese["avertissements_archivage"], (
        "un archivage avec des pièces manquantes doit le signaler")
    assert any("ne les crée pas" in a
               for a in synthese["avertissements_archivage"])


def test_archivage_d_un_dossier_inexistant(store) -> None:
    with pytest.raises(KeyError):
        archiver_dossier(store, "dos_inexistant")


# ─────────────────────────── traçabilité ───────────────────────────

def test_trace_contient_les_evenements_du_dossier(store) -> None:
    d = store.liste()[0]
    entrees = trace_dossier(store, d.id)
    evenements = [e.event for e in entrees]
    assert "dossier_created" in evenements
    assert "dossier_piece_added" in evenements
    # deux pièces ajoutées = deux événements
    assert evenements.count("dossier_piece_added") == 2


def test_trace_est_ordonnee_dans_le_temps(store) -> None:
    d = store.liste()[0]
    store.forcer_etat(d.id, DossierState.EXPORTE, motif="paquet généré")
    entrees = trace_dossier(store, d.id)
    horodatages = [e.ts for e in entrees]
    assert horodatages == sorted(horodatages), "la trace doit être chronologique"


def test_trace_distingue_etat_deduit_et_etat_force(store) -> None:
    """Un état posé par un humain ne doit pas ressembler à un état déduit."""
    d = store.liste()[0]
    store.forcer_etat(d.id, DossierState.EXPORTE, motif="paquet généré")
    entrees = {e.event: e for e in trace_dossier(store, d.id)}
    force = entrees.get("dossier_state_forced")
    assert force is not None, "le forçage d'état doit être tracé"
    assert "posé par un humain" in force.resume()
    assert "paquet généré" in force.resume()


def test_trace_exclut_le_rattachement_du_meme_document_ailleurs(store, tmp_path) -> None:
    """Un même document peut être joint à deux dossiers : son rattachement à
    l'autre dossier ne doit pas apparaître dans la trace de celui-ci.

    C'est le cas qu'a révélé le store réel : un job_id partagé faisait
    remonter les `dossier_piece_added` d'autres dossiers.
    """
    a = store.creer("Dossier A", "importation")
    b = store.creer("Dossier B", "importation")
    store.ajouter_piece(a.id, "job_partage", "facture.pdf", category="invoice")
    store.ajouter_piece(b.id, "job_partage", "facture.pdf", category="invoice")
    evenements = trace_dossier(store, a.id)
    ajouts = [e for e in evenements if e.event == "dossier_piece_added"]
    assert len(ajouts) == 1
    assert ajouts[0].dossier_id == a.id
    assert all(e.dossier_id in ("", a.id) for e in evenements)


def test_trace_ne_contient_pas_les_evenements_d_un_autre_dossier(store, tmp_path) -> None:
    autre = store.creer("Autre dossier", "personnalise")
    store.ajouter_piece(autre.id, "job_z", "autre.pdf", category="unknown")
    # liste() est triée par activité : on prend le dossier par son libellé
    d = next(x for x in store.liste() if x.label == "Import trace")
    evenements = trace_dossier(store, d.id)
    assert all(e.dossier_id in ("", d.id) for e in evenements)
    assert not any(e.job_id == "job_z" for e in evenements)


def test_trace_ne_remonte_pas_les_evenements_sans_rapport(store) -> None:
    """Une configuration de surveillance ne concerne pas un dossier."""
    from unocr.storage import audit

    audit(store.log_dir, "watch_configured", path="/tmp")
    d = store.liste()[0]
    evenements = [e.event for e in trace_dossier(store, d.id)]
    assert "watch_configured" not in evenements


def test_synthese_porte_l_avertissement(store) -> None:
    d = store.liste()[0]
    t = synthese_tracabilite(store, d.id)
    # l'avertissement est TOUJOURS présent, sans condition
    assert t["avertissement"] == AVERTISSEMENT_TRACABILITE
    assert "pas preuve inviolable" in t["avertissement"]
    assert t["garanties"] == list(GARANTIES_ARCHIVAGE)
    assert t["limites"] == list(LIMITES_ARCHIVAGE)
    assert t["total"] >= 3


def test_journal_illisible_ne_casse_pas_la_trace(store) -> None:
    journal = store.log_dir / "audit.log"
    with journal.open("a", encoding="utf-8") as f:
        f.write("{ceci n'est pas du json}\n")
    d = store.liste()[0]
    entrees = trace_dossier(store, d.id)
    assert len(entrees) >= 3, "une ligne illisible ne doit pas vider la trace"


def test_journal_absent_renvoie_une_liste_vide(store, tmp_path) -> None:
    vide = DossierStore(tmp_path / "vides", log_dir=tmp_path / "pas-de-logs")
    assert lit_journal(vide.log_dir) == []


def test_trace_d_un_dossier_inexistant(store) -> None:
    with pytest.raises(KeyError):
        trace_dossier(store, "dos_inexistant")


# ─────────────────── le journal n'est pas une preuve ───────────────────

def test_avertissement_dit_ce_que_le_journal_n_est_pas() -> None:
    """Le texte doit être honnête sur les limites, pas rassurant."""
    assert "modifier" in AVERTISSEMENT_TRACABILITE
    assert "administrateur" in AVERTISSEMENT_TRACABILITE
    assert "preuve inviolable" in AVERTISSEMENT_TRACABILITE
    # et il ne doit surtout pas promettre l'inviolabilité
    for interdit in ("inviolable", "inaltérable", "infalsifiable",
                     "opposable juridiquement"):
        assert interdit not in GARANTIES_ARCHIVAGE, (
            f"une garantie promet « {interdit} » : c'est faux")


def test_les_garanties_sont_limitees_a_ce_qui_est_vrai() -> None:
    texte = " ".join(GARANTIES_ARCHIVAGE)
    assert "supprimés" in texte          # rien n'est supprimé
    assert "corrections humaines" in texte
    assert "pas une preuve" in " ".join(LIMITES_ARCHIVAGE)
