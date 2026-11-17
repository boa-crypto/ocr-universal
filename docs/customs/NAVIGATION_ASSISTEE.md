# Navigation assistée dans les résultats de revue — lot 14

2026-11-06. **Raccourcis de consultation, pas relations juridiques supplémentaires.**

## Parcours ajoutés dans la coque existante

Dans Administration → Revue douanière · quarantaine, les réponses reconnues
peuvent présenter des boutons de lecture en plus du rapport JSON et de ses
avertissements :

- recherche Code → **Lire la version ID** pour l’ID effectivement retourné ;
- historique → lecture des versions et du contexte des relations, sans doublon
  d’ID et sans déduire une succession juridique ;
- recherche tarifaire ou feuilles de l’arbre → **Fiche documentaire CODE10** ;
- navigation tarifaire → **Enfants de ID/CODE**, au niveau suivant déclaré et
  cohérent avec la chaîne sections → chapitres → positions → SH6 → codes10 ;
- navigation tarifaire paginée → **Page suivante des enfants**, si le serveur
  fournit un décalage suivant entier, croissant et compatible avec les totaux ;
- lecture d’article → **Fragment suivant de l’article**, pour le même ID et champ,
  avec la limite et le décalage fournis par le service en points de code Unicode.

Ces raccourcis n’ajoutent aucun endpoint, source, téléchargement, classement,
validation ou publication. Un bouton ne constitue pas une relation juridique.
Les actions ne reprennent **jamais une URL de source** ; elles appellent seulement
les routes relatives de revue déjà protégées, avec IDs/codes/plages explicites.
Les identifiants et libellés de boutons sont du texte DOM, jamais du HTML.

## Paramètres et continuité

Ouvrir une version depuis recherche/historique choisit explicitement son
`texte_integral`, limite 4000, décalage 0 ; ce n’est pas un choix de version applicable
ou de traduction. Le formulaire permet ensuite de sélectionner FR/AR/origine/
modificatif. Une fiche ouverte par raccourci repart à la première page de mesures,
limite 20, sans fixer de taxe applicable. Une descente hiérarchique repart à la
première page d’enfants, limite 20. La page suivante conserve niveau, parent et
limite du rapport qui l’a proposée, pas des champs modifiés depuis.

Le fragment suivant conserve ID/champ/limite du rapport et reprend
`decalage_suivant`, sans calcul basé sur `String.length` JavaScript. L’unité de
pagination doit être celle annoncée par le service, pas UTF-16. Pas de bouton
suivant en fin, pour langue/ID absent ou si les paramètres retournés sont invalides.
Les fragments ne sont pas accumulés dans le navigateur : la nouvelle lecture
remplace la précédente et relance intégrité, épingle et autorisation serveur.

Les sélecteurs et saisies restent disponibles pour revenir à la racine, choisir
une autre version/langue ou saisir une plage. La navigation tarifaire n’est pas
encore un arbre graphique dépliable avec fil d’Ariane ; ce lot évite la recopie
manuelle des IDs pour la descente et l’ouverture des fiches.

## Cloisonnement et limites

La zone d’actions est effacée avec le résultat à chaque nouvelle requête,
changement de lot/niveau ou navigation. Les boutons sont liés à la génération
de requête, au lot et à la session qui ont produit le rapport : un ancien bouton
conservé/détaché est inerte après remplacement. Un changement de jeton détecté
refuse l’action, efface les outils et demande l’actualisation des lots.
La révocation de droits reste autoritaire **côté serveur à chaque lecture** ;
elles ne retirent pas une information déjà lue/copiée. Pas de protection contre
un poste/extension compromis, pas d’effacement forensique ou DLP.

IDs/chiffres, niveaux et plages des actions sont contrôlés ; le backend garde
ses validations et droits. Les résultats restent non validés/non publiés, avec
provenance visible. Aucun lot fictif installé pour montrer ces boutons dans la
prévisualisation anonyme : celle-ci conserve le refus attendu de la revue.
Coque service worker v46 ; pas de nouvelle persistance de documents ou cache API.

Qualification : **36 scénarios JSDOM** et parcours HTTP/API réel isolé étendu.
JSDOM ne remplace pas une qualification visuelle, clavier/lecteur d’écran complète
ou un benchmark national. [Rapport lot 14](RAPPORT_LOT14.md).
