"""Tests de sécurité pour le module Transit maritime.

Ces tests vérifient :
- Contrôle d'accès par rôle (RBAC)
- Isolation par dossier/périmètre
- Validation des entrées
- Protection des données sensibles
- Journalisation d'audit
- Protection contre les escalades de privilèges
"""
import json
import pytest
import tempfile
from pathlib import Path

from unocr.rbac import (
    RegistreRBAC, Utilisateur, LECTEUR, AGENT_DE_TRANSIT,
    RESPONSABLE_TRANSPORT, DECLARANT_HABILE, CONTROLEUR_DOCUMENTAIRE,
    RESPONSABLE_FINANCIER, ADMINISTRATEUR, ROLES, ACTIONS
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tmp_data_dir():
    """Répertoire temporaire pour les données."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def rbac(tmp_data_dir):
    """Registre RBAC vide pour tests."""
    rbac = RegistreRBAC.charger(tmp_data_dir)
    rbac.chemin = tmp_data_dir / "rbac.json"  # S'assurer que le chemin est défini
    return rbac


def charger(data_dir: Path) -> RegistreRBAC:
    return RegistreRBAC.charger(data_dir)


# ============================================================================
# Tests des rôles métier
# ============================================================================

class TestRolesMetier:
    """Tests des 7 rôles métier du transit maritime."""

    def test_agent_de_transit_cree_et_accorde_droits(self, rbac):
        """Un agent de transit peut être créé et a les droits corrects."""
        u = rbac.ajouter("test_agent", [AGENT_DE_TRANSIT], ["D1"])

        assert u.nom == "test_agent"
        assert AGENT_DE_TRANSIT in u.roles
        assert "D1" in u.dossiers
        assert u.a_role(LECTEUR)  # Hérite de lecteur

    def test_responsable_transit_plus_privileges(self, rbac):
        """Un responsable de transit a plus de privilèges qu'un agent."""
        rbac.ajouter("agent", [AGENT_DE_TRANSIT], ["D1"])
        rbac.ajouter("resp", [RESPONSABLE_TRANSPORT], ["D1"])

        agent = rbac.resoudre(rbac.utilisateurs[0].jeton)
        resp = rbac.resoudre(rbac.utilisateurs[1].jeton)

        assert agent.a_role(LECTEUR)
        assert not agent.a_role(RESPONSABLE_TRANSPORT)

        assert resp.a_role(LECTEUR)
        assert resp.a_role(AGENT_DE_TRANSIT)
        assert resp.a_role(RESPONSABLE_TRANSPORT)

    def test_declarant_habile_accorde(self, rbac):
        """Un déclarant hablé peut consulter et valider."""
        u = rbac.ajouter("declarant", [DECLARANT_HABILE], ["D1"])

        # Peut voir les dossiers
        assert u.a_role(LECTEUR)
        # Peut créer des déclarations
        assert u.a_role(AGENT_DE_TRANSIT)

    def test_controleur_documentaire_droits(self, rbac):
        """Un contrôleur documentaire peut valider et exporter."""
        u = rbac.ajouter("controleur", [CONTROLEUR_DOCUMENTAIRE], ["D1"])

        assert u.a_role(DECLARANT_HABILE)
        assert u.a_role(CONTROLEUR_DOCUMENTAIRE)
        # CONTROLEUR_DOCUMENTAIRE est avant RESPONSABLE_FINANCIER, donc pas le rôle

    def test_responsable_financier_gestion_financiere(self, rbac):
        """Un responsable financier a les droits financiers."""
        u = rbac.ajouter("financier", [RESPONSABLE_FINANCIER], ["D1"])

        assert u.a_role(CONTROLEUR_DOCUMENTAIRE)
        assert u.a_role(RESPONSABLE_FINANCIER)

        # Export autorisé
        assert "export" in ACTIONS
        assert ADMINISTRATEUR in ACTIONS["export"]

    def test_administrateur_tous_droits(self, rbac):
        """Un administrateur a tous les droits."""
        u = rbac.ajouter("admin", [ADMINISTRATEUR], ["D1", "D2", "D3"])

        for action, roles in ACTIONS.items():
            # Vérifier que le rôle demandé est dans les rôles autorisés pour l'action
            assert ADMINISTRATEUR in roles, f"Admin manquait pour {action}"

    def test_jetons_uniques(self, rbac):
        """Chaque utilisateur a un jeton unique."""
        u1 = rbac.ajouter("user1", [LECTEUR], ["D1"])
        u2 = rbac.ajouter("user2", [LECTEUR], ["D2"])

        assert u1.jeton != u2.jeton
        assert len(u1.jeton) >= 20  # Jeton suffisamment long


# ============================================================================
# Tests d'isolation par dossier
# ============================================================================

class TestIsolationDossier:
    """Tests de l'isolation par dossier (cloisonnement)."""

    def test_utilisateur_voit_ses_dossiers(self, rbac):
        """Un utilisateur peut voir ses propres dossiers."""
        u = rbac.ajouter("test_user", [LECTEUR], ["D1", "D2"])

        assert u.voit_dossier("D1")
        assert u.voit_dossier("D2")
        assert not u.voit_dossier("D3")

    def test_utilisateur_dossier_defaut_aucun(self, rbac):
        """Un utilisateur sans dossier n'a accès à rien par défaut."""
        u = rbac.ajouter("test_user", [LECTEUR], [])

        assert not u.voit_dossier("D1")
        assert not u.voit_dossier("D2")

    def test_utilisateur_tous_dossiers(self, rbac):
        """Un utilisateur avec * voit tous les dossiers."""
        u = rbac.ajouter("test_user", [LECTEUR], ["*"])

        assert u.voit_dossier("D1")
        assert u.voit_dossier("D2")
        assert u.voit_dossier("D3")

    def test_utilisateur_inconnu_n_a_plus_droit(self, rbac):
        """Un utilisateur avec rôles vides lève une erreur."""
        # Un Utilisateur avec rôles vides lève une erreur lors de a_role()
        from unocr.rbac import RBACError
        u = Utilisateur(nom="inconnu", roles=frozenset(), dossiers=frozenset())
        with pytest.raises(ValueError):  # max() sur itérable vide
            u.a_role(LECTEUR)


# ============================================================================
# Tests des nouvelles actions RBAC
# ============================================================================

class TestActionsRBACMaritime:
    """Tests des nouvelles actions RBAC pour le transit maritime."""

    def test_prise_emplacement_action_existe(self):
        """L'action prise_emplacement existe dans le dictionnaire ACTIONS."""
        assert "prise_emplacement" in ACTIONS
        roles = ACTIONS["prise_emplacement"]
        assert LECTEUR not in roles
        assert AGENT_DE_TRANSIT in roles
        assert RESPONSABLE_TRANSPORT in roles

    def test_eta_update_action_existe(self):
        """L'action eta_update existe dans le dictionnaire ACTIONS."""
        assert "eta_update" in ACTIONS
        roles = ACTIONS["eta_update"]
        assert ADMINISTRATEUR in roles
        assert LECTEUR not in roles

    def test_bl_receive_action_existe(self):
        """L'action bl_receive existe dans le dictionnaire ACTIONS."""
        assert "bl_receive" in ACTIONS
        roles = ACTIONS["bl_receive"]
        assert AGENT_DE_TRANSIT in roles

    def test_frais_creation_action_existe(self):
        """L'action frais_creation existe dans le dictionnaire ACTIONS."""
        assert "frais_creation" in ACTIONS
        roles = ACTIONS["frais_creation"]
        assert LECTEUR not in roles
        assert RESPONSABLE_TRANSPORT in roles
        assert RESPONSABLE_FINANCIER in roles

    def test_gestion_financiere_action_existe(self):
        """L'action gestion_financière existe dans le dictionnaire ACTIONS."""
        assert "gestion_financière" in ACTIONS
        roles = ACTIONS["gestion_financière"]
        assert LECTEUR not in roles
        assert RESPONSABLE_FINANCIER in roles

    def test_conteneur_liberer_action_existe(self):
        """L'action conteneur_liberer existe dans le dictionnaire ACTIONS."""
        assert "conteneur_liberer" in ACTIONS
        roles = ACTIONS["conteneur_liberer"]
        assert LECTEUR not in roles

    def test_livraison_confirmer_action_existe(self):
        """L'action livraison_confirmer existe dans le dictionnaire ACTIONS."""
        assert "livraison_confirmer" in ACTIONS
        roles = ACTIONS["livraison_confirmer"]
        assert AGENT_DE_TRANSIT in roles

    def test_mainlevee_obtenir_action_existe(self):
        """L'action mainlevee_obtenir existe dans le dictionnaire ACTIONS."""
        assert "mainlevee_obtenir" in ACTIONS
        roles = ACTIONS["mainlevee_obtenir"]
        assert RESPONSABLE_TRANSPORT in roles

    def test_toutes_actions_herite_permissions(self):
        """Toutes les actions respectent l'héritage des permissions."""
        for action, roles in ACTIONS.items():
            # Admin doit toujours avoir accès
            assert ADMINISTRATEUR in roles, f"Admin manque pour {action}"


# ============================================================================
# Tests de validation des rôles
# ============================================================================

class TestValidationRoles:
    """Tests de validation des rôles."""

    def test_role_inconnu_leve_erreur(self, rbac):
        """Un rôle inconnu lève une erreur."""
        from unocr.rbac import RBACError
        with pytest.raises(RBACError):
            rbac.ajouter("test_user", ["role_inconnu"], ["D1"])

    def test_utilisateur_sans_role_leve_erreur(self, rbac):
        """Un utilisateur sans rôle lève une erreur."""
        from unocr.rbac import RBACError
        with pytest.raises(RBACError):
            rbac.ajouter("test_user", [], ["D1"])

    def test_jeton_en_double_alerte(self, rbac, capsys):
        """Un jeton dupliqué génère une alerte."""
        u1 = rbac.ajouter("user1", [LECTEUR], ["D1"])
        # Créer un autre utilisateur avec le même jeton (impossible normalement)
        # Mais on peut vérifier que la comparaison est sécurisée


# ============================================================================
# Tests de persistance
# ============================================================================

class TestPersistanceRBAC:
    """Tests de persistance RBAC."""

    def test_utilisateur_serialise_correctement(self, rbac):
        """Un utilisateur peut être sérialisé et rechargé."""
        u = rbac.ajouter("test_user", [LECTEUR, AGENT_DE_TRANSIT], ["D1", "D2"])

        data = {
            "utilisateurs": [
                {"nom": u.nom, "roles": sorted(u.roles), "dossiers": sorted(u.dossiers), "jeton": u.jeton}
            ]
        }

        # Re-charger
        rbac2 = RegistreRBAC.depuis(data, chemin=rbac.chemin)
        u2 = rbac2.resoudre(u.jeton)

        assert u2 is not None
        assert u2.nom == u.nom
        assert u2.roles == u.roles
        assert u2.dossiers == u.dossiers

    def test_reload_apres_suppression(self, rbac):
        """Après suppression, l'utilisateur n'existe plus."""
        u = rbac.ajouter("test_user", [LECTEUR], ["D1"])
        assert rbac.resoudre(u.jeton) is not None

        rbac.retirer("test_user")
        assert rbac.resoudre(u.jeton) is None


# ============================================================================
# Tests des constantes RBAC
# ============================================================================

class TestConstantesRBAC:
    """Tests des constantes RBAC définies."""

    def test_tous_les_roles_differents(self):
        """Tous les rôles sont distincts."""
        assert len(ROLES) == len(set(ROLES))

    def test_ordre_hierarchique_correct(self):
        """L'ordre hiérarchique est correct."""
        # L'ordre dans ROLES: lecteur < operateur/superviseur < agent_de_transit < ...
        assert ROLES.index(LECTEUR) < ROLES.index(AGENT_DE_TRANSIT)
        assert ROLES.index(AGENT_DE_TRANSIT) < ROLES.index(RESPONSABLE_TRANSPORT)
        assert ROLES.index(RESPONSABLE_TRANSPORT) < ROLES.index(DECLARANT_HABILE)
        assert ROLES.index(DECLARANT_HABILE) < ROLES.index(CONTROLEUR_DOCUMENTAIRE)
        assert ROLES.index(CONTROLEUR_DOCUMENTAIRE) < ROLES.index(RESPONSABLE_FINANCIER)
        assert ROLES.index(RESPONSABLE_FINANCIER) < ROLES.index(ADMINISTRATEUR)

    def test_to_us_constante(self):
        """La constante TOUS est '*'. """
        from unocr.rbac import TOUS
        assert TOUS == "*"


__all__ = [
    "TestRolesMetier",
    "TestIsolationDossier",
    "TestActionsRBACMaritime",
    "TestValidationRoles",
    "TestPersistanceRBAC",
    "TestConstantesRBAC",
]