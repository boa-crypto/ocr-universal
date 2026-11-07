"""Dispatch fermé des exports rejouables, type de lot toujours fourni par opérateur."""
import re
from urllib.parse import urlsplit

from .article_detail import consulter_article
from .article_diff import comparer_versions_article
from .article_pdf_match import rapprocher_fragment_article_pdf
from .article_relations import consulter_relations_article
from .code_tree import parcourir_code
from .comparison import charger_lot
from .coverage import diagnostiquer_couverture
from .export_replay import _parametres_export
from .fiscal_importer import charger_lot_mesures
from .fiscal_pdf_page import lire_page_pdf_mesures
from .history import historique_article
from .legal_comparison import charger_lot_code
from .measure_pdf_match import rapprocher_description_mesure_pdf
from .measure_search import rechercher_mesures_tarif
from .pdf_page import lire_page_pdf
from .relation_pdf_match import rapprocher_justification_pdf
from .review_export import ExportRefuse
from .search import rechercher_code, rechercher_tarif
from .source_catalog import inventorier_sources
from .tariff_criteria import rechercher_tarif_criteres
from .tariff_detail import consulter_code
from .tariff_tree import parcourir_tarif


def preparer_rejeu(requete, lot_id, type_lot, *, autoriser_pdf=False):
    prefixe = f"/api/v1/customs-review/lots/{lot_id}/"
    chemin = urlsplit(requete).path
    route = chemin[len(prefixe):] if chemin.startswith(prefixe) else ""
    def lire(autorises, numeriques=None):
        return _parametres_export(requete,lot_id,route=route,autorises=autorises,numeriques=numeriques)

    pdf_types = {"pdf":"code","article-pdf-match":"code","relation-pdf-match":"code",
                 "fiscal-pdf":"mesures","measure-pdf-match":"mesures"}
    if route in pdf_types:
        if not autoriser_pdf:
            raise ExportRefuse("Rejeu PDF non autorisé explicitement")
        if type_lot != pdf_types[route]:
            raise ExportRefuse("Route PDF incompatible avec le type explicite fourni")
        id_cle = {"pdf":"document_id","fiscal-pdf":"document_id","article-pdf-match":"article_id",
                  "relation-pdf-match":"relation_id","measure-pdf-match":"mesure_id"}[route]
        cles = {id_cle,"page","limit","offset"}
        if route == "article-pdf-match":
            cles.add("field")
        params = lire(cles,{"page":("page",5),"limit":("limite",5),"offset":("decalage",8)})
        if id_cle not in params or (route in {"article-pdf-match","relation-pdf-match"} and "page" not in params):
            raise ExportRefuse("ID et page explicites requis pour ce rapport PDF")
        if "field" in params:
            params["champ"] = params.pop("field")
        if route in {"measure-pdf-match"}:
            params.setdefault("page",1)
        service = {"pdf":lire_page_pdf,"fiscal-pdf":lire_page_pdf_mesures,
                   "article-pdf-match":rapprocher_fragment_article_pdf,
                   "relation-pdf-match":rapprocher_justification_pdf,
                   "measure-pdf-match":rapprocher_description_mesure_pdf}[route]
        return lambda p: service(p,**params)
    if route == "tariff-criteria" and type_lot == "tarif":
        params = _parametres_export(requete,lot_id)
        return lambda p: rechercher_tarif_criteres(p,**params)
    if route == "search" and type_lot in {"code","tarif"}:
        params = lire({"q","limit","offset","article","source","nature"} if type_lot == "code" else {"q","limit","offset"})
        arguments = {"requete":params.pop("q", ""),**params}
        if type_lot == "code":
            for origine,cible in (("article","numero_article"),("source","source_id")):
                if origine in arguments:
                    arguments[cible] = arguments.pop(origine)
            return lambda p: rechercher_code(p,**arguments)
        return lambda p: rechercher_tarif(p,**arguments)
    if route == "measure-search" and type_lot in {"tarif","mesures"}:
        params = lire({"q","code10","measure_type","limit","offset"})
        arguments = {"requete":params.pop("q", ""),"type_lot":type_lot,**params}
        if "measure_type" in arguments:
            arguments["type_mesure"] = arguments.pop("measure_type")
        return lambda p: rechercher_mesures_tarif(p,**arguments)
    if route == "article" and type_lot == "code":
        params = lire({"article_id","field","limit","offset"}, {"limit":("limite",5),"offset":("decalage",8)})
        if "article_id" not in params:
            raise ExportRefuse("ID article explicite requis")
        if "field" in params:
            params["champ"] = params.pop("field")
        return lambda p: consulter_article(p,**params)
    if re.fullmatch(r"tariff/[0-9]{10}",route) and type_lot == "tarif":
        params = lire({"measures_limit","measures_offset"},
                      {"measures_limit":("limite_mesures",3),"measures_offset":("decalage_mesures",7)})
        return lambda p: consulter_code(p,route.split("/")[1],**params)
    if route == "sources":
        params = lire({"q","source_id","nature_document","limit","offset"})
        if "q" in params:
            params["requete"] = params.pop("q")
        return lambda p: inventorier_sources(p,type_lot,**params)
    if route in {"check","coverage"}:
        lire(set())
        if route == "coverage":
            return lambda p: diagnostiquer_couverture(p,type_lot)
        lecteur = {"code":charger_lot_code,"tarif":charger_lot,"mesures":charger_lot_mesures}[type_lot]
        return lambda p: lecteur(p)[1]
    if route == "history" and type_lot == "code":
        params = lire({"article","limit","offset","relations_limit","relations_offset"},
                      {"limit":("limite",3),"offset":("decalage",7),
                       "relations_limit":("limite_relations",3),"relations_offset":("decalage_relations",7)})
        if "article" not in params:
            raise ExportRefuse("Numéro article explicite requis")
        params["numero_article"] = params.pop("article")
        return lambda p: historique_article(p,**params)
    if route == "article-relations" and type_lot == "code":
        params = lire({"article_id","direction","relation_type","limit","offset"})
        if "article_id" not in params:
            raise ExportRefuse("ID article explicite requis")
        for a,b in (("direction","sens"),("relation_type","type_relation")):
            if a in params:
                params[b] = params.pop(a)
        return lambda p: consulter_relations_article(p,**params)
    if route == "article-diff" and type_lot == "code":
        params = lire({"avant_id","apres_id","field","limit","offset_avant","offset_apres"},
                      {"limit":("limite",5),"offset_avant":("decalage_avant",8),"offset_apres":("decalage_apres",8)})
        if not {"avant_id","apres_id"} <= params.keys():
            raise ExportRefuse("Deux IDs article explicites requis")
        if "field" in params:
            params["champ"] = params.pop("field")
        return lambda p: comparer_versions_article(p,**params)
    if route == "tree" and type_lot == "tarif":
        params = lire({"level","parent","limit","offset"})
        if "level" in params:
            params["niveau"] = params.pop("level")
        return lambda p: parcourir_tarif(p,**params)
    if route == "code-tree" and type_lot == "code":
        params = lire({"source_id","path","limit","offset"})
        if "path" in params:
            params["chemin"] = params.pop("path")
        return lambda p: parcourir_code(p,**params)
    raise ExportRefuse("Route non prise en charge pour le type explicite fourni")
