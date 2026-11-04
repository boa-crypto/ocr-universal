"""Dépendances partagées pour les routes — évite les imports circulaires."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, Request

from ..logging_setup import audit, get_logger
from ..rbac import ADMINISTRATEUR, LECTEUR, OPERATEUR, SUPERVISEUR, TOUS, Utilisateur

log = get_logger("deps")


def get_config(request: Request) -> Any:
    """Fournit la configuration de l'application via l'état de la requête."""
    return request.app.state.cfg


def _utilisateur_courant(request: Request):
    """Utilisateur résolu par le middleware, ou None si RBAC inactif."""
    return getattr(request.state, "utilisateur", None)


def utilisateur_ouvert() -> Utilisateur:
    """Utilisateur permissif utilisé quand `data/rbac.json` est absent.

    Sans fichier de rôles, le poste est ouvert : les routes doivent pouvoir
    journaliser un acteur (`u.nom`) et consulter le périmètre sans planter.
    """
    return Utilisateur(nom="local", roles=frozenset({ADMINISTRATEUR}),
                       dossiers=frozenset({TOUS}))


def _utilisateur_ou_ouvert(request: Request) -> Utilisateur:
    """Utilisateur courant, ou utilisateur ouvert si le RBAC est inactif."""
    return _utilisateur_courant(request) or utilisateur_ouvert()


# ───────────────────────────────────────────────────────────────
# Dépendances RBAC

def _exige(role: str):
    """Dépendance FastAPI : la route exige ce rôle au minimum.

    Quand RBAC est inactif, la dépendance laisse passer : sans fichier de
    rôles, aucune route ne se ferme. Quand il est actif, un rôle insuffisant
    est refusé **et tracé** — un refus non tracé ne se distingue pas d'un bug.
    """
    def dependance(request: Request) -> Optional[Utilisateur]:
        u = _utilisateur_courant(request)
        if u is None:
            # RBAC inactif : accès ouvert, mais on renvoie quand même un acteur
            # pour que les routes puissent journaliser sans tester None.
            return utilisateur_ouvert()
        if u.a_role(role):
            return u
        audit(request.app.state.cfg.log_dir, "acces_refuse_role", route=request.url.path,
              methode=request.method, acteur=u.nom,
              roles=sorted(u.roles), requis=role)
        log.warning("accès refusé : %s sur %s (rôle %s requis, a %s)",
                    u.nom, request.url.path, role, sorted(u.roles))
        raise HTTPException(403, "rôle « %s » requis" % role)

    return dependance


def _exige_dossier(dossier_id: str, request) -> None:
    """Refuse l'accès à un dossier hors du périmètre de l'utilisateur.

    Renvoie 403 et non 404 : dans un outil local dont la liste d'utilisateurs
    est explicite, révéler l'existence d'un dossier n'apporte rien à un
    attaquant, alors qu'un message clair évite à l'opérateur de croire à un
    dossier perdu.
    """
    u = _utilisateur_courant(request)
    if u is None or u.voit_dossier(dossier_id):
        return
    audit(request.app.state.cfg.log_dir, "acces_refuse_dossier", route=request.url.path,
          methode=request.method, acteur=u.nom, dossier=dossier_id)
    log.warning("accès refusé : %s sur le dossier %s (hors périmètre)",
                u.nom, dossier_id)
    raise HTTPException(403, "dossier hors de votre périmètre")


# ───────────────────────────────────────────────────────────────
# Raccourcis pour les rôles courants

ExigeAdmin = Depends(_exige(ADMINISTRATEUR))
ExigeSuperviseur = Depends(_exige(SUPERVISEUR))
ExigeOperateur = Depends(_exige(OPERATEUR))
ExigeLecteur = Depends(_exige(LECTEUR))
