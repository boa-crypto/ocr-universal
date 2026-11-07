"""Dispatch fermé des exports rejouables, type de lot toujours fourni par opérateur."""
import re
from urllib.parse import urlsplit

from .article_detail import consulter_article
from .export_replay import _parametres_export
from .measure_search import rechercher_mesures_tarif
from .review_export import ExportRefuse
from .search import rechercher_code, rechercher_tarif
from .tariff_criteria import rechercher_tarif_criteres
from .tariff_detail import consulter_code


def preparer_rejeu(requete, lot_id, type_lot):
    prefixe = f"/api/v1/customs-review/lots/{lot_id}/"
    chemin = urlsplit(requete).path
    route = chemin[len(prefixe):] if chemin.startswith(prefixe) else ""
    def lire(autorises, numeriques=None):
        return _parametres_export(requete,lot_id,route=route,autorises=autorises,numeriques=numeriques)

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
    raise ExportRefuse("Route non prise en charge pour le type explicite fourni")
