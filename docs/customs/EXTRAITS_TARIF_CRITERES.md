# Positions et extraits des critères tarifaires — lot 47

Complément additif à la [recherche multicritère](RECHERCHE_TARIF_CRITERES.md).
Même service, même CLI, route et audit. Aucun nouveau droit, recherche distante,
fichier de production ou mécanisme de validation. Ce contrat concerne les libellés
reçus, **pas une preuve PDF ou un attribut produit certifié**.

## Restitution

Chaque résultat contient désormais :

- `positions_par_critere[critere][terme_normalise]` : liste des libellés FR/AR déjà
  identifiés dans `correspondances_par_critere`, chacun avec `champ_texte`,
  `unite_decalage`, `correspondance_debut`, `correspondance_fin`.
- Toutes les positions sont en **points de code Unicode Python du libellé original**,
  début inclus, fin exclusive. Ni octets UTF-8 ni unités UTF-16 JavaScript, ni
  coordonnées PDF ou numéros de page. Chaque terme a une première occurrence par
  libellé correspondant ; aucune autre occurrence comptée ou localisée.
- `extraits_correspondants` : jusqu'à **16 extraits par ligne**, au plus 384 points
  de code chacun, avec critère, terme, champ, fragment original, offset de fragment,
  taille du texte, bornes du match et indicateurs de troncature/visibilité.
- `total_extraits_disponibles` compte les triplets critère/terme/libellé ayant une
  première occurrence (maximum 5 × 16 × 2 = 160), **pas les occurrences dans le texte**.
  `extraits_tronques` indique si seuls les 16 premiers triplets ont un extrait.
  Toutes leurs positions restent présentes, y compris au-delà de ces 16 extraits.
- Ordre des critères et termes saisis, puis ordre des noms de champs de la preuve
  préexistante. Pas réordonnancement de pertinence. Un terme répété dans plusieurs
  critères reste traçable sous chacun ; les positions techniques sont partagées.

Rapport : `occurrences_denombrees:false`, `maximum_extraits_par_ligne:16`,
`politique_localisation:premiere_occurrence_par_critere_terme_et_libelle`.
Une recherche par préfixe seul conserve ses résultats et donne des positions et
extraits vides, sans inventer de terme ni d'attribut technique.

## Projection et limites

Normalisation de comparaison existante conservée. Une seule projection par libellé
localise tous les débuts/fins nécessaires, sans table d'indices de tout le texte.
Les positions sont produites **seulement pour la page de résultats retenue**.
La recherche continue cependant à rejouer tout le lot avant pagination : pas moteur
indexé, mémoire constante, streaming ou qualification de charge nationale.

Les expansions de caractères (`œ`, ligatures, fractions, etc.) peuvent conduire à
une même portion originale pour plusieurs caractères normalisés. Une position
encadre cette portion originale, pas une position de glyphe, de graphème ou une
égalité littérale du terme saisi. Tatweel et marques arabes peuvent allonger le
span au-delà de l'extrait ; `correspondance_entierement_visible:false` est alors
restitué et signalé dans l'interface. Aucun texte reçu n'est corrigé.

Le projecteur est partagé avec les extraits du Code, qui gardent leur contrat
antérieur : un extrait par champ, premier terme demandé trouvé, pas tous les termes.
Ces sorties antérieures sont couvertes par la non-régression.

## Interface et export

Affichage en `blockquote` avec direction automatique, code10, critère, terme,
champ et positions originales. Fragment affiché en texte, jamais HTML ou lien
source suivi. Contrôles du champ/critère demandé, des bornes Unicode, de la taille,
de la visibilité et de l'égalité du fragment à la tranche du libellé reçu. Conversion
UTF-16 → points de code par `Array.from`, réutilisée pour les extraits d'un champ.
Ancien export sans ces nouveaux champs reste consultable ; pas de migration.

Les positions et extraits sont inclus dans les mêmes exports partiels et le
contrôleur structurel hors ligne existant. La limite globale d'export de 10 Mio
reste applicable : **ces bornes d'extraits ne garantissent pas qu'un rapport soit
exportable**, car il contient aussi les libellés complets reçus. Réduire la page si
nécessaire ; aucun texte n'est silencieusement coupé pour contourner cette limite.
Cache de l'interface : `v67-tariff-excerpts`.
