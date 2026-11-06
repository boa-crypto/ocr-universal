# Avancement — lot 2 : XLSX et comparaison de préparations

**2026-11-06 — livraison technique partielle, aucune activation réglementaire.**

## Résultat livré

1. `customs-prepare` accepte maintenant XLSX, en plus de CSV UTF-8 et JSON.
   Feuille visible nommée explicitement, mapping déclaré, codes texte conservés,
   zéro initial jamais reconstitué ; formules refusées dans le tableau sélectionné.
   Archives reçues conservées dans un dossier neuf, jamais remplacées.
2. Le rapport décrit le périmètre sélectionné, les feuilles non importées et les
   lignes vides. Les lignes cachées sont lues. Une dimension XLSX mensongère ne
   tronque pas silencieusement les données.
3. `customs-diff AVANT APRES` compare deux préparations locales, sans modifier
   les lots ni les stores : sources, empreintes et horodatages machine déclarés,
   périmètres, codes ajoutés/retirés, désignations, périodes, unités, quatre
   niveaux hiérarchiques et mesures. Les taux sont comparés sans arrondi.
4. Les changements d’identifiant technique/localisateur sont rapportés séparément
   des changements de contenu. Les mesures modifiées conservent leurs références.
5. Un lot incomplet, altéré, actif, symbolique, incohérent avec ses sources ou
   avec son rapport est refusé intégralement (CLI code 2). Les octets vérifiés
   sont ceux utilisés pour le rejeu ; aucune source distante n’est téléchargée.

Les options, bornes et limites sont détaillées dans le [guide](README.md).
`openpyxl>=3.1` était déjà déclaré ; verrou existant `3.1.5`, aucune dépendance
supplémentaire. XLS, PDF, XML et ZIP comme formats d’entrée directs ne sont pas
encore qualifiés. Le conteneur ZIP interne XLSX ne change pas ce constat.

## Validation technique

Fixtures exclusivement **NON OFFICIELLES**, temporaires et non publiées comme
référentiel. La qualification porte sur le lecteur générique, pas sur un fichier
national DGD/ALCES encore absent. Les sources fiscales déclarées dans des sidecars
ne sont pas automatiquement authentifiées ni validées par leur seule structure.

Sélection finale exécutée avec `UNOCR_DATA_DIR` et `UNOCR_LOG_DIR` isolés :

```sh
python -m pytest tests/test_customs_reference.py tests/test_customs_xlsx.py \
  tests/test_customs_comparison.py tests/test_corrections_routes.py \
  tests/test_referentiels.py tests/test_referentiels_base.py \
  tests/test_customs_connector.py -q
```

**155 tests réussis, 1 avertissement** de dépréciation Starlette/httpx.
Cela comprend les **89 tests de la sélection lot 1** et **66 nouveaux cas**
XLSX/comparaison ; ce n’est pas la suite complète du dépôt.
Les 33 cas XLSX ont aussi été rejoués avec `OPENPYXL_LXML=False` :
**33 réussis**, pour contrôler le second moteur XML (sans les recompter comme
nouveaux tests). Ruff `src tests` et `git diff --check` contrôlés également.

Couverture ajoutée : chaînes avec zéros, cellules numériques malgré formatage,
formules, en-têtes, feuille cachée, lignes cachées/vides, dimensions inexactes,
bornes de taille et de parcours, archives dangereuses/actives/dupliquées, DTD
ASCII/UTF-16, XML mal formé avec et sans moteur lxml, intégrité des archives,
rejeu après re-hachage, rapport et types incohérents, traversée/symlinks,
provenance, taux équivalents, très précis et à exposant extrême sans expansion, hiérarchie, versions déclarées
identiques mais différentes, différences de périmètre, compatibilité lot 1,
CLI en processus séparé sans création de stores et refus sans écriture.

Les deux fichiers historiques restent inchangés :

- `data/reglementation/base.json` :
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`
- `data/referentiels.json` :
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`

## Complétude et limites inchangées

- **0 article et 0 ligne tarifaire nationale officiels importés et validés.**
- Aucun original éditeur acquis dans ce lot ; ni nouveau dépouillement exhaustif
  du JO, ni preuve de complétude du tarif national courant.
- `UniOCR_Referentiels_StarterPack` toujours absent du checkout.
- Aucune consolidation applicable, publication, validation juridique humaine,
  API v1 douanière, interface administrateur, recherche FR/AR ou classification
  IA livrée dans ce lot. Les deux calculs legacy non sourcés restent bloqués.
- Empreintes et rejeu prouvent une cohérence locale, pas l’origine officielle,
  l’exhaustivité, l’immutabilité WORM ou l’applicabilité à une date.
- Une disparition entre deux fichiers **ne vaut pas abrogation** ; un changement
  de périmètre doit être examiné avant toute interprétation.

## Prochaines dépendances

Acquérir le StarterPack et les originaux officiels du Code/modifications, puis
le fichier national tarifaire intégral avec sa version et ses sources fiscales.
Qualifier les mappings sur ces fichiers réels et comparer les compteurs,
parents, désignations, périodes, taux et exclusions. La validation habilitée et
tracée demeure un préalable à tout usage douanier réel. En parallèle, les tâches
indépendantes futures restent l’archivage documentaire des textes originaux et
modificatifs séparés, le workflow de revue autorisé et l’intégration aux routes
et composants existants — sans ouverture par défaut du RBAC historique.
