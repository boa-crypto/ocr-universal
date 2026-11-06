"""Revue administrative en lecture seule ; aucun chemin fourni par HTTP."""
import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from ..customs_reference.article_detail import (
    MAX_DECALAGE_TEXTE,
    MAX_FRAGMENT,
    ParamArticleInvalide,
    consulter_article,
)
from ..customs_reference.comparison import charger_lot, comparer_lots
from ..customs_reference.coverage import diagnostiquer_couverture
from ..customs_reference.history import ParamHistoriqueInvalide, historique_article
from ..customs_reference.importer import _lire
from ..customs_reference.legal_comparison import charger_lot_code, comparer_lots_code
from ..customs_reference.review_registry import (
    IDENTIFIANT,
    RegistreRevueIndisponible,
    charger_registre,
)
from ..customs_reference.search import ParamRechercheInvalide, rechercher_code, rechercher_tarif
from ..customs_reference.tariff_detail import ParamFicheTarifInvalide, consulter_code
from ..customs_reference.tariff_tree import ParamArbreTarifInvalide, parcourir_tarif
from ..logging_setup import AuditIndisponible

NO_STORE = {"Cache-Control": "no-store"}


def creer_router_revue(autoriser, chemin_registre, tracer):
    router = APIRouter(prefix="/api/v1/customs-review", tags=["customs-review"])

    def tracer_operation(obligatoire=False, **champs):
        try:
            tracer(**champs)
        except AuditIndisponible:
            if obligatoire:
                raise HTTPException(503, {"code": "audit_revue_indisponible"}, headers=NO_STORE) from None
            # Ne pas transformer un refus d'accès ou de lot en succès si l'audit échoue.

    def executer(utilisateur, operation, ids, action):
        try:
            path = Path(chemin_registre())
            registre = charger_registre(path)
            if utilisateur.nom not in registre.reviseurs:
                raise HTTPException(403, {"code": "reviseur_non_habilite"}, headers=NO_STORE)
            par_id = {lot.id: lot for lot in registre.lots}
            if any(identifiant not in par_id for identifiant in ids):
                raise HTTPException(404, {"code": "lot_revue_inconnu"}, headers=NO_STORE)
            entrees = [par_id[identifiant] for identifiant in ids]
            if len({lot.type_lot for lot in entrees}) > 1:
                raise HTTPException(422, {"code": "types_lots_incompatibles"}, headers=NO_STORE)
            # dossier est un nom simple strictement validé dans la configuration.
            dossiers = [path.parent / lot.dossier for lot in entrees]
            for entree, dossier in zip(entrees, dossiers):
                if dossier.is_symlink() or not dossier.is_dir():
                    raise ValueError("Dossier enregistré absent ou symbolique")
                if hashlib.sha256(_lire(dossier / "manifest.json")).hexdigest() != entree.manifest_sha256:
                    raise ValueError("Manifeste différent avant traitement")
            resultat = action(entrees, dossiers, registre)
            if entrees:
                archives = ([resultat["archive"]] if len(entrees) == 1
                            else [resultat["archives"]["avant"], resultat["archives"]["apres"]])
                if any(archive["manifest_sha256"] != entree.manifest_sha256 for archive, entree in zip(archives, entrees)):
                    raise ValueError("Manifeste lu différent de l'empreinte épinglée")
            reponse = JSONResponse({"lecture_seule": True, "publication_active": False,
                                 "validation_juridique": "non_validee", "perimetre": "revue_administrative_quarantaine",
                                 "resultat": resultat}, headers=NO_STORE)
        except ParamArticleInvalide:
            statut, code = 422, "parametres_lecture_article_invalides"
        except ParamArbreTarifInvalide:
            statut, code = 422, "parametres_navigation_tarif_invalides"
        except ParamFicheTarifInvalide:
            statut, code = 422, "parametres_fiche_tarif_invalides"
        except ParamHistoriqueInvalide:
            statut, code = 422, "parametres_historique_invalides"
        except ParamRechercheInvalide:
            statut, code = 422, "parametres_recherche_invalides"
        except RegistreRevueIndisponible:
            statut, code = 503, "registre_revue_indisponible"
        except HTTPException as exc:
            tracer_operation(operation=operation, acteur=utilisateur.nom, lots=ids, statut=exc.status_code)
            raise
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            statut, code = 409, "lot_revue_incoherent_ou_empreinte_modifiee"
        else:
            # Réponse sérialisée avant l'événement ; aucun contenu métier libéré si
            # l'append/synchronisation échoue. Cela ne garantit pas sa livraison réseau.
            tracer_operation(obligatoire=True, operation=operation, acteur=utilisateur.nom, lots=ids, statut=200,
                             manifestes={lot.id: lot.manifest_sha256 for lot in entrees})
            return reponse
        tracer_operation(operation=operation, acteur=utilisateur.nom, lots=ids, statut=statut)
        # Ni chemin local ni texte de validation ni contenu de document dans l'erreur.
        raise HTTPException(statut, {"code": code}, headers=NO_STORE)

    @router.get("/lots")
    def lots(utilisateur=Depends(autoriser)):
        def lister(entrees, dossiers, registre):
            return {"lots": [{"id": lot.id, "type_lot": lot.type_lot, "manifest_sha256_attendu": lot.manifest_sha256}
                             for lot in registre.lots], "integrite_lots": "non_controlee_par_la_liste"}
        return executer(utilisateur, "liste", [], lister)

    @router.get("/lots/{lot_id}/check")
    def controler(lot_id: str, utilisateur=Depends(autoriser)):
        return executer(utilisateur, "controle", [lot_id], lambda e, p, registre:
                        (charger_lot(p[0]) if e[0].type_lot == "tarif" else charger_lot_code(p[0]))[1])

    @router.get("/lots/{lot_id}/coverage")
    def couverture(lot_id: str, utilisateur=Depends(autoriser)):
        return executer(utilisateur, "couverture", [lot_id], lambda e, p, registre:
                        diagnostiquer_couverture(p[0], e[0].type_lot))

    @router.get("/lots/{lot_id}/search")
    def chercher(lot_id: str, q: str = Query("", max_length=256),
                 limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=1_000_000),
                 article: str | None = Query(None, min_length=1, max_length=256),
                 source: str | None = Query(None, min_length=1, max_length=256),
                 nature: str | None = Query(None, max_length=32), utilisateur=Depends(autoriser)):
        def chercher_lot(e, p, registre):
            if e[0].type_lot == "tarif":
                if any(v is not None for v in (article, source, nature)):
                    raise HTTPException(422, {"code": "filtres_code_non_applicables_au_tarif"}, headers=NO_STORE)
                return rechercher_tarif(p[0], q, limit, offset)
            return rechercher_code(p[0], q, limit, offset, article, source, nature)
        return executer(utilisateur, "recherche", [lot_id], chercher_lot)

    @router.get("/lots/{lot_id}/history")
    def historique(lot_id: str, article: str = Query(..., min_length=1, max_length=256),
                   limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=1_000_000),
                   relations_limit: int = Query(20, ge=1, le=100),
                   relations_offset: int = Query(0, ge=0, le=1_000_000), utilisateur=Depends(autoriser)):
        def lire_historique(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "historique_code_non_applicable_au_tarif"}, headers=NO_STORE)
            return historique_article(p[0], article, limit, offset, relations_limit, relations_offset)
        return executer(utilisateur, "historique", [lot_id], lire_historique)

    @router.get("/lots/{lot_id}/tariff/{code10}")
    def fiche_tarif(lot_id: str, code10: str, measures_limit: int = Query(20, ge=1, le=100),
                    measures_offset: int = Query(0, ge=0, le=1_000_000), utilisateur=Depends(autoriser)):
        def lire_fiche(e, p, registre):
            if e[0].type_lot != "tarif":
                raise HTTPException(422, {"code": "fiche_tarif_non_applicable_au_code_documentaire"}, headers=NO_STORE)
            return consulter_code(p[0], code10, measures_limit, measures_offset)
        return executer(utilisateur, "fiche_tarif", [lot_id], lire_fiche)

    @router.get("/lots/{lot_id}/tree")
    def arbre_tarif(lot_id: str, level: str = Query("sections", max_length=32),
                    parent: str | None = Query(None, min_length=1, max_length=256),
                    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=1_000_000),
                    utilisateur=Depends(autoriser)):
        def lire_arbre(e, p, registre):
            if e[0].type_lot != "tarif":
                raise HTTPException(422, {"code": "navigation_tarif_non_applicable_au_code_documentaire"}, headers=NO_STORE)
            return parcourir_tarif(p[0], level, parent, limit, offset)
        return executer(utilisateur, "navigation_tarif", [lot_id], lire_arbre)

    @router.get("/lots/{lot_id}/article")
    def lire_article(lot_id: str, article_id: str = Query(..., min_length=1, max_length=256),
                     field: str = Query("texte_integral", max_length=32),
                     limit: int = Query(4000, ge=1, le=MAX_FRAGMENT),
                     offset: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE), utilisateur=Depends(autoriser)):
        def lire_version(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "lecture_article_non_applicable_au_tarif"}, headers=NO_STORE)
            return consulter_article(p[0], article_id, field, limit, offset)
        return executer(utilisateur, "lecture_article", [lot_id], lire_version)

    @router.get("/diff")
    def comparer(avant: str = Query(..., pattern=IDENTIFIANT), apres: str = Query(..., pattern=IDENTIFIANT),
                 utilisateur=Depends(autoriser)):
        return executer(utilisateur, "comparaison", [avant, apres], lambda e, p, registre:
                        comparer_lots(*p) if e[0].type_lot == "tarif" else comparer_lots_code(*p))

    return router
