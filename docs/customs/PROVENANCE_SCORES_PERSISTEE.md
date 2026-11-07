# Provenance des scores Baidu dans les résultats — lot 67

7 novembre 2026. Complète la [politique du lot 66](SCORES_BAIDU_SANS_VALEUR_INVENTEE.md), sans changer les scores.

## Champ facultatif par exécution

Le pipeline projette les seuls compteurs locaux validés dans :

`pages[i].engine_runs[j].confidence_provenance`

```json
{
  "policy": "provider_average_else_zero",
  "calibrated": false,
  "reported": 1,
  "missing": 1,
  "invalid": 1
}
```

Ce cas signifie trois éléments : un score fournisseur numérique exploitable
(éventuellement réellement nul), un score absent et un score invalide. Avec une
moyenne nulle, `reported: 1` reste distinct de `missing: 1` : les nombres seuls
ne permettaient pas cette distinction au lot 66.

Les compteurs portent sur les éléments/mots de **ce run**, pas sur la qualité
juridique du document, ni nécessairement sur les mots finalement retenus par le
consensus. Ce n'est pas une attribution individuelle du statut à chaque mot.
Les runs des différentes variantes ne sont pas agrégés par cette modification.

## Projection et cohérence

- Projection réservée aux sorties/runs Baidu réussis, avec même nombre de mots et
  même moyenne. Pas copie générale de `EngineOutput.raw` ni du corps fournisseur.
- Politique exacte, `calibrated` strictement `false`, compteurs entiers stricts
  entre 0 et 10 000 ; pas chaîne, booléen, flottant, champ supplémentaire ou secret.
- Somme des compteurs égale à `word_count`, au plus 10 000. La moyenne du run est
  comprise entre zéro et `reported / word_count` (zéro pour un run vide) : les
  éléments absents/invalides contribuent zéro, les éléments déclarés au plus un.
- La validation de structure ne reconstitue pas les scores individuels et ne
  prouve ni authenticité fournisseur, ni absence de modification hors application.
- Provenance manquante, malformée ou incompatible : run conservé **sans ce champ**,
  sans inférer de compteurs et sans journaliser l'erreur de validation susceptible
  d'inclure les données. L'absence signifie **provenance indisponible**, pas zéro
  élément absent/invalide ni score déclaré. Ce chemin n'améliore aucun score.

## Stockage, API et export

Le modèle facultatif est sérialisé dans `DocumentResult`, puis dans le
`result.json` du job. Le GET de résultat et l'export JSON existants le conservent.
Les tests exercent le vrai stockage temporaire et les routes HTTP via TestClient,
sans appel OCR distant. Ce n'est pas une qualification d'un navigateur ou du
service Baidu réel.

Les runs sans provenance gardent leur forme JSON historique : pas de nouvelle clé
à `null`, ni de compteur créé par défaut. Les anciens résultats sont lisibles et
réexportables. **Aucune migration/réécriture des anciens jobs ou exports**, aucune
requalification rétroactive de leurs scores : un ancien score Baidu élevé sans
provenance ne devient pas un score fournisseur prouvé. Aucune nouvelle interface
visuelle, synthèse CSV, signature ou preuve d'audit fournisseur n'est ajoutée.

## Ce qui ne change pas

Les scores numériques, leur moyenne et le signalement de faible confiance du
lot 66 sont conservés. Ni calibration, validation humaine, classement retenu,
calcul fiscal, consentement ou autorisation d'API ne sont ajoutés. Les autres
moteurs ne reçoivent pas cette provenance Baidu.

L'endpoint et les options fournisseur sont inchangés. La géométrie Baidu
préexistante, notamment la boîte pleine page en absence de `location`, reste
approximative et non qualifiée. Les limites de transport/OAuth du lot 65 restent
présentes. Aucun appel Baidu réel, corpus officiel ou résultat FR/AR qualifié
n'est revendiqué.

Voir [rapport et résultats mesurés](RAPPORT_LOT67.md).
