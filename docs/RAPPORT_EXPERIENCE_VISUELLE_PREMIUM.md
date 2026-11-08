# UniOCR — Expérience visuelle premium et motion design

## Livré

La coque existante reste un outil métier : les visuels expliquent le parcours documentaire, les animations orientent l’attention et les fonctions/API demeurent inchangées.

### Identité visuelle et illustration

- **Illustration SVG originale sur mesure** : pièces sources → lecture OCR → champs structurés. Papiers en perspective, profondeur, grille discrète et palette vert/sauge cohérente avec UniOCR.
- Visuel vectoriel net à toute résolution, **3 551 octets**, servi localement. Aucune banque d’images, aucun service tiers ou image lourde.
- Composition intégrée au cockpit sur ordinateur ; bande illustrée sous les trois actions sur tablette/mobile. La priorité reste aux actions sur petit écran.
- Dimensions intrinsèques et ratio réservés ; cadrage adapté, texte alternatif sur le visuel principal et légende indiquant explicitement qu’il s’agit d’une illustration, pas d’une extraction réelle.
- Fond radial subtil, accents graphiques des cartes, profondeur au survol et continuité du thème sombre.

### Mouvement utile

| Interaction | Effet implémenté |
|---|---|
| Entrée d’une carte ou d’un panneau dans la vue | Révélation progressive courte, une seule fois par élément, via IntersectionObserver |
| Changement de route | Entrée discrète de 220 ms, sans attendre l’animation pour naviguer ; remplacement de l’ancienne animation concurrente |
| Boutons et cartes d’action | Feedback de pression de 170 ms ; relief, bordure et déplacement subtil au survol sur appareils disposant d’un vrai survol |
| Palette et menus notifications/aide/profil | Ouverture de 180 ms ; fermeture immédiate conservée pour ne pas retarder le focus ou bloquer les actions |
| Mise à jour des compteurs | Transition de la valeur réelle par opacité/déplacement ; aucun nombre intermédiaire inventé ni écriture dans les données |
| Chargement réellement actif | Indicateur circulaire personnalisé lié aux états `is-busy` / `aria-busy`, pas de faux chargement |
| Graphiques | Réutilisation des tracés et transitions du moteur SVG existant, déjà sensible à la préférence de réduction du mouvement |

Les animations JavaScript utilisent la **Web Animations API native** ; les micro-interactions légères utilisent CSS. Aucun ajout de Framer Motion, GSAP, Lottie ou WebGL : ces bibliothèques et une parallaxe décorative n’apporteraient ici aucune valeur proportionnée à leur coût et au risque de distraction.

### Accessibilité et performances

- `prefers-reduced-motion` neutralise les nouvelles animations et les animations CSS héritées de la coque ; un changement de préférence en cours de session annule les animations actives.
- Les contenus ne sont jamais initialement cachés dans l’attente d’un observateur. Sans API d’animation, l’interface reste lisible et utilisable.
- Animations d’entrée fondées sur **transform et opacity**, durées bornées, décalage progressif limité à 140 ms, pas de boucle décorative permanente.
- Arrêt des animations JavaScript actives quand l’onglet devient invisible ; animations terminées retirées du registre.
- Valeurs métier et annonces inchangées : pas de compteur défilant donnant temporairement de fausses quantités.
- Nouveaux JS + CSS + SVG : **14 123 octets non compressés**, hors métadonnées et tests. Aucune dépendance d’exécution supplémentaire.
- Ressources intégrées au service worker **v103-visual-motion** ; pas de changement de CSP et toujours aucune mise en cache des API.

## Contrôle qualité et corrections

Les premiers relevés de stabilité visuelle montraient des décalages importants au chargement, surtout sur tablette : ajout tardif du fil d’Ariane et des raccourcis après initialisation de la navigation autorisée. Le HTML réserve maintenant leur espace **sans rendre de liens non autorisés**. Le contrôleur réutilise l’emplacement réservé et conserve son filtrage des destinations.

