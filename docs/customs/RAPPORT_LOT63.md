# Rapport lot 63 — rendu des modules servis et échecs non masqués

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Le contrôle supplémentaire UI en échec au lot 62 est réparé sans réduire ses
assertions. Il lit désormais la page puis ses modules externes **par HTTP**,
au lieu de rechercher une région inline disparue. Le statut du contrôleur parent
attend les vérifications asynchrones et refuse les faux succès.

[Contrat et limites](RENDU_MODULES_SERVIS.md), [recette machine](RECETTE_LOT63.json).

## Livré et réellement exécuté

- **55 assertions documentaires + 21 assertions Hub**, sur DOM simulé avec
  modules réellement servis et API temporaire réelle. Compteurs maintenus.
- Le test démarre un serveur isolé et y dépose deux PDF synthétiques traités en
  lecture native. Plus de dépendance à un aperçu/port 8123 ou aux dossiers du
  poste, plus d'ignoré du rendu faute de serveur. Pas besoin de Tesseract/Indra
  pour cette sélection ; elle n'est pas une qualification OCR.
- **6 nouveaux cas Python**, dont un exécute **24 contrats Node imbriqués** :
  source HTTP, références HTML/ports/taille, statuts HTTP, erreurs de modules,
  bilans incomplets et statuts du processus parent. Ces deux niveaux de compteurs
  ne sont pas additionnés artificiellement aux totaux Python.
- Sélection de rendu finale : **8 réussis, 0 échec, 0 ignoré, 37,56 s**.
- Sélection documentaire historique : **2 160 réussis, 0 échec, 0 ignoré,
  1 avertissement, 55,57 s**, 66 fichiers. Ruff et **212 scénarios JSDOM** réussis.
  Les 74 exports existants des quatre ponts restent contrôlés ; pas nouveau
  parcours métier ou validation juridique attribué.
- **Complète finale : 3 238 réussis, 2 échecs, 1 ignoré, 1 avertissement,
  328,63 s**, soit **3 241 tests**, code **1**. Durée JUnit 327,602 s, distincte
  de la durée console. Lecteur JUnit : compteurs cohérents avec les cas réels,
  sélection complète non verte. Le rendu documentaire passe dans cette complète.
- Les deux échecs sont exactement ceux du lot 62, liés à Indra absent :
  `test_indra_engine_availability` et `test_selection_prefers_native_when_present`.
  L'unique ignoré est `test_indra_engine_recognize`. Pas d'assertion de moteur
  relâchée, moteur simulé déclaré disponible ou contournement réseau des modèles.
- **27/27 empreintes historiques conformes**, benchmark PNG et cache suivis propres,
  sans restauration après les tests de ce lot. Journaux historiques et données
  exploratoires locales hors commit. Artefacts : `/home/user/recettes-unocr/lot63`.

Première complète avant normalisation du reporter pour Node 24 : 3 238 réussis,
2 échecs, 1 ignoré, 1 avertissement, 347,03 s. Elle n'est pas le résultat final.
Les durées sous charge de recettes concurrentes ne sont pas un benchmark terrain.

## CI vérifiée, y compris les essais en échec

Code final **`d02d6583`**, run
**[42396949741](https://github.com/boa-crypto/ocr-universal/actions/runs/42396949741)**
terminé **success** : nouvelle étape de rendu isolé puis sélection documentaire
historique réussies, artefacts déposés. Ubuntu 24.04, Python 3.11, Node 24.
Cette CI **n'exécute pas la suite OCR complète** ; les chiffres détaillés ci-dessus
sont mesurés localement. Métadonnées et statuts contrôlés via `gh`, pas de JUnit
distant téléchargé.

Les runs préliminaires **42396443610** et **42396771271** ont échoué : Node 24
emploie par défaut le reporter spec (`ℹ fail 0`) alors que le contrôle attendait
le TAP (`# fail 0`). Les 24 contrats passaient, mais l'assertion de format échouait.
Reporter TAP désormais explicite ; assertion conservée. Lecture brute des logs
GitHub bloquée par l'hôte de résultats hors allowlist : pas contournement.
L'étape diagnostique ajoute maintenant les échecs synthétiques JUnit aux
annotations GitHub, ce qui a permis d'identifier le problème par l'API normale
des checks. Elle ne masque pas le statut de l'étape en échec.

## Limites maintenues

Le DOM est simulé et la réponse d'anomalie utilisée pour certaines assertions
d'affichage reste explicitement simulée ; pas preuve de cohérence métier réelle,
rendu visuel, clavier, accessibilité, charge ou navigateur réel. Les actions API
et les PDF synthétiques du serveur temporaire sont réels, sans transmission
administrative externe. Premier essai de fixture avec dépôts concurrents : perte
du serveur, cause non établie ; les dépôts finaux sont séquentiels, sans prétendre
corriger ou qualifier la concurrence.

Tesseract local PNG/PNM, OpenCV headless et suspension du cache du lot 62 inchangés.
Aucun nouveau codec, modèle, déploiement de production, API métier ou écran livré.
**Mission réglementaire partielle : 0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.**
