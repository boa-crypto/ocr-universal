# Revue des champs de confiance nulle et rapport final — lot 71

7 novembre 2026. Complète la [qualité des pages sans sortie](PAGES_SANS_SORTIE_DANS_QUALITE.md).

## Zéro n'est plus ignoré par le filtre

`build_quality_report` compare désormais directement `FieldValue.confidence` au
seuil configuré, sans test préalable de vérité du nombre. Un zéro, y compris
`-0.0`, est donc recensé dans `fields_low_confidence` si le seuil est positif.

L'exclusion des champs `NOT_DETECTED` reste inchangée : leurs anomalies de champs
obligatoires absents relèvent du chemin existant. Le test reste strict `<` : à
seuil zéro, un champ à zéro n'est pas ajouté ; un score exactement égal au seuil
n'est pas ajouté. Cela diffère du signalement inconditionnel des pages sans
sortie du lot 70. Pas nouvelle validation des bornes du seuil ou de tous les
scores numériques dans ce lot.

La liste utilise les clés du dictionnaire `result.fields`, dans leur ordre,
pas le libellé ou l'attribut `name` du champ. Aucun champ ou score n'est créé.

## Cohérence avec les confiances finales du pipeline

Le pipeline appliquait déjà un facteur de qualité et un arrondi aux confiances
globales des champs, mais après la construction du rapport. La liste pouvait
donc correspondre à un score antérieur, différent de celui finalement enregistré.

Le calcul existant des confiances est conservé ; **le rapport est désormais
construit après ce recalcul**. Les tests couvrent une baisse sous le seuil, une
hausse au-dessus du seuil, un zéro initial relevé par le calcul existant et un
petit score arrondi à zéro. La liste utilise `confidence`, pas une nouvelle
probabilité ni le champ `calibrated_confidence` comme seuil alternatif.

Le garde-fou existant du recalcul, notamment l'absence de recalcul pour une
confiance moteur nulle par défaut ou une page non retrouvée, n'est pas modifié.
Ce lot corrige le filtre et l'ordre de construction, pas toute la provenance ou
validité des valeurs de confiance.

## Statuts humains et valeurs préservés

Le rapport ne change aucun statut, valeur brute/normalisée/corrigée/confirmée ou
origine de valeur. La politique historique n'exclut que `NOT_DETECTED` : un champ
`VALIDATED` sous le seuil peut donc figurer dans la liste, sans que sa validation
soit révoquée. Un zéro validé est désormais traité comme un autre faible score
validé, pas comme une décision de rouvrir automatiquement un dossier.

La liste est un signal, pas une preuve de revue humaine, une file visuelle,
un verrou fiscal, une transition de job ou une validation réglementaire.
Aucun recalcul des anciens jobs/exports ou rapports réutilisés par dédoublonnage.
La cohérence corrigée porte sur la construction du rapport par le pipeline ;
aucune garantie nouvelle de reconstruction après toutes les éditions/API humaines.

## Vérification et limites

27 nouveaux cas : statuts, zéros signés, seuils, exclusion non détectée,
non-mutation, conservation des confirmations, recalcul final et persistance.
Des images PNG réelles sont ingérées dans un harnais à registre de moteurs vide,
avec **contrats d'extraction explicitement injectés** pour les quatre scénarios
numériques. Il ne s'agit pas d'OCR ou d'extraction réelle mesurée. Stockage
JSON temporaire, GET résultat et téléchargement JSON via TestClient sont exercés.

Pas validation générale des scores non finis/hors bornes, calibration, précision
FR/AR, navigateur réel ou changement des règles métier. Repli historique 0,95
pour texte sans mots, géométrie Baidu absente et risques OAuth query inchangés.
Voir [rapport et recette](RAPPORT_LOT71.md).
