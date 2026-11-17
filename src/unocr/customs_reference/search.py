"""Recherche documentaire locale, jamais classement ou validation douanière."""
import re
import unicodedata
from pathlib import Path

from .comparison import charger_lot
from .legal_comparison import charger_lot_code
from .search_excerpt import extraits_correspondants

MAX_REQUETE = 256
MAX_TERMES = 16
MAX_APERCU = 512
NATURES = {"originale", "modificative", "consolidee_provisoire"}


class ParamRechercheInvalide(ValueError):
    """Paramètres clients invalides, distincts d’une archive incohérente."""


def _normaliser(texte):
    # Copie pour comparaison seulement ; aucun champ archivé n'est modifié.
    decompose = unicodedata.normalize("NFKD", texte).casefold().replace("œ", "oe").replace("æ", "ae")
    sans_marques = "".join(c for c in decompose if not unicodedata.category(c).startswith("M") and c != "ـ")
    return " ".join(re.findall(r"[^\W_]+", sans_marques))


def _parametres(requete, limite, decalage, filtre=False):
    if type(limite) is not int or not 1 <= limite <= 100:
        raise ParamRechercheInvalide("Limite entière de 1 à 100 requise")
    if type(decalage) is not int or not 0 <= decalage <= 1_000_000:
        raise ParamRechercheInvalide("Décalage entier de 0 à 1000000 requis")
    if not isinstance(requete, str) or len(requete) > MAX_REQUETE:
        raise ParamRechercheInvalide("Requête textuelle de 256 caractères maximum requise")
    if any(unicodedata.category(c) == "Cc" and not c.isspace() for c in requete):
        raise ParamRechercheInvalide("Caractère de contrôle interdit dans la requête")
    termes = list(dict.fromkeys(_normaliser(requete).split()))
    if len(termes) > MAX_TERMES:
        raise ParamRechercheInvalide("16 termes maximum par requête")
    if not termes and (requete.strip() or not filtre):
        raise ParamRechercheInvalide("Requête vide ou sans terme recherchable")
    return termes


def _correspondances(champs, termes):
    if not termes:
        return {}
    normalises = {cle: _normaliser(valeur) for cle, valeur in champs.items() if valeur is not None}
    preuves = {terme: sorted(cle for cle, valeur in normalises.items() if terme in valeur) for terme in termes}
    return preuves if all(preuves.values()) else None


def _apercu(texte):
    return None if texte is None else {"texte": texte[:MAX_APERCU], "tronque": len(texte) > MAX_APERCU}


def _rapport(type_recherche, requete, termes, mode, filtres, rapport, total, resultats, limite, decalage):
    suivant = decalage + len(resultats)
    return {
        "type_recherche": type_recherche, "perimetre": "lot_en_quarantaine",
        "lecture_seule": True, "publication_active": False, "validation_juridique": "non_validee",
        "validation_humaine_requise": True, "completude_reglementaire": "non_etablie",
        "classement_douanier_valide": False, "restitution_juridique_a_date": False,
        "requete": requete, "termes_normalises": termes, "mode": mode, "filtres": filtres,
        "archive": rapport["archive"], "total_correspondances": total, "limite": limite, "decalage": decalage,
        "decalage_suivant": suivant if suivant < total else None, "resultats": resultats,
        "avertissements": [
            "Recherche dans un seul lot contrôlé en quarantaine, pas dans un référentiel officiel exhaustif.",
            "Résultats documentaires non validés : ni classement tarifaire, ni règle applicable, ni conseil juridique.",
            "Normalisation de recherche seulement ; textes et codes reçus conservés sans correction.",
            "Sous-chaînes littérales de tous les termes, sans synonymes, traduction, IA ou score de confiance.",
            "Aucun résultat ne signifie seulement aucune correspondance dans ce périmètre, pas absence de droit.",
            "Empreintes et rejeu ne prouvent pas authenticité, exactitude des transcriptions ou immutabilité WORM.",
        ],
    }


