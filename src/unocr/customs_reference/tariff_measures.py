"""Consultation documentaire tarif/mesures autonomes, sans rattachement juridique."""
from pathlib import Path

from .measure_search import rechercher_mesures_tarif
from .tariff_detail import consulter_code, verifier_parametres_fiche


def juxtaposer_tarif_mesures(tarif: Path, mesures: Path, code10: str,
                              limite_tarif: int = 20, decalage_tarif: int = 0,
                              limite_mesures: int = 20, decalage_mesures: int = 0) -> dict:
    verifier_parametres_fiche(code10, limite_tarif, decalage_tarif)
    verifier_parametres_fiche(code10, limite_mesures, decalage_mesures)
    fiche = consulter_code(tarif, code10, limite_tarif, decalage_tarif)
    autonomes = rechercher_mesures_tarif(mesures, code10=code10, limite=limite_mesures,
                                       decalage=decalage_mesures, type_lot="mesures")
    return {"type_rapport":"consultation_documentaire_tarif_mesures_autonomes", "lecture_seule":True,
        "publication_active":False, "validation_juridique":"non_validee", "validation_humaine_requise":True,
        "code_tarifaire_10_exact":code10,
        "archives":{"avant":fiche["archive"],"apres":autonomes["archive"]},
        "roles_archives":{"avant":"nomenclature", "apres":"mesures_autonomes"},
        "fiche_nomenclature":{k:v for k,v in fiche.items() if k != "archive"},
        "mesures_autonomes":{k:v for k,v in autonomes.items() if k != "archive"},
        "correspondance_codes":"egalite_textuelle_exacte_sans_inference_juridique",
        "rattachement_juridique_etabli":False, "mesures_fusionnees":False,
        "identites_mesures_rapprochees":False, "fiscalite_applicable_etablie":False,
        "classement_douanier_valide":False, "restitution_juridique_a_date":False,
        "completude_reglementaire":"non_etablie", "utilisable_pour_calcul_douanier":False,
        "avertissements":[
            "Un code exact consulté dans deux lots choisis : égalité textuelle seulement, pas rattachement juridique validé.",
            "Sources, dates, références et mesures de la nomenclature et du lot autonome restent distinctes.",
            "Avant/après des archives désigne les deux rôles documentaires, pas une succession chronologique.",
            "IDs locaux aux lots ; aucun dédoublonnage, fusion de taux, priorité, héritage de date ou choix de règle applicable.",
            "Code absent de la nomenclature reçue : les mesures restent visibles, sans preuve d'existence nationale du code.",
            "Taux exacts en chaînes, null distinct du zéro ; aucune mesure ne signifie ni exonération ni absence de restriction.",
            "Deux paginations indépendantes, chargement/rejeu des lots entiers, pas transaction multi-dossiers.",
            "Empreintes et rejeu ne prouvent ni authenticité des sources, exhaustivité ou applicabilité fiscale.",
        ]}
