# Rapport lot 71 — champs à zéro et revue sur les confiances finales

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Deux écarts sont corrigés : le zéro n'est plus ignoré dans le filtre de revue des
champs ; le pipeline construit désormais le rapport **après** le recalcul existant
des confiances des champs, pas avant. La liste reflète donc les scores finalement
enregistrés par ce chemin du pipeline.

[Contrat et limites](REVUE_CHAMPS_CONFIANCE_NULLE.md),
[recette machine](RECETTE_LOT71.json).

## Réalisation

- Comparaison directe `confidence < review_threshold`, sans test de vérité du
  nombre. Zéro et zéro signé sont recensés sous un seuil positif.
- `NOT_DETECTED` reste exclu. Comparaison strictement inférieure : seuil zéro ou
  égalité au seuil n'ajoutent pas un champ à zéro. Pas modification de la politique
  inconditionnelle des pages sans sortie du lot 70.
- Recalcul, facteur de qualité, arrondi et calibration des champs inchangés ; seul
  l'ordre de construction du rapport change. Hausses, baisses et arrondis à zéro
  ne laissent plus une liste fondée sur la confiance antérieure.
- Aucune valeur ou origine de valeur changée par le rapport, aucun statut humain
  révoqué. La politique historique peut signaler un champ `VALIDATED` sous le seuil ;
  il garde son statut et sa valeur confirmée. Pas décision automatique de dossier.
- Stockage, API et export JSON conservent liste et valeurs/statuts sans nouveau schéma.

## Vérifications mesurées

- **27 nouveaux tests**, sélection qualité/Baidu **241 réussis**, zéro
  échec/ignoré, 1 avertissement, **5,08 s console**, JUnit 3,461 s.
- Statuts, zéros signés, seuils, exclusion non détectée, ordre des clés et absence
  de mutation ; quatre cas de recalcul final par le pipeline, dont un arrondi à zéro.
  Images PNG réelles, registre explicitement vide et contrats d'extraction injectés
  dans le harnais : pas OCR ou extraction réelle mesurée pour ces scénarios.
- Stockage temporaire et GET résultat/export via TestClient, relecture modèle et
  export JSON réels, avec statut `VALIDATED` et valeur confirmée synthétiques préservés.
- Contre-épreuve sur le couple qualité/pipeline exact du lot 70, chargé séparément
  avec les mêmes injections d'extraction de test : **16 échecs attendus, 11 réussis**,
  27 cas, code 1, **4,66 s console**, JUnit 2,772 s. Checkout non remplacé ; les
  hausses/baisses de confiance sont réellement exercées, pas des erreurs de harnais.
- Documentaire historique : **2 160 réussis**, zéro échec/ignoré, 1 avertissement,
  **83,82 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM documentaires** réussis.
  Quatre ponts et 74 exports existants, pas nouveau scénario métier attribué.
- **Complète : 3 496 réussis, 2 échecs, 1 ignoré, 1 avertissement, 498,24 s**,
  soit **3 499 cas**, JUnit 498,101 s, code **1**. Compteurs cohérents avec les
  vrais cas. Mêmes échecs Indra `test_indra_engine_availability` et
  `test_selection_prefers_native_when_present`, même ignoré
  `test_indra_engine_recognize` qu'au lot 70. **Suite complète non verte.**

Code **`58414fea269d779b1c28e6eb7e7dce498c651dfe`** poussé ;
[CI 42404996500](https://github.com/boa-crypto/ocr-universal/actions/runs/42404996500)
terminée **success**, révision et étapes confirmées via `gh` : 241 qualité/Baidu,
24 ingestion/PDF, 10 UI dont les 47 scénarios de provenance du lot 68, puis documentaire.
Pas suite OCR complète en CI ni JUnit distant téléchargé ; chiffres détaillés locaux
conservés dans `/home/user/recettes-unocr/lot71` hors dépôt.

Aucune dépendance nouvelle. Aperçu redémarré sur `0.0.0.0:8000` avec le correctif.

## Limites et réception

Signalement dans une liste, pas preuve de revue, file visuelle, révocation de
validation, transition de job ou verrou fiscal. Pas recalcul des anciens rapports,
exports ou résultats réutilisés par dédoublonnage. Pas garantie nouvelle de
reconstruction après toute édition humaine/API hors construction du pipeline.

La validité de tous les scores non finis/hors bornes et des seuils n'est pas
traitée ici. Le garde-fou préexistant du recalcul, notamment une confiance moteur
nulle par défaut, reste inchangé. `calibrated_confidence` ne remplace pas
`confidence` comme critère du rapport. Pas calibration ou précision FR/AR mesurée.
Repli texte sans mots 0,95, géométrie Baidu absente et risques OAuth query inchangés.
Aucun fournisseur, navigateur réel ou test de charge qualifié ; Indra non réparé.

**26/27 empreintes historiques conformes**, même écart qu'aux lots 64–70 :
`data/referentiels.json` observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`, attendu
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Référentiels, quatre dossiers partagés modifiés, autres données exploratoires et
journaux préservés hors commit, sans restauration ou attribution certaine.

**0 nouvel original officiel, 0 article/code officiellement validé, 0 publication
active. Mission globale partielle, non recevable pour production fiscale.**
