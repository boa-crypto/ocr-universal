"""Autorisation par rôle et cloisonnement par dossier (P2).

**Le problème.** UniOCR n'avait qu'un jeton unique et partagé (`UNIOCR_TOKEN`).
C'est du tout ou rien : celui qui le détient lit tous les documents, valide
tous les champs, arbitre tous les constats, restaure toutes les sauvegardes.
Dans un service où un opérateur saisit, un superviseur arbitre et un auditeur
ne fait que consulter, ce modèle ne décrit aucune de ces frontières.

**Ce que fait ce module.**

- Quatre rôles ordonnés : `lecteur` < `operateur` < `superviseur` <
  `administrateur`. Un rôle donne accès à tout ce que donnent les rôles
  inférieurs — la hiérarchie évite de répéter les mêmes permissions partout.
- Un cloisonnement par dossier : chaque utilisateur ne voit que les dossiers
  qui lui sont affectés. `dossiers: ["*"]` les autorise tous, une liste vide
  n'en autorise aucun.
- Les utilisateurs vivent dans `data/rbac.json`, un fichier local lu et écrit
  comme les autres données de l'application. Aucune base externe, aucun
  service d'identité : UniOCR reste un outil local.

**Ce qu'il ne fait pas — et qu'il ne prétend pas faire.**

- **Il est inactif sans fichier.** Si `data/rbac.json` n'existe pas, `actif`
  vaut `False` et l'API se comporte exactement comme avant : pas de jeton
  exigé, aucune route fermée. Un déploiement existant n'a rien à migrer.
- **Il n'est pas un annuaire d'entreprise.** Pas de SSO, pas de LDAP, pas
  d'expiration de mot de passe. Les jetons sont des secrets porteurs, comparés
  à temps constant, stockés dans un fichier local — comme `UNIOCR_TOKEN`
  aujourd'hui. C'est la frontière de menace d'un outil local.
- **Il ne chiffre rien.** Voir `crypto_store` pour le chiffrement au repos.
- **Un jeton qui fuite donne les droits de son porteur.** La révocation se
  fait en retirant l'utilisateur du fichier ou en régénérant son jeton, pas en
  invalidant une session.

**Choix de sécurité assumés.**

- *Échec fermé* : un jeton inconnu est refusé quand le fichier existe, et un
  rôle inconnu dans le fichier fait échouer le chargement plutôt que d'être
  ignoré — une faute de frappe silencieusement ignorée donnerait plus de droits
  que prévu.
- *Le jeton d'environnement reste un passe-partout.* `UNIOCR_TOKEN`, s'il est
  défini, vaut `administrateur` sur tous les dossiers. C'est le comportement
  historique, conservé pour ne pas casser les déploiements et les scripts ;
  chaque utilisation est tracée dans l'audit.
"""
from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .logging_setup import get_logger

log = get_logger("rbac")

#: rôle minimal pour chaque action. L'ordre porte la hiérarchie : un
#: superviseur peut faire tout ce que fait un opérateur.
#: Hiérarchie étendue à 7 rôles pour le module Transit maritime :
#: lecteur < agent_de_transit < responsable_transit < declarant_habile
#: < controleur_documentaire < responsable_financier < administrateur
#: Les anciens rôles OPERATEUR et SUPERVISEUR sont conservés pour compatibilité
#: descendante : ils correspondent respectivement à agent_de_transit et
#: responsable_transit dans l'ordre hiérarchique.
LECTEUR = "lecteur"
AGENT_DE_TRANSIT = "agent_de_transit"
OPERATEUR = "operateur"  # alias compatibilité : équivaut à agent_de_transit
SUPERVISEUR = "superviseur"  # alias compatibilité : équivaut à responsable_transit
RESPONSABLE_TRANSPORT = "responsable_transit"
DECLARANT_HABILE = "declarant_habile"
CONTROLEUR_DOCUMENTAIRE = "controleur_documentaire"
RESPONSABLE_FINANCIER = "responsable_financier"
ADMINISTRATEUR = "administrateur"

