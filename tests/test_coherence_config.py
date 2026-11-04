"""Tests des règles de rapprochement configurables (lot 4).

Ce que ces tests verrouillent : une tolérance, une règle désactivée ou
bloquante doit **réellement** changer le comportement. Une configuration
qu'on peut écrire mais qui ne change rien est pire que pas de configuration :
elle laisse croire qu'on maîtrise les contrôles.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from unocr.coherence import ANOMALY, BLOCKING, ChampDocument, CoherenceEngine  # noqa: E402


def _champs(poids=(12000.0, 13500.0), conteneurs=("MSCU1234567", "TGHU7654321")):
    """Deux documents avec un écart de poids et deux conteneurs distincts."""
    return [
        ChampDocument(job_id="a", filename="bl.pdf", category="bill_of_lading",
                      key="gross_weight", value=str(poids[0]), label="Poids brut"),
        ChampDocument(job_id="b", filename="colisage.pdf", category="packing_list",
                      key="gross_weight", value=str(poids[1]), label="Poids brut"),
        ChampDocument(job_id="a", filename="bl.pdf", category="bill_of_lading",
                      key="container_number", value=conteneurs[0],
                      label="N° de conteneur"),
        ChampDocument(job_id="b", filename="colisage.pdf", category="packing_list",
                      key="container_number", value=conteneurs[1],
                      label="N° de conteneur"),
    ]


# ─────────────────────────── valeurs par défaut ───────────────────────────

def test_defauts_inchanges_sans_configuration():
    """Sans configuration, le comportement doit être celui d'avant : rien ne
    change pour les déploiements existants."""
    moteur = CoherenceEngine()
    assert moteur.tolerance("gross_weight") == 0.02
    assert moteur.tolerance("quantity") == 0.05
    assert moteur.cles_reference == ["invoice_number"]
    assert moteur.regles_desactivees == set()
    constats = moteur.verifie_poids(_champs())
    assert [c.rule for c in constats] == ["poids_divergent:gross_weight"]


def test_appel_positionnel_ancien_toujours_accepte():
    """La signature a changé ; l'ancien appel ne doit pas casser."""
    moteur = CoherenceEngine(["poids_divergent:gross_weight"])
    assert "poids_divergent:gross_weight" in moteur.regles_bloquantes


# ─────────────────────────── tolérances ───────────────────────────

def test_tolerance_plus_large_fait_disparaitre_le_constat():
    """Un écart de 11,8 % passe sous une tolérance de 20 % : c'est le sens
    même d'une tolérance configurable."""
    moteur = CoherenceEngine({"tolerances": {"gross_weight": 0.20}})
    assert moteur.verifie_poids(_champs()) == []


def test_tolerance_plus_stricte_fait_apparaitre_le_constat():
    moteur = CoherenceEngine({"tolerances": {"gross_weight": 0.001}})
    constats = moteur.verifie_poids(_champs())
    assert constats and constats[0].rule == "poids_divergent:gross_weight"


def test_tolerance_annoncee_dans_l_explication():
    """L'explication doit citer le seuil réellement appliqué, sinon
    l'opérateur ne peut pas savoir pourquoi l'alerte est partie."""
    moteur = CoherenceEngine({"tolerances": {"gross_weight": 0.001}})
    constat = moteur.verifie_poids(_champs())[0]
    assert "0 %" in constat.explication or "0.1" in constat.explication
    assert "tolérance" in constat.explication


def test_tolerance_par_cle_independante():
    """Chaque clé a sa tolérance : un poids et une quantité ne se tolèrent
    pas de la même façon."""
    moteur = CoherenceEngine({"tolerances": {"gross_weight": 0.5,
                                            "quantity": 0.001}})
    assert moteur.tolerance("gross_weight") == 0.5
    assert moteur.tolerance("quantity") == 0.001


def test_cle_inconnue_reprend_la_tolerance_par_defaut():
    moteur = CoherenceEngine({"tolerances": {"gross_weight": 0.3}})
    assert moteur.tolerance("champ_jamais_vu") == 0.02


# ─────────────────────────── règles désactivées ───────────────────────────

def test_regle_desactivee_ne_produit_aucun_constat():
    """Désactiver doit faire taire la règle, pas seulement baisser sa gravité."""
    moteur = CoherenceEngine({"regles_desactivees": ["poids_divergent"]})
    assert moteur.active("poids_divergent") is False
    assert moteur.verifie_poids(_champs()) == []
    assert [c.rule for c in moteur.analyser(_champs())
            if c.rule.startswith("poids_divergent")] == []


def test_regle_desactivee_n_affecte_pas_les_autres():
    moteur = CoherenceEngine({"regles_desactivees": ["document_en_double"]})
    constats = moteur.analyser(_champs())
    assert not any(c.rule == "document_en_double" for c in constats)
    assert any(c.rule.startswith("poids_divergent") for c in constats)


