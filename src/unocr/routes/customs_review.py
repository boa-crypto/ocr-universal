"""Revue de quarantaine et propositions métier, sans publication ni chemin HTTP."""
import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from ..customs_reference.article_detail import (
    MAX_DECALAGE_TEXTE,
    MAX_FRAGMENT,
    ParamArticleInvalide,
    consulter_article,
)
from ..customs_reference.article_diff import ParamDiffArticleInvalide, comparer_versions_article
from ..customs_reference.article_pdf_match import (
    ParamRapprochementInvalide,
    rapprocher_fragment_article_pdf,
)
from ..customs_reference.article_relations import (
    ParamRelationsArticleInvalide,
    consulter_relations_article,
)
from ..customs_reference.assessment import (
    CreationDossier,
    DossierInconnu,
    DossierRefuse,
    MagasinDossiers,
    ProduitDeclare,
    RevisionDossier,
    RevisionDossierConflict,
    preparer_diagnostic,
)
from ..customs_reference.code_tree import ParamArbreCodeInvalide, parcourir_code
from ..customs_reference.comparison import charger_lot, comparer_lots
from ..customs_reference.coverage import diagnostiquer_couverture
from ..customs_reference.fiscal_importer import charger_lot_mesures
from ..customs_reference.fiscal_pdf_page import lire_page_pdf_mesures
from ..customs_reference.history import ParamHistoriqueInvalide, historique_article
from ..customs_reference.importer import _lire
from ..customs_reference.legal_comparison import charger_lot_code, comparer_lots_code
from ..customs_reference.measure_pdf_match import (
    ParamRapprochementMesureInvalide,
    rapprocher_description_mesure_pdf,
)
from ..customs_reference.measure_search import rechercher_mesures_tarif
from ..customs_reference.pdf_page import LecturePDFRefusee, ParamPDFInvalide, lire_page_pdf
from ..customs_reference.relation_pdf_match import (
    ParamJustificationPDFInvalide,
    rapprocher_justification_pdf,
)
from ..customs_reference.review_registry import (
    IDENTIFIANT,
    RegistreRevueIndisponible,
    charger_registre,
)
from ..customs_reference.search import ParamRechercheInvalide, rechercher_code, rechercher_tarif
from ..customs_reference.source_catalog import inventorier_sources
from ..customs_reference.source_pdf import copier_pdf_source
from ..customs_reference.tariff_candidates import rechercher_pistes_tarifaires
from ..customs_reference.tariff_criteria import rechercher_tarif_criteres
from ..customs_reference.tariff_detail import ParamFicheTarifInvalide, consulter_code
from ..customs_reference.tariff_measures import juxtaposer_tarif_mesures
from ..customs_reference.tariff_pair import juxtaposer_fiches_tarifaires
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

    def executer(utilisateur, operation, ids, action, preparer_reponse=None):
        try:
            path = Path(chemin_registre())
            registre = charger_registre(path)
            if utilisateur.nom not in registre.reviseurs:
                raise HTTPException(403, {"code": "reviseur_non_habilite"}, headers=NO_STORE)
            par_id = {lot.id: lot for lot in registre.lots}
            if any(identifiant not in par_id for identifiant in ids):
                raise HTTPException(404, {"code": "lot_revue_inconnu"}, headers=NO_STORE)
            entrees = [par_id[identifiant] for identifiant in ids]
            paire_mesures = operation == "consultation_tarif_mesures" and [v.type_lot for v in entrees] == ["tarif", "mesures"]
            if operation == "consultation_tarif_mesures" and not paire_mesures:
                raise HTTPException(422, {"code":"paire_tarif_mesures_requise"}, headers=NO_STORE)
            if any(lot.type_lot == "mesures" for lot in entrees) and not paire_mesures and operation not in {
                    "controle", "recherche_mesures", "inventaire_sources", "couverture", "lecture_pdf_mesures", "rapprochement_mesure_pdf"}:
                raise HTTPException(422, {"code":"operation_non_applicable_aux_mesures_autonomes"}, headers=NO_STORE)
            if len({lot.type_lot for lot in entrees}) > 1 and not paire_mesures:
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
            reponse = preparer_reponse(resultat) if preparer_reponse else JSONResponse({"lecture_seule": operation not in {"creation_dossier_metier", "revision_dossier_metier"}, "publication_active": False,
                                 "validation_juridique": "non_validee", "perimetre": "revue_administrative_quarantaine",
                                 "resultat": resultat}, headers=NO_STORE)
        except ParamRapprochementMesureInvalide:
            statut, code = 422, "parametres_rapprochement_mesure_pdf_invalides"
        except ParamRapprochementInvalide:
            statut, code = 422, "parametres_rapprochement_article_pdf_invalides"
        except ParamJustificationPDFInvalide:
            statut, code = 422, "parametres_justification_pdf_invalides"
        except ParamRelationsArticleInvalide:
            statut, code = 422, "parametres_relations_article_invalides"
        except ParamArbreCodeInvalide:
            statut, code = 422, "parametres_navigation_code_invalides"
        except ParamDiffArticleInvalide:
            statut, code = 422, "parametres_diff_articles_invalides"
        except ParamPDFInvalide:
            statut, code = 422, "parametres_lecture_pdf_invalides"
        except LecturePDFRefusee:
            statut, code = 409, "pdf_recu_non_lisible_ou_hors_limites"
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
                        {"tarif":charger_lot, "code":charger_lot_code, "mesures":charger_lot_mesures}[e[0].type_lot](p[0])[1])

    @router.get("/lots/{lot_id}/measure-search")
    def mesures(lot_id: str, q: str = Query("", max_length=256), code10: str | None = Query(None, max_length=10),
                measure_type: str | None = Query(None, max_length=16), limit: int = Query(20, ge=1, le=100),
                offset: int = Query(0, ge=0, le=1_000_000), utilisateur=Depends(autoriser)):
        def chercher(e, p, registre):
            if e[0].type_lot not in {"tarif", "mesures"}:
                raise HTTPException(422, {"code": "recherche_mesures_non_applicable_au_code"}, headers=NO_STORE)
            return rechercher_mesures_tarif(p[0], q, code10, measure_type, limit, offset, e[0].type_lot)
        return executer(utilisateur, "recherche_mesures", [lot_id], chercher)

    @router.get("/lots/{lot_id}/pdf-source")
    def fichier_pdf(lot_id: str, document_id: str = Query(..., min_length=1, max_length=256), utilisateur=Depends(autoriser)):
        fichier = {}

        def lire_fichier(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "copie_pdf_code_uniquement"}, headers=NO_STORE)
            resultat, contenu = copier_pdf_source(p[0], document_id)
            fichier["octets"] = contenu
            return resultat

        def reponse_fichier(resultat):
            contenu = fichier["octets"]
            sha = hashlib.sha256(contenu).hexdigest()
            nom = f"uniocr-source-non-validee-{sha}.pdf"
            if (sha != resultat["sha256_pdf_copie"] or sha != resultat["document_declare"]["sha256"]
                    or len(contenu) != resultat["taille_octets"] or nom != resultat["nom_telechargement"]):
                raise ValueError("Copie binaire différente du rapport contrôlé")
            return Response(contenu, media_type="application/pdf", headers={**NO_STORE,
                "Content-Disposition": f'attachment; filename="{nom}"', "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "sandbox; default-src 'none'",
                "X-UniOCR-Source-SHA256": sha, "X-UniOCR-Manifest-SHA256": resultat["archive"]["manifest_sha256"],
                "X-UniOCR-Validation": "non_validee"})

        return executer(utilisateur, "copie_pdf_source", [lot_id], lire_fichier, reponse_fichier)

    @router.get("/lots/{lot_id}/sources")
    def sources(lot_id: str, q: str = Query("", max_length=256),
                source_id: str | None = Query(None, min_length=1, max_length=256),
                nature_document: str | None = Query(None, max_length=32),
                limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=1_000_000),
                utilisateur=Depends(autoriser)):
        return executer(utilisateur, "inventaire_sources", [lot_id], lambda e, p, registre:
                        inventorier_sources(p[0], e[0].type_lot, q, source_id, nature_document, limit, offset))

    @router.get("/lots/{lot_id}/coverage")
    def couverture(lot_id: str, utilisateur=Depends(autoriser)):
        return executer(utilisateur, "couverture", [lot_id], lambda e, p, registre:
                        diagnostiquer_couverture(p[0], e[0].type_lot))

    def dossier_metier(utilisateur, lot_id, dossier_id, operation, body=None, version=None):
        def agir(entrees, dossiers, registre):
            entree = entrees[0]
            if entree.type_lot != "tarif":
                raise HTTPException(422, {"code": "dossier_tarif_uniquement"}, headers=NO_STORE)
            magasin = MagasinDossiers(Path(chemin_registre()).parent / "dossiers_metier.sqlite3")
            try:
                if operation == "creation_dossier_metier":
                    produit = body.produit
                else:
                    if operation == "lecture_dossier_metier":
                        _, controle = charger_lot(dossiers[0])
                        if controle["archive"]["manifest_sha256"] != entree.manifest_sha256:
                            raise RevisionDossierConflict("Source modifiée")
                    precedent = magasin.lire(dossier_id, lot_id, entree.manifest_sha256,
                                             historique=operation == "lecture_dossier_metier" and version is None, version=version)
                    produit = (body.produit if body and body.produit is not None else
                               ProduitDeclare.model_validate(precedent["diagnostic"]["produit_declare"]))
                    if operation == "lecture_dossier_metier":
                        magasin.reconcilier_audit(dossier_id, lot_id, entree.manifest_sha256,
                            lambda **champs: tracer_operation(obligatoire=True, operation="version_dossier_metier",
                                                             lots=[lot_id], statut=200, **champs))
                        return precedent
                diagnostic = preparer_diagnostic(dossiers[0], produit)
                if diagnostic["recherche"]["archive"]["manifest_sha256"] != entree.manifest_sha256:
                    raise RevisionDossierConflict("Source modifiée avant sauvegarde")
                document = magasin.enregistrer(dossier_id, lot_id, entree.manifest_sha256, diagnostic,
                                           utilisateur.nom, body if isinstance(body, RevisionDossier) else None,
                                           pieces_techniques=body.pieces_techniques if isinstance(body, CreationDossier) else None)
                magasin.reconcilier_audit(dossier_id, lot_id, entree.manifest_sha256,
                    lambda **champs: tracer_operation(obligatoire=True, operation="version_dossier_metier",
                                                     lots=[lot_id], statut=200, **champs))
                return document
            except DossierInconnu:
                raise HTTPException(404, {"code": "dossier_metier_inconnu"}, headers=NO_STORE) from None
            except RevisionDossierConflict:
                raise HTTPException(409, {"code": "revision_dossier_metier_conflictuelle"}, headers=NO_STORE) from None
            except DossierRefuse:
                raise HTTPException(422, {"code": "dossier_metier_refuse"}, headers=NO_STORE) from None
            except (sqlite3.Error, OSError):
                raise HTTPException(503, {"code": "stockage_dossier_metier_indisponible"}, headers=NO_STORE) from None
        return executer(utilisateur, operation, [lot_id], agir)

    @router.post("/lots/{lot_id}/assessments")
    def creer_dossier_metier(lot_id: str, body: CreationDossier, utilisateur=Depends(autoriser)):
        return dossier_metier(utilisateur, lot_id, body.dossier_id, "creation_dossier_metier", body)

    @router.get("/lots/{lot_id}/assessments/{dossier_id}")
    def lire_dossier_metier(lot_id: str, dossier_id: str, version: int | None = Query(None, ge=1, le=100),
                           utilisateur=Depends(autoriser)):
        return dossier_metier(utilisateur, lot_id, dossier_id, "lecture_dossier_metier", version=version)

    @router.patch("/lots/{lot_id}/assessments/{dossier_id}")
    def reviser_dossier_metier(lot_id: str, dossier_id: str, body: RevisionDossier,
                             utilisateur=Depends(autoriser)):
        return dossier_metier(utilisateur, lot_id, dossier_id, "revision_dossier_metier", body)

    @router.get("/lots/{lot_id}/tariff-candidates")
    def pistes_tarif(lot_id: str, request: Request, designation: str | None = Query(None,max_length=256),
                     matiere: str | None = Query(None,max_length=256), fonction: str | None = Query(None,max_length=256),
                     usage: str | None = Query(None,max_length=256), caracteristiques: str | None = Query(None,max_length=256),
                     code_prefix: str | None = Query(None,max_length=10),
                     match_mode: Literal["sous_chaine", "mots_entiers"] = Query("sous_chaine"),
                     limit: int = Query(20,ge=1,le=100), offset: int = Query(0,ge=0,le=1_000_000),
                     utilisateur=Depends(autoriser)):
        def chercher(e,p,registre):
            if e[0].type_lot != "tarif":
                raise HTTPException(422, {"code":"pistes_tarif_uniquement"},headers=NO_STORE)
            autorises = {"designation","matiere","fonction","usage","caracteristiques",
                         "code_prefix","match_mode","limit","offset"}
            try:
                brut = request.scope["query_string"].decode("ascii")
                if re.search(r"%(?![0-9a-fA-F]{2})",brut):
                    raise ValueError("Encodage incompatible")
                paires = parse_qsl(brut,keep_blank_values=True,strict_parsing=True,
                                   max_num_fields=9,encoding="utf-8",errors="strict")
            except (ValueError,UnicodeError):
                raise ParamRechercheInvalide("Requête explicite compatible requise") from None
            if (any(c not in autorises for c,v in paires) or len({c for c,v in paires}) != len(paires)
                    or any(re.fullmatch(r"[0-9]{1,7}",v) is None for c,v in paires if c in {"limit","offset"})):
                raise ParamRechercheInvalide("Paramètres explicites uniques requis")
            return rechercher_pistes_tarifaires(p[0],designation=designation,matiere=matiere,fonction=fonction,
                usage=usage,caracteristiques=caracteristiques,code_prefix=code_prefix,limite=limit,decalage=offset,match_mode=match_mode)
        return executer(utilisateur,"recherche_pistes_tarifaires",[lot_id],chercher)

    @router.get("/lots/{lot_id}/tariff-criteria")
    def criteres_tarif(lot_id: str, designation: str | None = Query(None,max_length=256),
                      matiere: str | None = Query(None,max_length=256), fonction: str | None = Query(None,max_length=256),
                      usage: str | None = Query(None,max_length=256), caracteristiques: str | None = Query(None,max_length=256),
                      code_prefix: str | None = Query(None,max_length=10),
                      match_mode: Literal["sous_chaine", "mots_entiers"] = Query("sous_chaine"),
                      limit: int = Query(20,ge=1,le=100),
                      offset: int = Query(0,ge=0,le=1_000_000), utilisateur=Depends(autoriser)):
        def chercher(e,p,registre):
            if e[0].type_lot != "tarif":
                raise HTTPException(422, {"code":"criteres_tarif_uniquement"},headers=NO_STORE)
            return rechercher_tarif_criteres(p[0],designation=designation,matiere=matiere,fonction=fonction,
                usage=usage,caracteristiques=caracteristiques,code_prefix=code_prefix,limite=limit,decalage=offset,match_mode=match_mode)
        return executer(utilisateur,"recherche_tarif_criteres",[lot_id],chercher)

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

    @router.get("/lots/{lot_id}/relation-pdf-match")
    def justification_pdf(lot_id: str, relation_id: str = Query(..., min_length=1, max_length=256),
                          page: int = Query(..., ge=1, le=10000), limit: int = Query(4000, ge=1, le=MAX_FRAGMENT),
                          offset: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE), utilisateur=Depends(autoriser)):
        def constater(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "justification_pdf_non_applicable_au_tarif"}, headers=NO_STORE)
            return rapprocher_justification_pdf(p[0], relation_id, page, limit, offset)
        return executer(utilisateur, "rapprochement_justification_pdf", [lot_id], constater)

    @router.get("/lots/{lot_id}/article-relations")
    def relations_article(lot_id: str, article_id: str = Query(..., min_length=1, max_length=256),
                          direction: str = Query("tous", max_length=16), relation_type: str | None = Query(None, max_length=16),
                          limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=1_000_000),
                          utilisateur=Depends(autoriser)):
        def consulter(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "relations_article_non_applicables_au_tarif"}, headers=NO_STORE)
            return consulter_relations_article(p[0], article_id, direction, relation_type, limit, offset)
        return executer(utilisateur, "relations_article", [lot_id], consulter)

    @router.get("/lots/{lot_id}/article-pdf-match")
    def rapprochement(lot_id: str, article_id: str = Query(..., min_length=1, max_length=256),
                      page: int = Query(..., ge=1, le=10000), field: str = Query("texte_integral", max_length=32),
                      limit: int = Query(4000, ge=1, le=MAX_FRAGMENT),
                      offset: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE), utilisateur=Depends(autoriser)):
        def constater(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "rapprochement_article_pdf_non_applicable_au_tarif"}, headers=NO_STORE)
            return rapprocher_fragment_article_pdf(p[0], article_id, page, field, limit, offset)
        return executer(utilisateur, "rapprochement_article_pdf", [lot_id], constater)

    @router.get("/lots/{lot_id}/code-tree")
    def arbre_code(lot_id: str, source_id: str | None = Query(None, max_length=256),
                   path: str = Query("[]", max_length=8192), limit: int = Query(20, ge=1, le=100),
                   offset: int = Query(0, ge=0, le=1_000_000), utilisateur=Depends(autoriser)):
        def parcourir(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "navigation_code_non_applicable_au_tarif"}, headers=NO_STORE)
            return parcourir_code(p[0], source_id, path, limit, offset)
        return executer(utilisateur, "navigation_code", [lot_id], parcourir)

    @router.get("/lots/{lot_id}/article-diff")
    def diff_articles(lot_id: str, avant_id: str = Query(..., min_length=1, max_length=256),
                      apres_id: str = Query(..., min_length=1, max_length=256), field: str = Query("texte_integral", max_length=32),
                      limit: int = Query(4000, ge=1, le=MAX_FRAGMENT),
                      offset_avant: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE),
                      offset_apres: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE), utilisateur=Depends(autoriser)):
        def comparer(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "diff_articles_non_applicable_au_tarif"}, headers=NO_STORE)
            return comparer_versions_article(p[0], avant_id, apres_id, field, limit, offset_avant, offset_apres)
        return executer(utilisateur, "diff_articles", [lot_id], comparer)

    @router.get("/lots/{lot_id}/pdf")
    def lire_pdf(lot_id: str, document_id: str = Query(..., min_length=1, max_length=256),
                 page: int = Query(1, ge=1, le=10000), limit: int = Query(4000, ge=1, le=MAX_FRAGMENT),
                 offset: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE), utilisateur=Depends(autoriser)):
        def lire_document(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "lecture_pdf_non_applicable_au_tarif"}, headers=NO_STORE)
            return lire_page_pdf(p[0], document_id, page, limit, offset)
        return executer(utilisateur, "lecture_pdf", [lot_id], lire_document)

    @router.get("/lots/{lot_id}/measure-pdf-match")
    def mesure_pdf(lot_id: str, mesure_id: str = Query(..., min_length=1, max_length=256),
                   page: int = Query(1, ge=1, le=10000), limit: int = Query(4000, ge=1, le=MAX_FRAGMENT),
                   offset: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE), utilisateur=Depends(autoriser)):
        def constater(e,p,registre):
            if e[0].type_lot != "mesures":
                raise HTTPException(422, {"code":"rapprochement_mesure_pdf_uniquement"}, headers=NO_STORE)
            return rapprocher_description_mesure_pdf(p[0],mesure_id,page,limit,offset)
        return executer(utilisateur,"rapprochement_mesure_pdf",[lot_id],constater)

    @router.get("/lots/{lot_id}/fiscal-pdf")
    def lire_pdf_fiscal(lot_id: str, document_id: str = Query(..., min_length=1, max_length=256),
                       page: int = Query(1, ge=1, le=10000), limit: int = Query(4000, ge=1, le=MAX_FRAGMENT),
                       offset: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE), utilisateur=Depends(autoriser)):
        def lire_document(e, p, registre):
            if e[0].type_lot != "mesures":
                raise HTTPException(422, {"code":"lecture_pdf_mesures_uniquement"}, headers=NO_STORE)
            return lire_page_pdf_mesures(p[0],document_id,page,limit,offset)
        return executer(utilisateur,"lecture_pdf_mesures",[lot_id],lire_document)

    @router.get("/tariff-measures")
    def tarif_mesures(tarif: str = Query(..., pattern=IDENTIFIANT), mesures: str = Query(..., pattern=IDENTIFIANT),
                      code10: str = Query(..., min_length=10, max_length=10),
                      tariff_limit: int = Query(20, ge=1, le=100), tariff_offset: int = Query(0, ge=0, le=1_000_000),
                      measures_limit: int = Query(20, ge=1, le=100), measures_offset: int = Query(0, ge=0, le=1_000_000),
                      utilisateur=Depends(autoriser)):
        def consulter(e, p, registre):
            resultat = juxtaposer_tarif_mesures(p[0], p[1], code10, tariff_limit, tariff_offset, measures_limit, measures_offset)
            resultat["lots_exacts"] = {"tarif":tarif, "mesures":mesures}
            return resultat
        return executer(utilisateur, "consultation_tarif_mesures", [tarif, mesures], consulter)

    @router.get("/tariff-compare")
    def fiches_tarifaires(avant: str = Query(..., pattern=IDENTIFIANT), apres: str = Query(..., pattern=IDENTIFIANT),
                         code10: str = Query(..., min_length=10, max_length=10),
                         before_limit: int = Query(20, ge=1, le=100), before_offset: int = Query(0, ge=0, le=1_000_000),
                         after_limit: int = Query(20, ge=1, le=100), after_offset: int = Query(0, ge=0, le=1_000_000),
                         utilisateur=Depends(autoriser)):
        def juxtaposer(e, p, registre):
            if e[0].type_lot != "tarif":
                raise HTTPException(422, {"code": "fiches_tarifaires_non_applicables_au_code"}, headers=NO_STORE)
            resultat = juxtaposer_fiches_tarifaires(p[0], p[1], code10, before_limit, before_offset, after_limit, after_offset)
            resultat["lots_exacts"] = {"avant": avant, "apres": apres}
            return resultat
        return executer(utilisateur, "juxtaposition_fiches_tarifaires", [avant, apres], juxtaposer)

    @router.get("/article-diff")
    def diff_articles_inter_lots(avant: str = Query(..., pattern=IDENTIFIANT), apres: str = Query(..., pattern=IDENTIFIANT),
                                avant_id: str = Query(..., min_length=1, max_length=256),
                                apres_id: str = Query(..., min_length=1, max_length=256),
                                field: str = Query("texte_integral", max_length=32),
                                limit: int = Query(4000, ge=1, le=MAX_FRAGMENT),
                                offset_avant: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE),
                                offset_apres: int = Query(0, ge=0, le=MAX_DECALAGE_TEXTE), utilisateur=Depends(autoriser)):
        def comparer(e, p, registre):
            if e[0].type_lot != "code":
                raise HTTPException(422, {"code": "diff_articles_non_applicable_au_tarif"}, headers=NO_STORE)
            resultat = comparer_versions_article(p[0], avant_id, apres_id, field, limit, offset_avant, offset_apres, p[1])
            resultat["lots_exacts"] = {"avant": avant, "apres": apres}
            return resultat
        return executer(utilisateur, "diff_articles_inter_lots", [avant, apres], comparer)

    @router.get("/diff")
    def comparer(avant: str = Query(..., pattern=IDENTIFIANT), apres: str = Query(..., pattern=IDENTIFIANT),
                 utilisateur=Depends(autoriser)):
        return executer(utilisateur, "comparaison", [avant, apres], lambda e, p, registre:
                        comparer_lots(*p) if e[0].type_lot == "tarif" else comparer_lots_code(*p))

    return router