#: tous les rôles reconnus dans l'ordre croissant de privilèges.
#: Un rôle donné couvre tous ceux qui le précèdent dans cette liste.
#: Ordre : lecteur < operateur(superviseur) < agent_de_transit < responsable_transit
#: < declarant_habile < controleur_documentaire < responsable_financier < administrateur
ROLES = (LECTEUR, OPERATEUR, SUPERVISEUR, AGENT_DE_TRANSIT,
         RESPONSABLE_TRANSPORT, DECLARANT_HABILE, CONTROLEUR_DOCUMENTAIRE,
         RESPONSABLE_FINANCIER, ADMINISTRATEUR)

#: portée « tous les dossiers »
TOUS = "*"

#: dictionnaire des actions supportées par le système RBAC.
#: Chaque action mappe vers un tuple de rôles autorisés, classés du plus
#: privilégié au moins privilégié. Un rôle donné couvre tous ceux qui le
#: précèdent dans la liste ROLES (hiérarchie décroissante).
ACTIONS = {
    # Consultation — lire/view
    "consultation": (LECTEUR, AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                     DECLARANT_HABILE, CONTROLEUR_DOCUMENTAIRE,
                     RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Création — créer un nouveau dossier
    "creation": (AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                 DECLARANT_HABILE, CONTROLEUR_DOCUMENTAIRE,
                 RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Modification — éditer un dossier existant
    "modification": (AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                     DECLARANT_HABILE, CONTROLEUR_DOCUMENTAIRE,
                     RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # ── Opérations maritime spécifiques ──
    "prise_emplacement": (AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                          DECLARANT_HABILE, CONTROLEUR_DOCUMENTAIRE,
                          RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    "eta_update": (AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                   DECLARANT_HABILE, ADMINISTRATEUR),
    "bl_receive": (AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                   CONTROLEUR_DOCUMENTAIRE, ADMINISTRATEUR),
    "frais_creation": (RESPONSABLE_TRANSPORT, RESPONSABLE_FINANCIER,
                       ADMINISTRATEUR),
    "mainlevee_obtenir": (RESPONSABLE_TRANSPORT, RESPONSABLE_FINANCIER,
                          ADMINISTRATEUR),
    "conteneur_liberer": (AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                          RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    "livraison_confirmer": (AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                            RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # ── Opérations documentaires et administratives ──
    # Suppression logique — marquer supprimé (soft-delete)
    "suppression_logique": (CONTROLEUR_DOCUMENTAIRE,
                            RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Archivage — déplacer en archive
    "archivage": (CONTROLEUR_DOCUMENTAIRE,
                  RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Validation documentaire — valider un champ/champ
    "validation_documentaire": (CONTROLEUR_DOCUMENTAIRE,
                                RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Résolution d'anomalies — traiter une anomalie
    "resolution_anomalies": (RESPONSABLE_TRANSPORT,
                             CONTROLEUR_DOCUMENTAIRE,
                             RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Changement de statut — modifier le statut d'un dossier
    "changement_statut": (AGENT_DE_TRANSIT, RESPONSABLE_TRANSPORT,
                          DECLARANT_HABILE, CONTROLEUR_DOCUMENTAIRE,
                          RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Gestion financière — frais, paiements
    "gestion_financière": (CONTROLEUR_DOCUMENTAIRE,
                           RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Export — exporter des données
    "export": (CONTROLEUR_DOCUMENTAIRE,
               RESPONSABLE_FINANCIER, ADMINISTRATEUR),
    # Configuration métier — paramètres du système
    "configuration_métier": (ADMINISTRATEUR,),
}


class RBACError(Exception):
    """Fichier de rôles inutilisable (rôle inconnu, jeton en double…)."""


def _roles_valides(roles: Iterable[str]) -> frozenset[str]:
    propres = {str(r).strip() for r in roles if str(r).strip()}
    inconnus = sorted(propres - set(ROLES))
    if inconnus:
        raise RBACError(
            "rôle(s) inconnu(s) dans data/rbac.json : %s. Rôles acceptés : %s"
            % (", ".join(inconnus), ", ".join(ROLES)))
    if not propres:
        # aucun rôle = aucun droit. Configuration valide mais dangereuse si
        # elle n'est pas voulue : on le dit au chargement.
        raise RBACError("utilisateur sans rôle : précisez au moins « %s »" % LECTEUR)
    return frozenset(propres)


def _portee(dossiers: Iterable[str] | None) -> frozenset[str]:
    if dossiers is None:
        return frozenset({TOUS})
    return frozenset(str(d).strip() for d in dossiers if str(d).strip())


@dataclass
class Utilisateur:
    """Un porteur de jeton, ses rôles et son périmètre de dossiers.

    Non gelé volontairement : `regenerer()` doit pouvoir remplacer un jeton
    compromis. La protection contre les modifications accidentelles porte sur
    les champs qui comptent — `roles` et `dossiers` sont des `frozenset`, donc
    non modifiables en place. `public()` ne reprend jamais le jeton, et c'est
    la seule sortie autorisée vers l'extérieur.

    `jeton` est conservé ici pour la comparaison mais **jamais** exposé.
    """

    nom: str
    roles: frozenset[str]
    dossiers: frozenset[str] = frozenset({TOUS})
    jeton: str = field(default="", repr=False, compare=False)
    #: jeton d'environnement (passe-partout), pas un utilisateur du fichier
    environnement: bool = False

    def a_role(self, minimum: str) -> bool:
        """Le rôle demandé est-il couvert ?

        La hiérarchie compare les **niveaux**, pas les noms : un `operateur`
        couvre `lecteur` parce qu'il est plus haut dans l'ordre des rôles. Sans
        cette comparaison de niveaux, il faudrait répéter `lecteur` dans chaque
        rôle supérieur — et l'oublier une fois suffirait à fermer l'accès d'un
        superviseur à la simple consultation.
        """
        if minimum not in ROLES:
            raise RBACError("rôle demandé inconnu : %s" % minimum)
        return max(ROLES.index(r) for r in self.roles) >= ROLES.index(minimum)

    def voit_dossier(self, dossier_id: str) -> bool:
        """Ce dossier fait-il partie du périmètre ?

        Portée « tous » ou dossier listé. Une liste vide ne voit rien : le
        cloisonnement est fermé par défaut, un utilisateur sans affectation
        n'accède à aucun dossier plutôt qu'à tous par accident.
        """
        return TOUS in self.dossiers or dossier_id in self.dossiers

    def public(self) -> dict:
        """Représentation exposable — **sans le jeton**."""
        return {"nom": self.nom,
                "roles": sorted(self.roles),
                "dossiers": sorted(self.dossiers),
                "environnement": self.environnement}


@dataclass
class RegistreRBAC:
    """Utilisateurs connus, chargés depuis `data/rbac.json`."""

    chemin: Path | None = None
    utilisateurs: list[Utilisateur] = field(default_factory=list)
    actif: bool = False
    #: horodatage du dernier chargement, pour l'observabilité
    charge_a: float = 0.0

    # ─────────────────────────────── cycle de vie

    @classmethod
    def charger(cls, data_dir: Path) -> "RegistreRBAC":
        """Lit `data/rbac.json`. Absent = inactif, sans erreur.

        C'est le point qui garantit la compatibilité : un déploiement qui n'a
        jamais créé ce fichier obtient un registre inactif et rien d'autre ne
        change.
        """
        chemin = Path(data_dir) / "rbac.json"
        if not chemin.is_file():
            return cls(chemin=chemin, actif=False)
        try:
            data = json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RBACError("data/rbac.json illisible : %s" % exc) from exc
        return cls.depuis(data, chemin=chemin)

    @classmethod
    def depuis(cls, data: Any, chemin: Path | None = None) -> "RegistreRBAC":
        """Construit le registre depuis un dictionnaire (fichier ou test)."""
        if isinstance(data, list):        # forme courte : liste d'utilisateurs
            data = {"utilisateurs": data}
        if not isinstance(data, dict):
            raise RBACError("data/rbac.json doit être un objet")
        brut = data.get("utilisateurs") or []
        if not isinstance(brut, list):
            raise RBACError("« utilisateurs » doit être une liste")

        vus: dict[str, Utilisateur] = {}
        for entree in brut:
            if not isinstance(entree, dict):
                raise RBACError("chaque utilisateur doit être un objet")
            nom = str(entree.get("nom") or "").strip()
            jeton = str(entree.get("jeton") or "").strip()
            if not nom:
                raise RBACError("utilisateur sans nom")
            if not jeton:
                raise RBACError("utilisateur « %s » sans jeton" % nom)
            if nom in vus:
                raise RBACError("utilisateur en double : %s" % nom)
            vus[nom] = Utilisateur(nom=nom,
                                   roles=_roles_valides(entree.get("roles") or []),
                                   dossiers=_portee(entree.get("dossiers")),
                                   jeton=jeton)
        reg = cls(chemin=chemin, utilisateurs=list(vus.values()), actif=True,
                  charge_a=time.time())
        log.info("rôles chargés : %d utilisateur(s)", len(reg.utilisateurs))
        return reg

    # ─────────────────────────────── consultation

    def resoudre(self, jeton: str) -> Utilisateur | None:
        """Utilisateur porteur de ce jeton, ou None.

        La comparaison est à temps constant : sans cela, le temps de réponse
        renseignerait sur le jeton attendu.
        """
        jeton = (jeton or "").strip()
        if not jeton:
            return None
        trouve = None
        for u in self.utilisateurs:
            if not _compare(jeton, u.jeton):
                continue
            # deux jetons identiques : le premier gagne, mais on le dit —
            # un doublon silencieux rendrait la révocation incompréhensible
            if trouve is not None:
                log.warning("jeton en double entre %s et %s", trouve.nom, u.nom)
            trouve = trouve or u
        return trouve

    def liste(self) -> list[dict]:
        """Utilisateurs exposables — jetons exclus."""
        return [u.public() for u in self.utilisateurs]

    # ─────────────────────────────── écriture

    def ajouter(self, nom: str, roles: Iterable[str],
                dossiers: Iterable[str] | None = None) -> Utilisateur:
        """Crée un utilisateur et son jeton, puis persiste.

        Le jeton est généré ici, jamais fourni par l'appelant : un jeton faible
        ou réutilisé serait une faiblesse que l'appelant ne voit pas.
        """
        nom = str(nom).strip()
        if not nom:
            raise RBACError("nom requis")
        if any(u.nom == nom for u in self.utilisateurs):
            raise RBACError("utilisateur déjà existant : %s" % nom)
        jeton = secrets.token_urlsafe(24)
        u = Utilisateur(nom=nom, roles=_roles_valides(roles),
                        dossiers=_portee(dossiers), jeton=jeton)
        self.utilisateurs.append(u)
        self._persiste()
        return u

    def maj(self, nom: str, roles: Iterable[str] | None = None,
            dossiers: Iterable[str] | None = None) -> Utilisateur:
        """Modifie rôles et/ou périmètre d'un utilisateur existant."""
        u = self._trouve(nom)
        if roles is not None:
            u.roles = _roles_valides(roles)
        if dossiers is not None:
            u.dossiers = _portee(dossiers)
        self._persiste()
        return u

    def retirer(self, nom: str) -> bool:
        avant = len(self.utilisateurs)
        self.utilisateurs = [u for u in self.utilisateurs if u.nom != nom]
        if len(self.utilisateurs) == avant:
            return False
        self._persiste()
        return True

    def regenerer(self, nom: str) -> str:
        """Nouveau jeton pour un utilisateur existant (secret compromis)."""
        u = self._trouve(nom)
        u.jeton = secrets.token_urlsafe(24)
        self._persiste()
        return u.jeton

    # ─────────────────────────────── interne

    def _trouve(self, nom: str) -> Utilisateur:
        for u in self.utilisateurs:
            if u.nom == nom:
                return u
        raise RBACError("utilisateur introuvable : %s" % nom)

    def _persiste(self) -> None:
        """Réécrit `data/rbac.json` avec les jetons courants.

        Écriture atomique (fichier temporaire + renommage) : une coupure en
        plein milieu ne doit pas laisser un registre à moitié écrit, donc sans
        aucun utilisateur — ce qui fermerait tout l'accès.
        """
        if self.chemin is None:
            raise RBACError("aucun chemin de persistance configuré")
        lignes = [{"nom": u.nom, "roles": sorted(u.roles),
                   "dossiers": sorted(u.dossiers), "jeton": u.jeton}
                  for u in self.utilisateurs]
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.chemin.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"utilisateurs": lignes}, ensure_ascii=False,
                                  indent=1), encoding="utf-8")
        tmp.replace(self.chemin)
        try:
            self.chemin.chmod(0o600)     # contient des secrets
        except OSError:
            pass


def _compare(a: str, b: str) -> bool:
    """Comparaison à temps constant, sûre même si `b` est vide."""
    if not b:
        return False
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