Les six mesures finales de **CLS de laboratoire** sont comprises entre **0,002 et 0,006**, sous le budget de test fixé à **0,05**. Il reste donc de très faibles variations au chargement : ce n’est ni une promesse de CLS strictement nul ni une mesure terrain de toute l’application.

### Résultats

- **72 tests pytest ciblés réussis**, 1 avertissement de dépendance FastAPI/Starlette existant ; Ruff et `git diff --check` réussis.
- Tests JSDOM : révélations, feedback, intégrité des valeurs, arrêt dynamique en mode réduit, initialisation idempotente ; scénarios produit existants et **23 scénarios de catalogue juridique** également réussis.
- **306 passages de routes** dans Chromium : ordinateur 1440 px, tablette 834 px, mobile 390 px ; **0 exception JavaScript, 0 débordement horizontal de page, 0 tentative d’écriture HTTP**.
- Recette motion distincte sur **six configurations** : trois largeurs × mouvement normal/réduit. Vérification des images chargées, interactions des menus, état de la palette, budget CLS, absence de mutation réseau et changement dynamique de préférence.
- En mode réduit : **0 appel aux nouvelles animations JavaScript**, **0 animation de palette**.
- Captures du cockpit relues sur ordinateur, tablette et mobile ; inspection complémentaire de l’illustration en thème sombre.
- **CI documentaire/JSDOM réussie** pour le code `fae03a23` : [exécution 42486070190](https://github.com/boa-crypto/ocr-universal/actions/runs/42486070190). Ce workflow ne prétend pas être la suite OCR complète.
- **27 empreintes sur 27 identiques aux valeurs observées au lot 101**. Aucun fichier de données ou journal ajouté aux commits.

Une tentative de capture Chromium a expiré pendant l’exécution parallèle des recettes. La recette complète a été rejouée isolément, sans clic forcé ni désactivation de la CSP ; le diagnostic est conservé hors du dossier de captures finales.

La suite Python complète n’a pas été réexécutée dans cette étape exclusivement visuelle. Ses deux échecs environnementaux Indra documentés lors de l’étape précédente ne sont pas présentés comme résolus. Les résultats ci-dessus sont ceux de la recette de cette étape, pas une réutilisation des anciens chiffres de suite complète.

## Fichiers et reproduction

- `web/assets/document-flow.svg` : illustration locale.
- `web/visual-motion.js`, `web/visual-motion.css` : orchestration, interactions, préférence de mouvement et composition.
- `web/index.html`, `web/product-experience.js` : intégration et réservation de l’espace.
- `web/sw.js` : cache des nouveaux assets ; version attendue adaptée dans le test de provenance.
- `tests/ui_visual_motion.cjs`, `tests/ui_visual_motion_browser.cjs`, `tests/test_ui_visual_motion.py` : tests d’exécution, navigateur et contrats.

```sh
npm run ui:motion
npm run ui:motion:browser
npm run ui:product -- http://127.0.0.1:8000 /home/user/recettes-unocr/visual-motion/browser
.venv/bin/python -m pytest tests/test_ui_visual_motion.py tests/test_ui_product_experience.py tests/test_ui_premium.py tests/test_ui_engine_provenance.py tests/test_web_architecture_refactored.py -q
```

Preuves hors Git : `/home/user/recettes-unocr/visual-motion/`, notamment `browser/browser-report.json`, `motion/report.json`, captures, `targeted.log`, `empreintes.json` et `ci.json`.

## Limites

Validation sur Chromium, pas certification de tous les navigateurs ni benchmark de FPS sur téléphone physique. Le CLS mesuré est un indicateur de recette locale, pas une mesure terrain. Aucun déploiement de production, changement d’habilitation, migration ou manipulation de document métier. Les illustrations ne modifient pas le statut non validé/non publié des sources juridiques.