def rechercher_tarif(repertoire: Path, requete: str, limite: int = 20, decalage: int = 0) -> dict:
    termes = _parametres(requete, limite, decalage)
    brut = requete.strip()
    numerique = brut.isdecimal()
    if numerique and re.fullmatch(r"[0-9]{1,10}", brut) is None:
        raise ParamRechercheInvalide("Préfixe de code : de 1 à 10 chiffres ASCII, sans conversion ni zfill")
    lot, rapport = charger_lot(repertoire)
    resultats, total = [], 0
    for ligne in sorted(lot.lignes, key=lambda o: o.code_tarifaire_10):
        preuves = ({brut: ["code_tarifaire_10"]} if ligne.code_tarifaire_10.startswith(brut) else None) if numerique else _correspondances({
            "designation_officielle_fr": ligne.designation_officielle_fr,
            "designation_officielle_ar": ligne.designation_officielle_ar,
        }, termes)
        if preuves is None:
            continue
        if decalage <= total < decalage + limite:
            resultats.append({"ligne": ligne.model_dump(mode="json"), "champs_correspondants": preuves})
        total += 1
    resultat = _rapport("tarif_documentaire", requete, termes, "prefixe_code_ascii" if numerique else "texte_normalise",
                        {}, rapport, total, resultats, limite, decalage)
    resultat["perimetre_lecture"] = rapport["perimetre_lecture"]
    resultat["source_declaree"] = lot.source.model_dump(mode="json")
    resultat["avertissements"].append("Les mesures fiscales séparées ne sont pas recherchées ni utilisées pour calculer des droits.")
    return resultat


def rechercher_code(repertoire: Path, requete: str = "", limite: int = 20, decalage: int = 0,
                    numero_article: str | None = None, source_id: str | None = None, nature: str | None = None) -> dict:
    for valeur in (numero_article, source_id):
        if valeur is not None and (not isinstance(valeur, str) or not valeur.strip() or len(valeur) > MAX_REQUETE):
            raise ParamRechercheInvalide("Filtre article/source textuel non vide, de 256 caractères maximum requis")
    if nature is not None and (not isinstance(nature, str) or nature not in NATURES):
        raise ParamRechercheInvalide("Nature d'article inconnue")
    filtres = {"numero_article": numero_article, "source_id": source_id, "nature_version": nature}
    termes = _parametres(requete, limite, decalage, any(v is not None for v in filtres.values()))
    lot, rapport = charger_lot_code(repertoire)
    resultats, total = [], 0
    for article in sorted(lot.articles, key=lambda o: o.id):
        if ((numero_article is not None and article.numero_article != numero_article)
                or (source_id is not None and article.reference.source_id != source_id)
                or (nature is not None and article.nature_version != nature)):
            continue
        preuves = _correspondances({"intitule": article.intitule, "texte_integral": article.texte_integral,
                                    "texte_francais": article.texte_francais, "texte_arabe": article.texte_arabe}, termes)
        if preuves is None:
            continue
        if decalage <= total < decalage + limite:
            resultats.append({"id": article.id, "numero_article": article.numero_article,
                              "nature_version": article.nature_version, "version_juridique": article.version_juridique,
                              "intitule": article.intitule, "reference": article.reference.model_dump(mode="json"),
                              "validation_juridique": article.validation_juridique,
                              "statut_juridique_declare": article.statut_juridique_declare,
                              "date_entree_vigueur_declaree": article.date_entree_vigueur.isoformat() if article.date_entree_vigueur else None,
                              "date_fin_validite_declaree": article.date_fin_validite.isoformat() if article.date_fin_validite else None,
                              "apercus": {cle: _apercu(getattr(article, cle)) for cle in ("texte_integral", "texte_francais", "texte_arabe")},
                              "champs_correspondants": preuves,
                              "extraits_correspondants": extraits_correspondants({cle: getattr(article, cle) for cle in (
                                  "intitule", "texte_integral", "texte_francais", "texte_arabe")}, termes)})
        total += 1
    resultat = _rapport("code_documentaire", requete, termes, "texte_normalise_et_filtres_exacts", filtres,
                        rapport, total, resultats, limite, decalage)
    resultat["strategie_extraits"] = "un_par_champ_premier_terme_de_requete_present_premiere_occurrence"
    resultat["limite_caracteres_extrait"] = 384
    resultat["occurrences_denombrees"] = False
    resultat["transcription_verification"] = "non_verifiee"
    resultat["documents_declares"] = [d.model_dump(mode="json") for d in lot.documents]
    resultat["avertissements"].append("Aperçus initiaux conservés ; extraits originaux de 384 points de code maximum, un par champ correspondant, sans dénombrement des occurrences ni version applicable choisie.")
    return resultat
