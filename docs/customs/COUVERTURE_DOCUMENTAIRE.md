# Diagnostic de couverture documentaire — lot 11

2026-11-06. **Compteurs du lot reçu, pas complétude du droit applicable.**

## Objectif et frontière

Le service commun `diagnostiquer_couverture` contrôle/rejoue un lot entier puis
produit un état descriptif de ses éléments déclarés. Il n’inspecte pas d’autres
dossiers, ne télécharge rien, n’altère pas les archives et ne remplace pas une
revue juridique. Les mêmes services d’intégrité que les autres lectures de revue
sont utilisés ; un lot corrompu ne produit pas de diagnostic partiel présenté valide.

Le résultat distingue explicitement :

- `integrite_locale=coherente_au_rejeu` : cohérence locale seulement ;
- `completude_reglementaire=non_etablie` ;
- `nombre_officiel_attendu=null` et `pourcentage_completude_reglementaire=null` ;
- `validation_juridique=non_validee`, `publication_active=false` ;
- `utilisable_pour_calcul_douanier=false`.

Aucun nombre national issu d’une annonce/recherche n’est utilisé comme dénominateur.
Il n’existe ni score, ni seuil automatique de publication, ni verdict « prêt ».
Même un lot sans champ manquant reste non validé et ne prouve pas la complétude.

## Indicateurs tarifaires

Compteurs section/chapitre/position/SH6/ligne code10/mesure ; champs non renseignés
FR/AR, unités, dates et taux de ligne ; taux/unités/dates non renseignés des mesures ;
mesures par type ; nombre de lignes sans mesure ; parents déclarés sans ligne code10.

Un parent sans ligne peut simplement appartenir à une hiérarchie plus large que
le fichier reçu : il n’est pas déclaré erroné. Les mesures sont mono-source ; aucun
rapprochement fiscal externe n’est effectué. Depuis le lot 23, les subdivisions nationales sont facultatives et explicitement
déclarées. Le compteur de lignes sans lien est descriptif, pas preuve d’absence
nationale ; aucun code à huit chiffres n’est reconstruit.

Les taux inconnus de ligne restent comptés comme inconnus, sans copie des mesures.
Une mesure à taux déclaré zéro est bien renseignée : elle n’est pas comptée comme
null et ne devient pas applicable. Une restriction sans taux est un constat normal,
pas nécessairement une erreur. Aucune mesure ne prouve pas exonération.

## Indicateurs du Code documentaire

Documents/articles transcrits/numéros exacts distincts/relations ; documents et
articles par nature ; champs de langue, dates et références JO non renseignés ;
documents sans article transcrit ; empreintes PDF identiques signalées sans fusion ;
articles sans relation ; types de relations et occurrences des niveaux hiérarchiques.

Une même disposition peut avoir plusieurs versions : compter les numéros n’est
pas compter des articles juridiquement uniques. Une même empreinte PDF ne donne
pas lieu à suppression ou changement de rôle documentaire. Une relation absente
ne prouve pas absence de modification. Des niveaux sans occurrence ne signifient
pas que chaque article devrait obligatoirement les posséder.

`texte_francais` ou `texte_arabe` absent ne prouve pas l’absence de cette langue
ailleurs dans `texte_integral` ou dans le PDF. La date d’article manquante n’est
pas remplie depuis la date du document. Zéro article transcrit est possible ;
les compteurs de champs manquants valent alors zéro par absence d’éléments,
**pas parce que les documents seraient intégralement transcrits**.

Un champ non renseigné signifie null ou chaîne vide/blanche ; les valeurs reçues
ne sont pas normalisées/réécrites. Les champs optionnels ne deviennent pas des
exigences juridiques universelles. Aucun calendrier des actes manquants n’est inféré.

## Accès

```sh
PYTHONPATH=src python -m unocr.cli customs-coverage /chemin/lot --type tarif
PYTHONPATH=src python -m unocr.cli customs-coverage /chemin/lot-code --type code
```

Type explicite, pas d’autodécouverte. JSON en lecture seule, code retour 0 si le
rejeu réussit, 2 si refus. Un type incompatible est refusé. Le CLI local nécessite
l’accès au système de fichiers, pas une nouvelle habilitation de validation.

GET `/api/v1/customs-review/lots/{lot_id}/coverage` utilise le **type inscrit dans
le registre serveur**, avec les droits nominatifs habituels, épingle avant lecture
comparée à celle du lecteur, audit opération `couverture` et `no-store`. Pas de
chemin local choisi par HTTP. Le résultat contient l’ancrage de l’archive, les IDs,
SHA256 et marqueurs de non-vérification des sources, sans dump des transcriptions.
Aucune nouvelle base, aucun cache de diagnostic.

Dans Administration → Revue douanière · quarantaine, sélectionner le lot puis
**Diagnostiquer la couverture documentaire**. Le bouton s’applique au Code comme
au tarif ; il ne reprend pas les filtres de recherche ou un code/article saisi.
Rendu JSON texte dans la même zone et mêmes protections de réponses tardives,
d’accès et de confidentialité que les autres lectures. Coque service worker v43 ;
API toujours exclue du cache.

## Limites restantes

Un seul lot à la fois, pas de comparaison avec un corpus officiel exhaustif,
de qualification de signature PDF, d’authenticité, de traduction/transcription,
de consolidation, de validation humaine, de publication ou de calcul.
Les limites de concurrence et taille du rejeu restent applicables ; aucun benchmark
national ou garantie globale mémoire/temps supplémentaire. JSDOM ne remplace pas
la qualification complète d’un navigateur/lecteur d’écran ou d’un déploiement.

[Rapport et qualification](RAPPORT_LOT11.md). Les originaux, modifications,
tarif national et sources fiscales restent à acquérir et vérifier humainement.

[Subdivisions nationales déclarées et compatibilité](SUBDIVISIONS_NATIONALES.md).
