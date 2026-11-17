# Rapport97 — comparaison des déclarations et pistes d'un dossier

**Extension documentaire livrée et testée ; mission globale partielle, non
recevable pour production fiscale.** Pas d'IA, expertise ou droit consolidé
revendiqué. Aucun nouvel original officiel, article/code officiellement validé
ou publication active.

## Fonction opérationnelle sur environnement de test

Nouvelle vue API et UI réunissant, pour une version précise du dossier :

- les cinq caractéristiques produit déclarées ;
- les pièces associées et leur provenance (SHA du texte, auteur, date, localisateur) ;
- les déclarations d'attributs avec citations exactes ;
- l'égalité exacte avec le produit et les valeurs textuellement différentes ;
- les candidats littéraux du snapshot, leurs références, termes et extraits ;
- des questions sur les champs manquants, citations absentes et écarts à examiner.

La vue ne réécrit pas le dossier, ne crée pas de version, ne remplit pas le
produit et ne reclasse pas les candidats. L'état est identifié par version,
manifest et SHA canonique du dossier. L'interface distingue la version enregistrée
du brouillon local ; consulter une comparaison historique ne réactive pas les
écritures. Rendu textuel uniquement, contrôle de contexte et enveloppe de réponse.

La nouvelle route `GET .../assessments/{id}/comparison?version=N` conserve RBAC,
allowlist, revalidation complète du lot tarifaire, intégrité des versions/pièces,
audit obligatoire et réconciliation de l'outbox. Version absente/invalide et
source modifiée sont refusées. Une lecture peut encore retourner503 si l'audit
est indisponible ; elle ne crée pas de nouvelle version métier.

Contrat : [COMPARAISON_DECLARATIONS_DOSSIERS.md](COMPARAISON_DECLARATIONS_DOSSIERS.md).

## Fichiers

- `src/unocr/customs_reference/assessment_comparison.py` : projection déterministe,
  provenance, questions et égalité exacte, sans muter ni partager les objets source.
- `src/unocr/routes/customs_review.py` : endpoint autorisé courant/historique.
- `web/customs-assessments.js`, `web/sw.js` : bouton explicite, vue textuelle et cache97.
- `tests/test_customs_assessment_comparison.py`, scénarios JSDOM/HTTP, contrat de
  cache et sélection CI ; documentation d'achèvement actualisée.

Code **b583cb8e1806838f122cf4eb39016e642858ffb3**, poussé sur la branche de session.
Aucun fichier de données ou journal partagé inclus dans ce commit.

## Validation

| Vérification | Résultat |
|---|---|
| Nouveaux cas Python | **20** |
| Sélection métier/revue/UI | **146 réussis**, aucun échec/ignoré |
| Recette documentaire | **2264 réussis**, aucun échec/ignoré |
| JSDOM métier | **28 scénarios réussis**, incluant les26 précédents |
| JSDOM historique | **212 scénarios réussis**, distincts |
| API réelle via HTTP isolé | Comparaison explicite de version1 après création/révision/relecture réussie |
| Suite complète | **4419 réussis, 2 échecs Indra historiques, 1 ignoré**, 385,42s |
| CI ciblée | [42473845675 : réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42473845675), SHA exact |
| Ruff source/tests/recette, syntaxe JS et diff | Réussis |
| Intégrité historique | **26/27**, même écart préexistant du référentiel partagé |

Les sélections se recouvrent ; ne pas additionner leurs effectifs. Les deux échecs
complets restent `tests/test_indra_ocr.py::test_indra_engine_availability` et
`tests/test_ocr.py::test_selection_prefers_native_when_present`. Le test de
reconnaissance Indra demeure ignoré ; aucun modèle réel téléchargé hors des hôtes
autorisés et aucun échec masqué.

Tests couvrant notamment citations/provenance et empreinte, absence de mutation,
absence de partage d'objets source, différences de casse/espaces/graphies arabes,
valeurs identiques sans score de confiance, pièces sans citation, versions
anciennes, refus d'accès, source altérée, abstention, audit503 puis récupération
sans nouvelle version et absence de reclassement après ajout d'une pièce.
L'UI refuse une réponse prétendant certifier un attribut et n'interprète pas les
chaînes hostiles comme HTML. JSDOM n'est pas une réception navigateur réelle.

Reçu : [RECETTE_LOT97.json](RECETTE_LOT97.json). Artefacts bruts hors dépôt :
`/home/user/recettes-unocr/lot97/`. Empreinte historique attendue du référentiel
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`, observée
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d` : même écart
préexistant préservé, aucune restauration pour rendre le résultat vert.

## Limites et suite réelle de la mission

**Différence textuelle ≠ contradiction technique ; égalité ≠ preuve de vérité.**
Pas de normalisation des valeurs déclarées, synonymes, traduction, interprétation
de négation, probabilité, attribut technique certifié ou raisonnement RGI.
Les candidats restent ceux de la recherche littérale du produit enregistré,
pas ceux des pièces ; au plus les20 déjà présents, avec indicateur de troncature.

La comparaison technique sémantique discriminante et l'ontologie/IA restent donc
non livrées. Restent également corpus officiel exhaustif FR/AR/versionné, mesures
fiscales sourcées, droit à date et règles qualifiées, relations juridiquement
prouvées, originaux PDF/images authentifiés, séparation des responsabilités,
publication contrôlée et intégration centrale. Du développement reste ouvert ;
les sources, cas de qualification et habilitations nécessaires ne sont pas
remplacés par des fixtures. Les sites officiels restent hors des hôtes réseau
autorisés dans cet environnement.

Les limites96 de confidentialité, conservation des pièces retirées, permissions
POSIX, outbox au moins une fois et sauvegarde non distribuée restent inchangées.
L'API de l'aperçu partagé demeure backend76, sans redémarrage, déploiement ou
activation du RBAC réel. Les fichiers Web sur disque évoluent et peuvent être
servis après rechargement ; ce processus n'est pas une qualification bout-en-bout97.
