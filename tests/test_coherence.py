"""Contrôles de cohérence interdocumentaires (étape 8).

**Pourquoi ces tests.** Le moteur compare des documents entre eux. Ce qui est
vérifié : il détecte une référence absente, un conteneur déclaré d'un côté
seulement, un poids qui diverge au-delà de la tolérance, un document en double
— et surtout qu'il **ne transforme pas toute différence en erreur** : une
divergence légitime reste un avertissement, et seul un conflit bloquant
explicitement configuré interdit la transmission.
"""
from __future__ import annotations

from unocr.coherence import (
    ANOMALY,
    BLOCKING,
    WARNING,
    ChampDocument,
    CoherenceEngine,
)


def _champs_complets() -> list[ChampDocument]:
    """Facture + BL + liste de colisage, partiellement cohérents."""
    return [
        ChampDocument("j1", "facture.pdf", "invoice", "invoice_number", "2024-118"),
        ChampDocument("j1", "facture.pdf", "invoice", "gross_weight", "13500 KG"),
        ChampDocument("j2", "bl.pdf", "bill_of_lading", "invoice_number", "2024-118"),
        ChampDocument("j2", "bl.pdf", "bill_of_lading", "gross_weight", "12000 KG"),
        ChampDocument("j2", "bl.pdf", "bill_of_lading", "container_number",
                      "MSCU1234567, TGHU7654321"),
        ChampDocument("j3", "colisage.pdf", "packing_list", "container_number",
                      "MSCU1234567"),
    ]


# ───────────────────────── poids ─────────────────────────

def test_poids_divergent_signale() -> None:
    constats = CoherenceEngine().verifie_poids(_champs_complets())
    assert len(constats) == 1
    c = constats[0]
    assert c.rule == "poids_divergent:gross_weight"
    assert c.severity == ANOMALY
    assert c.resultat == "divergent"
    assert c.explication


def test_poids_proche_ne_signale_rien() -> None:
    """Un arrondi de pesée n'est pas une anomalie."""
    champs = [
        ChampDocument("j1", "a.pdf", "invoice", "gross_weight", "12000 KG"),
        ChampDocument("j2", "b.pdf", "bill_of_lading", "gross_weight", "12100 KG"),
    ]
    assert CoherenceEngine().verifie_poids(champs) == []


def test_poids_absent_ne_signale_rien() -> None:
    champs = [ChampDocument("j1", "a.pdf", "invoice", "gross_weight", None)]
    assert CoherenceEngine().verifie_poids(champs) == []


# ───────────────────────── conteneurs ─────────────────────────

def test_conteneur_absent_dun_document_signale() -> None:
    constats = CoherenceEngine().verifie_conteneurs(_champs_complets())
    assert len(constats) == 1
    c = constats[0]
    assert c.resultat == "absent"
    assert "TGHU7654321" in c.valeurs
    assert c.severity == WARNING, (
        "un conteneur manquant dans une liste de colisage est un "
        "avertissement, pas une anomalie automatique"
    )


def test_conteneurs_identiques_ne_signale_rien() -> None:
    champs = [
        ChampDocument("j2", "bl.pdf", "bill_of_lading", "container_number", "MSCU1"),
        ChampDocument("j3", "pl.pdf", "packing_list", "container_number", "MSCU1"),
    ]
    assert CoherenceEngine().verifie_conteneurs(champs) == []


def test_un_seul_document_ne_declenche_pas_de_comparaison() -> None:
    champs = [ChampDocument("j2", "bl.pdf", "bill_of_lading",
                            "container_number", "MSCU1, TGHU2")]
    assert CoherenceEngine().verifie_conteneurs(champs) == []


# ───────────────────────── références ─────────────────────────

def test_reference_absente_dun_document_signalee() -> None:
    constats = CoherenceEngine().verifie_reference_absente(
        _champs_complets(), "invoice_number", ["packing_list"])
    assert len(constats) == 1
    c = constats[0]
    assert c.resultat == "absent"
    # la comparaison normalise (casse, espaces, séparateurs) : 2024-118 -> 2024118
    assert "2024118" in c.valeurs
    assert c.severity == WARNING


def test_reference_presente_partout_ne_signale_rien() -> None:
    champs = [
        ChampDocument("j1", "f.pdf", "invoice", "invoice_number", "A1"),
        ChampDocument("j3", "p.pdf", "packing_list", "invoice_number", "A1"),
    ]
    assert CoherenceEngine().verifie_reference_absente(
        champs, "invoice_number", ["packing_list"]) == []


def test_references_divergentes_sont_un_avertissement_pas_une_erreur() -> None:
    """Deux factures peuvent légitimement coexister dans un dossier."""
    champs = [
        ChampDocument("j1", "f.pdf", "invoice", "invoice_number", "A1"),
        ChampDocument("j2", "g.pdf", "invoice", "invoice_number", "A2"),
    ]
    constats = CoherenceEngine().verifie_reference_commune(champs)
    assert len(constats) == 1
    assert constats[0].severity == WARNING
    assert constats[0].resultat == "divergent"


# ───────────────────────── doublons ─────────────────────────

def test_document_en_double_signale_sans_suppression() -> None:
    empreintes = {"j1": "abc123", "j2": "abc123"}
    constats = CoherenceEngine().verifie_doublons_documentaires([], empreintes)
    assert len(constats) == 1
    c = constats[0]
    assert c.resultat == "doublon"
    assert "Aucune suppression automatique" in c.explication


def test_empreintes_distinctes_ne_signale_rien() -> None:
    assert CoherenceEngine().verifie_doublons_documentaires(
        [], {"j1": "a", "j2": "b"}) == []


# ───────────────────────── gravité et transmission ─────────────────────────

def test_regle_bloquante_configurable() -> None:
    """Seule une règle explicitement bloquante interdit la transmission."""
    moteur = CoherenceEngine(regles_bloquantes={"poids_divergent:gross_weight"})
    constats = moteur.verifie_poids(_champs_complets())
    assert constats[0].severity == BLOCKING
    ok, motif = moteur.peut_transmettre(constats)
    assert ok is False
    assert "poids_divergent" in motif


def test_sans_regle_bloquante_la_transmission_reste_possible() -> None:
    constats = CoherenceEngine().analyser(_champs_complets())
    assert constats, "des constats doivent être détectés"
    ok, motif = CoherenceEngine().peut_transmettre(constats)
    assert ok is True
    assert motif == ""


def test_constat_tranche_n_est_plus_bloquant() -> None:
    moteur = CoherenceEngine(regles_bloquantes={"poids_divergent:gross_weight"})
    constats = moteur.verifie_poids(_champs_complets())
    constats[0].status = "accepte"          # décision humaine
    assert moteur.peut_transmettre(constats)[0] is True


# ───────────────────────── agrégat ─────────────────────────

def test_analyse_trie_par_gravite() -> None:
    constats = CoherenceEngine().analyser(
        _champs_complets(), attendus={"invoice_number": ["packing_list"]})
    severites = [c.severity for c in constats]
    assert severites == sorted(severites, key=lambda s: -["information",
                              "avertissement", "anomalie", "blocage"].index(s))


def test_constat_serialisable() -> None:
    c = CoherenceEngine().verifie_poids(_champs_complets())[0]
    d = c.as_dict()
    assert set(d) >= {"rule", "severity", "documents", "valeurs",
                      "resultat", "explication", "status"}
    assert d["status"] == "a_trancher"
