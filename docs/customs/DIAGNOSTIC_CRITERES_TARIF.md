# Diagnostic explicite des critères tarifaires — lot 49

Complément de `tarif_criteres_documentaires` ; même API, CLI, droits, audit et export.
Aucune IA, proposition de classement, cause métier ou décision juridique créée.

## Compteurs et périmètre

`diagnostic_recherche` décrit toutes les lignes du lot **après filtre de préfixe
éventuel, avant pagination**, selon le mode littéral choisi au lot 48 :

- `lignes_dans_prefixe` : nombre de lignes dans ce périmètre. Sans préfixe, toutes
  les lignes du lot ; pas un effectif national attendu.
- `par_critere[critere].lignes_par_terme[terme]` : lignes contenant le terme dans
  au moins un libellé FR/AR. Chaque ligne comptée une seule fois, même si le terme
  est répété ou présent dans les deux langues. Pas nombre d'occurrences.
- `par_critere[critere].lignes_tous_termes` : lignes contenant **tous les termes de
  ce critère** dans leurs libellés. Plusieurs termes répartis sur différentes
  lignes ne satisfont pas un critère.
- `criteres_sans_ligne_complete` : critères dont le compteur précédent vaut zéro.
  Ce ne sont **pas des attributs techniques manquants du produit**. Cette liste
  peut être vide malgré une recherche sans résultat.
- `lignes_tous_criteres` : lignes réunissant tous les termes de tous les critères,
  identique à `total_correspondances`. Ne pas additionner les compteurs séparés.

Exemple technique : désignation « équipement » trouvée sur deux lignes, fonction
« pompe » sur une autre. Chacun a un compteur positif, mais zéro ligne commune :
aucune correspondance retenue et aucun classement déduit. Ces termes ne deviennent
pas des attributs certifiés grâce à leur étiquette de critère.

## Constats limités

`constat` vaut :

1. `aucune_ligne_dans_prefixe` : zéro ligne dans le périmètre (qui peut être le lot
   entier sans préfixe). Pas déclaration d'inexistence nationale du code.
2. `aucune_conjonction_sur_meme_ligne` : des lignes sont présentes mais aucune ne
   réunit tous les termes de tous les critères.
3. `page_hors_resultats` : des correspondances existent, mais l'offset ne restitue
   aucune ligne. À distinguer d'une recherche sans correspondance.
4. `correspondances_documentaires` : page contenant des correspondances non validées.

Les trois premiers constats sont hiérarchisés dans cet ordre. Les compteurs sont
stables entre pages pour les mêmes filtres ; le constat de page hors résultats
peut changer avec l'offset. Préfixe seul : `par_critere` et liste des critères vides,
aucun critère inventé. Zéro résultat reste HTTP 200 / CLI 0 avec rapport explicite.

`absence_de_droit_deduite` et `attributs_manquants_deduits` restent **false**. Le
service ne peut distinguer une requête inadéquate, une variante lexicale, une
transcription incomplète ou un vrai manque documentaire à partir de ces comptes.
Pas suggestion automatique de terme, synonyme, code, taux ou assouplissement du ET.

## Affichage et conservation

L'interface affiche le constat, les compteurs par critère et le rappel de
non-déduction. Elle refuse les diagnostics à périmètre/drapeaux/constat inconnus,
compteurs totaux incohérents ou constat incompatible avec les résultats ; les
compteurs affichés sont bornés au nombre de lignes du périmètre. Le contenu brut
du rapport reste un affichage textuel, pas une validation du JSON par l'interface.

L'export partiel conserve le diagnostic. Ancien rapport sans diagnostic : pas de
migration requise et aucun diagnostic inventé côté client. Changement de lot,
nouvelle lecture ou échec d'audit retirent l'ancien affichage des résultats.
Cache `v69-criteria-diagnostics`.

Les compteurs sont accumulés pendant le parcours déjà nécessaire ; pas second
rejeu du lot. Les limites existantes restent : archive complète chargée/rejouée,
pas index, streaming, mémoire constante ou qualification de charge nationale.