def test_plusieurs_regles_desactivees():
    moteur = CoherenceEngine({"regles_desactivees": ["poids_divergent",
                                                    "conteneur_absent"]})
    regles = {c.rule for c in moteur.analyser(_champs())}
    assert not any(r.startswith("poids_divergent") for r in regles)
    assert not any(r.startswith("conteneur_absent") for r in regles)


def test_desactivation_par_nom_de_regle_exact():
    """Le nom doit correspondre exactement : une approximation silencieuse
    laisserait croire à une désactivation qui n'a pas eu lieu."""
    moteur = CoherenceEngine({"regles_desactivees": ["poids_divergnt"]})
    assert moteur.verifie_poids(_champs()), "une faute de frappe ne désactive rien"


# ─────────────────────────── règles bloquantes ───────────────────────────

def test_regle_bloquante_interdit_la_transmission():
    moteur = CoherenceEngine({"regles_bloquantes": ["poids_divergent:gross_weight"]})
    constats = moteur.analyser(_champs())
    poids = [c for c in constats if c.rule == "poids_divergent:gross_weight"][0]
    assert poids.severity == BLOCKING
    assert poids.bloquant is True
    autorise, motif = moteur.peut_transmettre(constats)
    assert autorise is False
    assert "poids_divergent" in motif


def test_regle_non_bloquante_autorise_la_transmission():
    """Le comportement d'avant : une anomalie à trancher n'empêche pas de
    préparer le dossier, elle est seulement signalée."""
    moteur = CoherenceEngine()
    constats = moteur.analyser(_champs())
    poids = [c for c in constats if c.rule == "poids_divergent:gross_weight"][0]
    assert poids.severity == ANOMALY
    assert poids.bloquant is False
    autorise, _ = moteur.peut_transmettre(constats)
    assert autorise is True


def test_constat_tranche_ne_bloque_plus():
    """Une fois arbitrée par un humain, la décision est respectée."""
    moteur = CoherenceEngine({"regles_bloquantes": ["poids_divergent:gross_weight"]})
    constats = moteur.analyser(_champs())
    for c in constats:
        if c.rule == "poids_divergent:gross_weight":
            c.status = "accepte"
            c.decision_par = "amina"
    autorise, _ = moteur.peut_transmettre(constats)
    assert autorise is True


# ─────────────────────────── clés de référence ───────────────────────────

def test_cles_reference_configurables():
    champs = _champs() + [
        ChampDocument(job_id="a", filename="bl.pdf", category="bill_of_lading",
                      key="bl_number", value="BL-1", label="N° de BL"),
        ChampDocument(job_id="b", filename="colisage.pdf", category="packing_list",
                      key="bl_number", value="BL-2", label="N° de BL"),
    ]
    moteur = CoherenceEngine({"cles_reference": ["bl_number"]})
    regles = {c.rule for c in moteur.analyser(champs)}
    assert "reference_divergente:bl_number" in regles
    # invoice_number n'est plus cherchée par défaut
    assert not any(r.startswith("reference_divergente:invoice_number") for r in regles)


def test_plusieurs_cles_de_reference():
    champs = _champs() + [
        ChampDocument(job_id="a", filename="bl.pdf", category="bill_of_lading",
                      key="bl_number", value="BL-1", label="N° de BL"),
        ChampDocument(job_id="b", filename="colisage.pdf", category="packing_list",
                      key="bl_number", value="BL-2", label="N° de BL"),
    ]
    moteur = CoherenceEngine({"cles_reference": ["invoice_number", "bl_number"]})
    regles = {c.rule for c in moteur.analyser(champs)}
    assert "reference_divergente:bl_number" in regles


# ─────────────────────────── configuration effective ───────────────────────────

def test_configuration_effective_est_lisible():
    moteur = CoherenceEngine({"tolerances": {"gross_weight": 0.05},
                              "regles_bloquantes": ["document_en_double"],
                              "regles_desactivees": ["conteneur_absent"]})
    cfg = moteur.configuration_effective()
    assert cfg["tolerances"]["gross_weight"] == 0.05
    assert cfg["tolerances"]["quantity"] == 0.05   # défaut conservé
    assert cfg["regles_bloquantes"] == ["document_en_double"]
    assert cfg["regles_desactivees"] == ["conteneur_absent"]


def test_configuration_vide_est_sure():
    """Une configuration absente ou vide ne doit rien casser."""
    for valeur in (None, {}, {"tolerances": None}, {"regles_desactivees": None}):
        moteur = CoherenceEngine(valeur)
        assert moteur.tolerance("gross_weight") == 0.02
        assert moteur.verifie_poids(_champs())
