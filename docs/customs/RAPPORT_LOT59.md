# Rapport lot 59 — API autorisée et rejeu des pistes documentaires

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Route administrative `/lots/{lot_id}/tariff-candidates`, accès nominatif et
allowlist, type Tarif, manifeste épinglé et audit obligatoire avant résultat.
Paramètres explicites uniques, encodage strict et pagination ASCII. Format export
v1 étendu et schéma synchronisé ; rejeu typé de tout le rapport sans diff textuel.
Pas de nouvelle émission de fichier signée ou attestée par le serveur.

[Contrat API/rejeu](API_PISTES_TARIFAIRES.md), [recette machine](RECETTE_LOT59.json).

## Qualification locale exécutée

- **45 nouveaux cas Python** : cinq rapports API comparés au service et rejoués
  identiquement avec deux empreintes de test ; refus RBAC/allowlist/legacy, types,
  paramètres et encodages ; audit 503, manifeste différent avant/après service,
  source d'archive altérée ; six altérations distinctes de résultats détectées ;
  garde du contrôleur historique et CLI codes 0/1/2.
- Lanceur réel : **2 124 réussis, 66 fichiers, 0 ignoré, 1 avertissement,
  53,84 s**. Ruff et diff-check réussis ; **186 scénarios JSDOM** existants réussis.
- **70 exports des quatre parcours UI/API existants** encore rejoués (58 simples
  dont 14 PDF, 12 paires), et 4 copies PDF Code vérifiées. **Cinq rapports API de
  pistes supplémentaires** contrôlés/rejoués dans les nouveaux tests ; ils ne
  sont pas comptés comme nouveaux exports UI ou scénarios navigateur.
- **27/27 empreintes conformes à la référence 56**, sans restauration après cette
  sélection. Aucun original officiel ajouté ; journaux historiques hors commit.
  Artefacts locaux bruts : `/home/user/recettes-unocr/lot59`.

Suite complète **non relancée au lot 59**. Dernière complète exécutée au lot 58 :
**3 111 réussis, 18 échecs, 11 ignorés, 214,61 s**, non verte. Aucun échec OCR
annoncé résolu et aucun nouveau test d'échec converti en skip.

## Qualification GitHub Actions

Code du lot au commit **`8b521b9e`**. Run
**[42391189119](https://github.com/boa-crypto/ocr-universal/actions/runs/42391189119)**
terminé **success**, job **1 min 28 s** : installation stricte, recette ciblée et
upload des artefacts réussis. `gh run watch --exit-status` code 0, état confirmé
par `gh run view`. Ubuntu 24.04 / Node 24 / Python 3.11. Les métriques détaillées
ci-dessus sont mesurées localement, pas extraites du JUnit distant. Ce succès
ciblé n'est pas une exécution verte de la suite OCR complète.

## Limites

Aucune UI de pistes, cache/SW, sélection automatique, décision humaine habilitée,
publication ou mutation de données métier. Pistes littérales non validées seulement ;
phase IA/recherche métier encore partielle. Rejeu identique ne certifie ni origine,
audit serveur, signature, référence externe, fidélité PDF ou applicabilité juridique.
**0 nouvel original officiel acquis, 0 article/code national officiellement validé,
0 publication active.**
