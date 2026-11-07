"""Critères de recherche explicites dans les libellés, jamais attributs certifiés."""
import re
import unicodedata
from pathlib import Path

from .comparison import charger_lot
from .search import ParamRechercheInvalide, _normaliser, _parametres, _rapport

CRITERES = ("designation", "matiere", "fonction", "usage", "caracteristiques")


def rechercher_tarif_criteres(repertoire: Path, *, designation: str | None = None, matiere: str | None = None,
                              fonction: str | None = None, usage: str | None = None,
                              caracteristiques: str | None = None, code_prefix: str | None = None,
                              limite: int = 20, decalage: int = 0) -> dict:
    criteres = dict(zip(CRITERES,(designation,matiere,fonction,usage,caracteristiques)))
    # Pagination contrôlée même pour une recherche par préfixe seul.
    _parametres("",limite,decalage,filtre=True)
    if code_prefix is not None and (not isinstance(code_prefix,str) or re.fullmatch(r"[0-9]{1,10}",code_prefix) is None):
        raise ParamRechercheInvalide("Préfixe explicite de 1 à 10 chiffres ASCII requis")
    termes = {}
    for cle,valeur in criteres.items():
        if valeur is not None:
            if not isinstance(valeur,str) or not valeur.strip() or any(unicodedata.category(c)=="Cs" for c in valeur):
                raise ParamRechercheInvalide("Critère textuel non blanc sans surrogate requis")
            termes[cle] = _parametres(valeur,limite,decalage)
    if not termes and code_prefix is None:
        raise ParamRechercheInvalide("Au moins un critère ou un préfixe explicite requis")
    lot,rapport = charger_lot(repertoire)
    resultats,total = [],0
    for ligne in sorted(lot.lignes,key=lambda valeur:valeur.code_tarifaire_10):
        if code_prefix is not None and not ligne.code_tarifaire_10.startswith(code_prefix):
            continue
        champs = {cle:_normaliser(getattr(ligne,cle)) for cle in ("designation_officielle_fr","designation_officielle_ar")
                  if getattr(ligne,cle) is not None}
        preuves = {critere:{t:sorted(c for c,v in champs.items() if t in v) for t in mots}
                   for critere,mots in termes.items()}
        if not all(noms for critere in preuves.values() for noms in critere.values()):
            continue
        if decalage <= total < decalage+limite:
            resultats.append({"ligne":ligne.model_dump(mode="json"),"correspondances_par_critere":preuves})
        total += 1
    rep = _rapport("tarif_criteres_documentaires"," ; ".join(f"{k}={v}" for k,v in criteres.items() if v is not None),
        list(dict.fromkeys(t for mots in termes.values() for t in mots)),"conjonction_criteres_sous_chaines",
        {"criteres":criteres,"code_prefix":code_prefix},rapport,total,resultats,limite,decalage)
    rep.update(source_declaree=lot.source.model_dump(mode="json"),perimetre_lecture=rapport["perimetre_lecture"],
               termes_normalises_par_critere=termes,attributs_techniques_certifies=False,
               classement_ia_effectue=False,taux_calcules=False)
    rep["avertissements"].extend([
        "Matière, fonction, usage et caractéristiques sont des étiquettes de requête, pas des attributs produits certifiés.",
        "Chaque terme doit apparaître dans au moins un libellé FR/AR de la ligne ; les critères sont tous requis.",
        "Pas de synonymes, traduction FR/AR, raisonnement RGI, notes/exclusions ou score de confiance inventés.",
        "Mesures fiscales, règles, unités et dates non recherchées ; aucune fiscalité applicable déduite."])
    return rep
