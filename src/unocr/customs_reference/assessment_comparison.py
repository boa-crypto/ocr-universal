"""Juxtaposition des déclarations/citations et pistes, sans inférence technique."""
import copy
import hashlib
import json

from .tariff_criteria import CRITERES
from .technical_evidence import verifier_pieces


def comparer_dossier(document):
    document = copy.deepcopy(document)
    pieces = document.get("pieces_techniques", [])
    verifier_pieces(pieces)
    diagnostic = document["diagnostic"]
    criteres, questions = [], []
    for critere in CRITERES:
        produit = diagnostic["produit_declare"].get(critere)
        associees, declarations = [], []
        for piece in pieces:
            if critere in piece["criteres_declares"]:
                provenance = {k:piece[k] for k in ("piece_id","nom","sha256","fourni_par","horodatage","localisateur_declare")}
                associees.append(provenance)
                for declaration in piece["declarations_attributs"]:
                    if declaration["critere"] == critere:
                        declarations.append({**declaration, "piece":provenance,
                                             "egalite_exacte_avec_produit":None if produit is None else declaration["valeur_declaree"] == produit})
        valeurs = list(dict.fromkeys(d["valeur_declaree"] for d in declarations))
        divergence = len(valeurs) > 1
        criteres.append({"critere":critere, "valeur_produit_declaree":produit,
                         "pieces_associees":associees, "declarations_citees":declarations,
                         "valeurs_distinctes_exactes":valeurs, "divergence_textuelle_declarations":divergence})
        if produit is None:
            questions.append({"critere":critere,"type":"produit_non_renseigne",
                              "question":"Renseigner le produit sans déduire sa valeur automatiquement d'une pièce."})
        if not declarations:
            questions.append({"critere":critere,"type":"sans_citation_declaree",
                              "question":"Fournir une déclaration et sa citation technique, ou expliquer leur absence."})
        if divergence or any(d["egalite_exacte_avec_produit"] is False for d in declarations):
            questions.append({"critere":critere,"type":"ecart_textuel_a_examiner",
                              "question":"Examiner les valeurs textuelles différentes ; elles ne prouvent pas une contradiction technique."})
    candidats = []
    for candidat in diagnostic["recherche"]["resultats"]:
        ligne = candidat["ligne"]
        candidats.append({"code_tarifaire_10":ligne["code_tarifaire_10"], "reference":ligne["reference"],
                          "designation_officielle_fr":ligne.get("designation_officielle_fr"),
                          "designation_officielle_ar":ligne.get("designation_officielle_ar"),
                          "correspondances_litterales_par_critere":candidat["correspondances_par_critere"],
                          "termes_non_retrouves_par_critere":candidat["termes_non_retrouves_par_critere"],
                          "extraits_correspondants":candidat["extraits_correspondants"]})
    contenu = json.dumps({k:v for k,v in document.items() if k != "historique"},
                         ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    return {"type_rapport":"comparaison_declarations_et_pistes_non_validee", "dossier_id":document["id"],
            "version":document["version"], "lot_id":document["lot_id"],
            "manifest_sha256":document["manifest_sha256"], "sha256_dossier":hashlib.sha256(contenu).hexdigest(),
            "archive":document["archive"], "criteres":criteres, "candidats":candidats,
            "autres_candidats_non_affiches":diagnostic["autres_candidats_non_affiches"],
            "questions_a_arbitrer":questions, "attributs_techniques_certifies":False,
            "contradiction_semantique_etablie":False, "classement_ia_effectue":False,
            "candidat_retenu_automatiquement":False, "taux_calcules":False,
            "publication_active":False, "validation_juridique":"non_validee",
            "politique_comparaison":"egalite_exacte_sans_normalisation_traduction_ou_synonymes",
            "avertissements":["Une égalité textuelle ne certifie pas un attribut ; une différence ne prouve pas une contradiction.",
                               "Citations contrôlées dans la copie reçue, pas dans un original authentifié.",
                               "Correspondances des candidats issues de la recherche littérale du produit enregistré, pas des citations.",
                               "Aucun score de pertinence, probabilité, classement juridique ou nouvel élargissement des candidats."]}
