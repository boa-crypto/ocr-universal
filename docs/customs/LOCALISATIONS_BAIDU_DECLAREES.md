# Localisations Baidu fournies : validation bornée — lot 69

> Complément au lot 70 : [pages sans sortie incluses dans moyennes et revue](PAGES_SANS_SORTIE_DANS_QUALITE.md). La limite `pages_low_confidence` décrite ci-dessous est historique au lot 69 et désormais corrigée pour ce périmètre.

7 novembre 2026. Complète les lots 65–68 ; pas de changement d'endpoint,
d'option, d'autorisation ou de clé fournisseur.

## Présence et absence sont différentes

Quand la clé `location` est présente dans un élément `words_result`, sa valeur
doit être un objet contenant `left`, `top`, `width`, `height`. `null`, `false`,
zéro, chaîne vide, liste ou objet vide ne sont plus assimilés à une absence.
Chaque champ requis doit exister : aucune coordonnée manquante n'est inventée à zéro.

Les champs supplémentaires de cet objet sont ignorés, jamais persistés par cette
projection. Seules les quatre valeurs géométriques validées alimentent la boîte.

**Quand la clé `location` est réellement absente**, la boîte pleine image
préexistante est conservée pour compatibilité avec l'endpoint `accurate_basic`,
sans lui attribuer une précision ou une origine mesurée. Cette approximation
n'est pas supprimée par ce lot. Aucun changement vers un endpoint de localisation
ou ajout d'option fournisseur non qualifiée n'est effectué.

## Contrôles des valeurs fournies

- Valeur numérique JSON exacte `int`/`float` Python : ni booléen, texte, liste,
  objet ou valeur nulle ; flottants finis uniquement.
- Dimensions de l'image traitée entières strictement positives, au plus `2**31-1`
  par axe ; contrôle de contexte, pas test d'allocation de telles images.
- Origines non négatives ; largeurs/hauteurs strictement positives et bornées.
  Les bornes sont vérifiées avant conversion en flottant pour éviter le
  débordement de conversion d'entiers démesurés.
- Extrémités dans l'image ; largeur/hauteur effectives et aire calculée strictement
  positives, y compris après arrondi flottant. Une somme arrondie à l'origine ou
  une aire sous-fluente n'est pas acceptée comme boîte utile.
- Pas de clipping, permutation des extrémités, correction d'orientation ou de
  coordonnées, ni promotion d'un score liée à ces contrôles.

Ces bornes portent sur **l'image encodée et envoyée au moteur**, éventuellement
prétraitée, pas sur une page PDF originale. Aucune reprojection vers les
coordonnées d'origine, correction de rotation ou attestation de localisation réelle
n'est ajoutée. Le modèle général `BBox` et les autres moteurs restent inchangés.

## Refus sans réponse partielle

Une localisation fournie invalide fait échouer toute cette sortie Baidu, même si
un élément précédent était valide. Retour : texte vide, aucun mot, aucune
provenance partielle dans `raw`, score de sortie conservateur par défaut, et erreur
constante `Baidu : localisation invalide`. Aucun texte, coordonnée, jeton ou
exception distante n'est interpolé dans cette erreur ou journalisé par ce chemin.
Le pipeline garde un run échoué ; les autres sorties éventuelles restent gérées
par le pipeline préexistant, sans nouvel appel distant de secours.

Dans le cas testé où aucune sortie utilisable n'existe et la page n'est pas vide,
le rapport de qualité expose `OCR_FAILED` et une moyenne globale nulle. **La liste
existante `pages_low_confidence` ne recense pas cette page sans mots/texte** :
ce défaut de couverture n'est pas corrigé ici. Une moyenne sur un document mixte
peut encore exclure les pages échouées ; ce lot ne certifie pas cette agrégation
ni un verrou de validation humaine fondé uniquement sur cette liste.

## Compatibilité et limites

Une localisation numérique valide est conservée, y compris fractions et bords
exacts. Les scores déclarés/absents/invalides et leur provenance des lots 66–68
restent inchangés pour les sorties réussies. Aucun ancien résultat ou export
n'est migré. L'absence de localisation reste approximative et non distinguée par
un nouveau champ de provenance géométrique persisté.

Tests sur réponses synthétiques locales : pas appel Baidu réel, précision FR/AR,
coordonnées fournisseur mesurées, charge, corpus officiel ou qualification
scientifique. Les limites OAuth query, délais d'inactivité et transport du lot 65
restent présentes. Voir [rapport et recette](RAPPORT_LOT69.md).
