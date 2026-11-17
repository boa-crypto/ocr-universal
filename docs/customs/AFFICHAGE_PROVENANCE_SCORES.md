# Affichage des compteurs de scores par run — lot 68

7 novembre 2026. S'appuie sur la [provenance persistée du lot 67](PROVENANCE_SCORES_PERSISTEE.md).

## Dans l'interface existante

Le panneau moteurs du résultat affiche chaque exécution : moteur, page, numéro
ordinal de run, état, moyenne enregistrée, nombre d'éléments et durée si disponibles.
Un moteur unique n'est plus remplacé par une invitation à installer d'autres
moteurs. Les moyennes ne sont plus agrégées par moteur dans ce panneau : les runs
peuvent inclure plusieurs variantes d'une même page. Leur ordre n'est pas un
classement, et leur numéro n'identifie pas une variante de prétraitement nommée.

Pour Baidu, une provenance cohérente affiche les compteurs déclaré/absent/invalide
et rappelle la non-calibration, le repli zéro et la portée par run, pas par mot.
Aucune jauge verte de classement ou de précision mesurée n'est créée. Un run vide
est explicitement indiqué sans lui attribuer un score mesuré.

Un ancien score élevé reste une **moyenne enregistrée non qualifiée**, avec
« Provenance indisponible ». Aucun compteur n'est déduit de sa seule valeur.
Aucun compteur Baidu n'est attribué aux autres moteurs. Un run échoué est annoncé
comme tel ; son erreur brute n'est pas réaffichée dans ce panneau.

## Contrôles locaux, pas certification

Le module vérifie les champs attendus, la politique connue, `calibrated: false`,
les nombres entiers JavaScript bornés, leur somme, le plafond de moyenne et
l'association à un run Baidu réussi sur la même page. Les chaînes, booléens,
valeurs non finies, champs supplémentaires et incohérences sont refusés.
Après décodage JSON, JavaScript ne distingue pas les écritures numériques `1`
et `1.0` ; ces contrôles ne certifient pas la syntaxe du JSON d'origine.

Une incohérence entraîne « Provenance indisponible », sans afficher la charge
invalide, ni inventer de compteurs. Chaque rendu remplace le précédent ; les
anciens compteurs ne restent pas affichés. Les noms moteurs sont échappés en HTML,
les valeurs numériques affichées sont contrôlées. Pas requête ou écriture ajoutée.

Le module dédié est chargé avant `app-extras.js`. Son absence entraîne un message
explicite dans le panneau, pas un affichage résiduel. Le service worker passe à
`unocr-shell-v71-engine-provenance` et inclut le module dans sa coquille ; sa règle
de non-cache des API est inchangée. Pas qualification d'un cycle offline réel.

## Vérification et portée

Le harnais télécharge le HTML et les trois modules complets par HTTP sur un
serveur applicatif éphémère, puis les exécute dans JSDOM. Pour l'intégration,
les scripts complets sont évalués dans un même contexte lexical, afin de préserver
les variables partagées des scripts classiques du navigateur. Les données de
provenance sont des contrats synthétiques injectés : **pas résultats Baidu réels**.
Le harnais existant prépare deux PDF natifs synthétiques, pas un corpus officiel.

Les 47 scénarios couvrent aussi le rendu complet du résultat, le module absent,
les métadonnées corrompues, les frontières de compteurs/moyennes, les pages/runs
multiples, la non-mutation, les noms hostiles et l'effacement des anciens détails.
Ils ne constituent pas une recette de navigateur réel, clavier, lecteur d'écran,
charge, fidélité visuelle ou précision OCR FR/AR.

## Inchangé et non couvert

Aucune migration/requalification des jobs historiques, calibration, comparaison
scientifique des moteurs, provenance individuelle par mot, signature ou preuve
d'authenticité fournisseur. Les jauges de qualité et les autres écrans ne sont
pas recalculés pour les anciens résultats : le message de provenance est limité
au panneau moteurs. Aucune règle de validation humaine ou fiscale n'est modifiée.

L'endpoint Baidu, sa géométrie approximative et les risques OAuth query restent
inchangés. Aucun appel distant Baidu ou nouvel original officiel n'est acquis.
Voir [rapport et recette](RAPPORT_LOT68.md).
