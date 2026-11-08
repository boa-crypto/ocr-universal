# Horodatage de classification et concordance d'acteur — lot 88

Route : `GET /api/jobs/{job_id}/classification`. Complète les lots78/86/87.

## Politique ciblée

Le résultat reste la référence ; l'audit ne peut qu'ajouter un `ts` déclaratif.
La dernière candidate JSON objet, événement et job exacts reste sélectionnée.
Les cinq champs catégorie/confiance/version/revue/manual doivent toujours
concorder comme au lot78.

**Si cette trace possède la clé `acteur`**, l'ajout de son horodatage exige aussi :
- `manual` exactement booléen `True` dans trace et décision ;
- acteur chaîne non blanche, égal exactement au `corrected_by` stocké.

Une clé `acteur` null/vide/inexploitable n'est pas une absence de clé. Pas
normalisation de casse, espaces ou Unicode lors de l'égalité. Une divergence
ou un acteur stocké absent/null empêche d'ajouter le timestamp de cette trace.
**Pas remontée à une ancienne trace compatible.** Sans décision stockée, le
fallback cinq champs reste retourné mais ne permet pas d'inférer l'acteur pour
une trace attribuée, donc pas son timestamp.

**Trace historique sans clé acteur** : politique cinq champs inchangée, sans
identité inventée ou statut de confiance nouveau. Cette compatibilité reste
moins stricte. La règle booléenne stricte ne refond pas tous les types legacy.
Le timestamp déjà présent dans la décision stockée n'est pas réparé/effacé ;
la règle empêche l'ajout ou l'écrasement depuis une trace incompatible.

## Recette

35 nouveaux cas : 11 acteurs divergents/inexploitables, trois noms concordants
(dont FR/AR), trois traces sans acteur legacy, une dernière trace conflictuelle,
quatre valeurs manual non booléen True, trois fallbacks sans décision, deux
acteurs stockés absents/null, trois gardes avant lecture du journal, quatre
chaînes réelles PATCH87 → GET avec comptes différents, un timestamp déjà stocké.
Stores/jobs/audits temporaires réels ; traces synthétiques explicites pour les
cas négatifs, empreintes inchangées sur GET, pas fournisseur OCR ou navigateur.

Contre-épreuve : seul ancien GET réinjecté en mémoire, fixtures et autres
handlers conservés ; checkout/aperçu non remplacés.
[Rapport](RAPPORT_LOT88.md), [recette](RECETTE_LOT88.json).

## Limites

Concordance déclarative, **pas authenticité du journal, identité de révision,
signature ou identité civile**. Deux actes de mêmes catégorie/acteur/autres
champs peuvent encore être confondus. Pas signature, compteur de révision,
comparaison complète des preuves/libellés, validation universelle de `ts` ou
des types, ni purge d'un `ts` déjà stocké. Lecture entière/préfiltre littéral
du journal et sélection sans verrou transactionnel global inchangés.

La trace attribuée automatique n'est pas un nouveau cas accepté : la route
automatique87 n'ajoute pas d'acteur, et la nouvelle règle cible le manuel.
Pas migration/attribution rétroactive du legacy. Modèle autoritaire, droits,
score manuel1, exports en cache, autres opérations dossiers à acteur client,
limites de révision processus/ABA et audit postcommit inchangés.

Aperçu backend76 maintenu : code77–88 poussé/testé mais non chargé avant
redémarrage maîtrisé pour préserver les traitements. RBAC non activé
implicitement ; mission réglementaire toujours partielle.
