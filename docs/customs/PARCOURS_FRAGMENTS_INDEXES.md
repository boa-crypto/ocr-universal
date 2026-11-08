# Parcourir une page indexée — 100

## Utilisation

Dans la revue documentaire d'un lot de Code, lancer une recherche textuelle ou
une recherche de repères candidats, puis **Lire la page** sur un résultat.

- **Fragment suivant** : continue au point de code immédiatement après le
  fragment affiché, dans la même page physique.
- **Fragment précédent** : remonte de 4000 points de code, sans dépasser le début
  de la page. Un retour en arrière peut recouvrir du texte déjà lu.
- **Revenir au contexte sélectionné** : reprend le décalage d'entrée initial,
  soit jusqu'à 200 points avant un repère candidat, soit 0 pour une page issue de
  la recherche textuelle.

L'intervalle `[début, fin[` affiché est semi-ouvert : début inclus, fin exclue.
Les indices sont des points de code Unicode Python, pas des octets UTF-8, des
unités UTF-16 JavaScript ou des caractères graphiques composés. Des accents
combinés peuvent donc être coupés entre deux fragments. Reconstituer les
fragments suivants dans l'ordre depuis 0 reproduit exactement le texte indexé.

Les commandes indisponibles aux bornes sont désactivées. Elles ne changent pas
de page physique et ne représentent pas le début ou la fin d'un article.
Pour changer de page, sélectionner un autre résultat documentaire.

## Garanties et refus

Chaque lecture doit garder le document, la page, le SHA du PDF, le SHA du texte,
le SHA de l'index et celui du manifeste du résultat d'origine. La longueur totale
est également stable pendant le parcours.

La vue vérifie l'unité Unicode, les longueurs exactes du fragment et de la page,
ainsi que le prochain curseur attendu. Elle refuse notamment un curseur figé,
une chaîne tronquée, une longueur modifiée ou un index remplacé. Le contexte est
alors effacé et ses commandes désactivées. Il faut relancer une recherche pour
prendre en compte un nouvel index légitime.

Le texte est inséré uniquement comme texte, pas comme HTML. Aucun fragment ni
historique de lecture n'est écrit dans le stockage du navigateur. Le changement
de requête, filtre, mode, lot, route ou compte invalide les requêtes tardives.
Une réponse 401/403 retire la vue. Ces contrôles complètent ceux du backend ;
ils ne constituent pas une preuve d'authenticité juridique.

## Exploitation

Aucune nouvelle route ni migration n'est nécessaire au 100. Les GET du 99 sont
réutilisés avec `limit=4000` et leurs offsets Unicode. La version du cache
statique est `unocr-shell-v100-legal-fragments`.

Le serveur partagé antérieur n'a pas été redémarré. Pour utiliser cette vue,
il faut le backend actualisé avec les routes 99 et une identité nominativement
habilitée. Le registre réel reste fermé, sans ajout de compte ou de droit.

Les PDF et l'index existants sont inchangés. La navigation ne corrige ni l'ordre
des colonnes ni les caractères dégradés ; ce n'est ni un OCR, ni une délimitation
d'articles, ni une consolidation juridique. La copie de la loi 17-04 et la
compilation portant Juin 2017 restent des sources reçues non authentifiées.
