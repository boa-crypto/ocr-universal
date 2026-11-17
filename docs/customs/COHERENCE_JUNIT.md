# Cohérence du JUnit avant bilan ciblé positif — lot 61

Le lanceur du lot 57 comparait seulement les totaux déclarés des suites : un XML
bien formé annonçant un cas réussi sans contenir de `testcase` pouvait satisfaire
ce contrôle. Il ne suffisait donc pas à établir la cohérence interne du rapport.

## Contrôle actuel

`bilan_junit` vérifie désormais chaque suite avant toute agrégation :

- racine `testsuite` ou `testsuites` ; suites plates, pas suites/cas imbriqués ou
  masqués dans des métadonnées ;
- quatre compteurs requis par suite, entiers ASCII non négatifs sur 1–9 chiffres ;
- compteurs calculés depuis les `testcase` directs et leurs statuts directs
  `failure`, `error`, `skipped`, puis égalité exacte avec les valeurs déclarées ;
- au plus un statut d'échec/erreur/ignore par cas, pas statut inconnu ou caché ;
- métadonnées `properties/property`, `system-out`, `system-err` admises dans les
  formes attendues, sans structure cachant des cas/statuts ;
- compteurs éventuels de la racine `testsuites` égaux aux sommes vérifiées.

Une sélection ne réussit que si **toutes les étapes retournent zéro**, qu'au moins
un cas est présent, que les compteurs correspondent aux cas et qu'aucun cas n'a de
statut failure/error/skipped. Un échec réel avec compteurs cohérents reste lisible,
mais ne devient pas vert. Des compteurs négatifs de plusieurs suites ne peuvent
pas se compenser lors de l'agrégation.

Le bilan ajoute `compteurs_coherents_avec_cas`. Pour un rapport incompatible ou
illisible : false, `lisible:false`, `selection_sans_echec_ni_ignore:false`. Il ne
recopie pas texte d'erreur, sortie capturée, nom de cas ou contenu de document.

## Lecture bornée

Lecture unique d'un fichier régulier, limite **32 Mio** sans troncature acceptée.
Symlink final refusé (`O_NOFOLLOW` si disponible), FIFO/non-régulier refusé avant
lecture, mode non bloquant si disponible. UTF-8 requis, NUL/UTF-16, DTD et déclarations
d'entités refusés ; profondeur limitée à 16 pendant l'analyse XML par morceaux.
Pas validation XSD universelle de JUnit, pas prise en charge de tous les dialectes
ou plugins de rerun. Le format pytest effectivement produit est qualifié.

Ce contrôle porte sur le **document reçu**, pas sur l'authenticité de l'exécution.
Un auteur peut fabriquer un rapport complet et cohérent ; aucune signature,
identité de runner, test lancé, exhaustivité d'une sélection ou origine officielle
n'est certifiée par XML. Les cas sans identité, ou identités dupliquées, ne sont
pas authentifiés. Pas transaction/verrou filesystem, protection de tous les liens
parents, mémoire constante, sandbox OS ou garantie d'immutabilité après lecture.

## Qualification

36 nouveaux cas (54 tests du lanceur au total) : suites valides, compteurs réels,
statuts cohérents mais non verts, totaux contradictoires, nombres non ASCII/négatifs,
compensation inter-suites, structures/statuts cachés ou multiples, taille, DTD,
UTF-16, profondeur, symlink, FIFO et bilan global refusé malgré codes processus zéro.
Les processus et XML synthétiques de ces tests qualifient le contrôleur, pas un
résultat OCR simulé. Le lanceur a ensuite été exécuté sur sa sélection réelle et
le lecteur sur le JUnit complet contenant effectivement les 18 échecs.
