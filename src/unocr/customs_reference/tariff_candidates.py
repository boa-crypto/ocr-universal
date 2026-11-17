"""Pistes littérales partielles, tri documentaire explicite, jamais classement IA."""
from pathlib import Path

from .comparison import charger_lot
from .search import ParamRechercheInvalide, _rapport
from .tariff_criteria import CRITERES, _preuves_criteres, _valider_criteres
from .tariff_excerpt import MAX_EXTRAITS_TARIF, localiser_criteres


def _indicateurs(preuves):
    complets = [c for c,mots in preuves.items() if all(mots.values())]
    trouves = sum(bool(champs) for mots in preuves.values() for champs in mots.values())
    return complets, trouves


def rechercher_pistes_tarifaires(repertoire: Path, *, designation: str | None = None,
                                 matiere: str | None = None, fonction: str | None = None,
                                 usage: str | None = None, caracteristiques: str | None = None,
                                 code_prefix: str | None = None, limite: int = 20,
                                 decalage: int = 0, match_mode: str = "sous_chaine") -> dict:
    criteres = dict(zip(CRITERES,(designation,matiere,fonction,usage,caracteristiques)))
    termes = _valider_criteres(criteres,code_prefix,limite,decalage,match_mode)
    if not termes:
        raise ParamRechercheInvalide("Au moins un critère textuel explicite requis pour des pistes")
    lot,rapport = charger_lot(repertoire)
    # Ne matérialise les positions/extraits que pour la page retournée. Le lot et
    # le tableau de tri restent chargés en mémoire ; pas de streaming revendiqué.
    candidats = []
    for ligne in lot.lignes:
        if code_prefix is not None and not ligne.code_tarifaire_10.startswith(code_prefix):
            continue
        preuves = _preuves_criteres(ligne,termes,match_mode)
        complets,trouves = _indicateurs(preuves)
        if trouves:
            candidats.append((-len(complets),-trouves,ligne.code_tarifaire_10,ligne))
    candidats.sort(key=lambda c:c[:3])
    resultats = []
    for rang,candidat in enumerate(candidats[decalage:decalage+limite],start=decalage+1):
        ligne = candidat[3]
        preuves = _preuves_criteres(ligne,termes,match_mode)
        complets,trouves = _indicateurs(preuves)
        resultats.append({
            "statut":"piste_documentaire_non_validee", "rang_documentaire":rang,
            "ligne":ligne.model_dump(mode="json"), "correspondances_par_critere":preuves,
            "criteres_documentairement_complets":complets,
            "termes_non_retrouves_par_critere":{c:[t for t,champs in mots.items() if not champs]
                                                for c,mots in preuves.items()},
            "conjonction_documentaire_complete":len(complets) == len(termes),
            "indicateurs_tri":{"nombre_criteres_complets":len(complets),
                               "nombre_paires_critere_terme_retrouvees":trouves},
            **localiser_criteres(ligne,preuves,match_mode),
        })
    rep = _rapport("pistes_tarifaires_documentaires_non_validees",
        " ; ".join(f"{k}={v}" for k,v in criteres.items() if v is not None),
        list(dict.fromkeys(t for mots in termes.values() for t in mots)), "union_termes_criteres",
        {"criteres":criteres,"code_prefix":code_prefix,"match_mode":match_mode},rapport,
        len(candidats),resultats,limite,decalage)
    rep.update(source_declaree=lot.source.model_dump(mode="json"),perimetre_lecture=rapport["perimetre_lecture"],
               termes_normalises_par_critere=termes,attributs_techniques_certifies=False,
               classement_ia_effectue=False,taux_calcules=False,candidat_retenu_automatiquement=False,
               probabilite_classement_etablie=False,maximum_extraits_par_ligne=MAX_EXTRAITS_TARIF,
               politique_tri=["nombre_criteres_complets_decroissant",
                              "nombre_paires_critere_terme_retrouvees_decroissant",
                              "code_tarifaire_10_croissant"],
               politique_admission="au_moins_une_paire_critere_terme_retrouvee_dans_les_libelles_fr_ar")
    rep["avertissements"] = [a for a in rep["avertissements"] if not a.startswith("Sous-chaînes littérales")]
    rep["avertissements"].extend([
        "Pistes partielles explicites : au moins un terme retrouvé, tous les critères ne sont pas requis.",
        "Tri par nombres de critères complets, puis paires critère-terme retrouvées, puis code ; pas confiance ou pertinence juridique.",
        "Un terme répété sous plusieurs critères compte plusieurs paires : compteurs non indépendants, pas occurrences ni probabilités.",
        "Un terme non retrouvé dans ces libellés ne prouve pas l'absence d'un attribut du produit ou d'un droit.",
        "Les étiquettes matière/fonction/usage/caractéristiques ne certifient aucun attribut technique.",
        "Sous-chaîne ou mot entier normalisé selon match_mode ; pas synonymes, traduction, IA, notes, exclusions ou raisonnement RGI.",
        "Positions Unicode et 16 extraits maximum par ligne dans les libellés reçus, pas preuve PDF.",
        "Mesures fiscales non recherchées ; aucun classement, taux, date d'application ou candidat choisi automatiquement.",
    ])
    return rep
