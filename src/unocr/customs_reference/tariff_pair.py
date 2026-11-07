"""Deux fiches documentaires isolées, sans fusion fiscale ou version applicable."""
from pathlib import Path

from .tariff_detail import consulter_code, verifier_parametres_fiche


def juxtaposer_fiches_tarifaires(avant: Path, apres: Path, code10: str,
                                 limite_avant: int = 20, decalage_avant: int = 0,
                                 limite_apres: int = 20, decalage_apres: int = 0) -> dict:
    # Valider aussi le côté après avant de lire quoi que ce soit du côté avant.
    verifier_parametres_fiche(code10, limite_avant, decalage_avant)
    verifier_parametres_fiche(code10, limite_apres, decalage_apres)
    a = consulter_code(avant, code10, limite_avant, decalage_avant)
    b = consulter_code(apres, code10, limite_apres, decalage_apres)
    champs = ("ligne_trouvee", "ligne_declaree", "hierarchie_declaree", "source_declaree",
              "total_mesures_declarees", "limite_mesures", "decalage_mesures",
              "decalage_mesures_suivant", "mesures_declarees")
    return {"type_rapport": "juxtaposition_documentaire_fiches_tarifaires", "lecture_seule": True,
            "publication_active": False, "validation_juridique": "non_validee", "validation_humaine_requise": True,
            "archives": {"avant": a["archive"], "apres": b["archive"]},
            "perimetre": "un_code_exact_dans_deux_lots_tarifaires_explicitement_choisis",
            "code_tarifaire_10_exact": code10,
            "avant": {cle: a[cle] for cle in champs}, "apres": {cle: b[cle] for cle in champs},
            "mesures_fusionnees": False, "identites_mesures_rapprochees": False,
            "fiscalite_applicable_etablie": False, "classement_douanier_valide": False,
            "restitution_juridique_a_date": False, "completude_reglementaire": "non_etablie",
            "utilisable_pour_calcul_douanier": False,
            "avertissements": [
                "Un même code exact est recherché séparément dans deux lots contrôlés, pas dans le tarif national complet.",
                "Avant/après exprime l'ordre demandé, pas succession des sources ni choix de version applicable.",
                "Chaque source, période, parent, unité et mesure reste rattaché à son propre lot ; aucune fusion fiscale.",
                "IDs de source/mesure locaux : une chaîne identique ne prouve ni identité ou continuité juridique.",
                "Sources et mesures non authentifiées/validées ; aucune date d'effet retenue automatiquement.",
                "Aucune mesure ou taux null ne signifie pas exonération ou zéro ; aucun taux combiné, arrondi ou calcul.",
                "Pagination des mesures indépendante ; les compteurs portent sur chaque lot, pas sur la couverture nationale.",
                "Absence de code dans l'un des lots ne prouve ni suppression nationale, création ou interdiction.",
                "Empreintes et rejeu ne constituent pas authenticité éditeur, transaction multi-dossiers ou archivage WORM.",
            ]}
