# Lot 63 — contrôler les modules réellement servis

7 novembre 2026. Qualification technique sur données synthétiques, pas navigateur
réel, accessibilité, rendu visuel, charge ou validation douanière.

## Défauts corrigés dans les contrôleurs

Les harnais historiques cherchaient une région DOSSIER inline et le dernier bloc
`<script>` du HTML. Après modularisation, `/dossier.js`, `/formulaire.js`,
`/tracabilite.js`, `/transmission.js` et `/connectors.js` sont des fichiers séparés.
Le test optionnel du lot 62 échouait donc avant de contrôler ces modules.

- Lecture **HTTP** de `/`, analyse HTML avec JSDOM sans exécuter les scripts ou
  charger de ressources, vérification d'une seule référence exacte par module,
  puis lecture de ces cinq chemins sur le **même serveur loopback**.
- Aucun repli sur une copie de disque ou une ancienne région inline. Chemins
  fixes, port ASCII 1–65535, réponse HTTP 200 exigée, pas de redirection,
  limite 2 MiB par réponse et délai d'inactivité HTTP 5 secondes. Ce harnais
  n'est pas un téléchargeur public ni une sandbox de scripts non fiables.
- Les compteurs **55 assertions documentaires et 21 assertions Hub** sont
  maintenus. Rejets, exceptions, erreurs `[FAIL]/[KO]`, sortie incomplète et
  code enfant non nul deviennent des échecs du processus parent.
- Le parent attend le résultat des contrôles asynchrones avant son statut final.
  Plus de variable locale `ko` masquant la fonction de signalement. Plus de
  génération/copie de `_hub_render.js` ; seuls les sources canoniques s'exécutent.
- Les fichiers de contrôle statique sont créés dans un répertoire temporaire
  système propre, pas dans `tests/` avec des noms partagés.

## Serveur de recette isolé

`tests/ui_render_server.py` démarre un processus UniOCR temporaire sur un port
libre, écoute `0.0.0.0`, puis vérifie son état HTTP. Données, journaux et profils
utilisateur sont sous `tmp_path`. Deux PDF **synthétiques réellement générés**
sont envoyés par l'API `/api/documents`, puis attendus en état `done`.
Lecture native demandée, sans tableaux/barcodes : ce test ne dépend donc pas de
l'installation de Tesseract/Indra et ne prétend pas qualifier leur reconnaissance.
Les documents ont les noms de référence nécessaires aux sept assertions de
cohérence qui étaient autrement conditionnelles à l'état du magasin.

La réponse d'anomalie connue reste simulée dans la partie de vérification de
l'affichage des constats, comme avant : **ce n'est pas une preuve de cohérence
métier calculée sur ces PDF**. Les autres actions utilisent l'API temporaire réelle,
y compris création de dossier, traitement des PDF, association de pièces et paquet.
Aucune transmission administrative réelle n'est effectuée.

Les deux dépôts sont séquentiels. Un premier essai de fixture avec dépôts
concurrents a perdu son serveur pendant le suivi des jobs ; cause non établie,
pas annoncée corrigée. Cette recette ne qualifie pas l'ingestion concurrente.
Le processus est arrêté en fin de fixture, avec arrêt forcé borné si nécessaire.
Les premiers essais exploratoires sur l'aperçu ont créé des dossiers synthétiques
locaux ; ils restent hors commit, comme les journaux historiques. Les recettes
finales utilisent uniquement le magasin temporaire.

## Exécuter

```sh
npm ci
.venv/bin/python -m pytest tests/test_ui_render_contract.py tests/test_ui_dossier.py -q
node --test --test-reporter=tap tests/ui_served_modules.test.js
```

Le premier appel démarre son propre serveur : ni aperçu actif ni port 8123 requis.
L'absence de Node garde le marqueur d'ignoré explicite existant ; en CI Node 24 est
installé. Une erreur de démarrage/traitement/rendu n'est jamais un ignoré.

Le contrôleur Node peut aussi être appelé séparément :

```sh
node tests/ui_stub_check.js --static
PORT=8000 node tests/ui_stub_check.js --require-render
```

`--static` ne sonde pas de serveur. Sans option, seul un **ECONNREFUSED** du
serveur facultatif permet de signaler « rendu non exécuté » ; HTTP 500,
module 404, syntaxe invalide, timeout ou assertion ratée sont des échecs.
`--require-render` refuse aussi le serveur absent. Un serveur externe non préparé
peut légitimement échouer aux 55 assertions : le test pytest prépare ses entrées,
il ne dépend plus des documents présents sur le poste.

## Régressions et CI

Six nouveaux cas Python, dont un lance **24 contrats Node imbriqués**. Ceux-ci
contrôlent la source HTTP effective, les références absentes/dupliquées/externes,
les faux `data-src`/commentaires, HTTP 302/401/404/500, la taille, les ports,
les compteurs incomplets et erreurs de callbacks. Les cas Python vérifient le
statut final du parent pour serveur absent facultatif/obligatoire, HTTP 500,
module 404 et JavaScript invalide, serveur pourtant joignable.

Le workflow ajoute une étape de huit tests (six nouveaux + deux existants),
séparée de la sélection documentaire historique. Les deux sélections ne sont
pas une suite OCR complète. JUnit de rendu archivé avec les autres artefacts ;
en cas d'échec, détails des fixtures synthétiques exposés en annotations GitHub
sans masquer le statut de l'étape en échec.

Le premier run a révélé une différence de reporter Node : le défaut Node 24
imprime `ℹ fail 0`, là où Node 22 donnait `# fail 0`. Les 24 contrats passaient,
mais l'assertion de format échouait. **TAP est maintenant explicitement demandé**,
sans suppression de l'assertion ni transformation d'un échec fonctionnel.
