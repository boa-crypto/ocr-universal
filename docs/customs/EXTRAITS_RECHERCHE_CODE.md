# Extraits contextualisés de recherche Code — lot 33

La recherche centrale `customs-code-search` et `GET /api/v1/customs-review/lots/{id}/search`
conservent leurs paramètres, résultats et aperçus initiaux. Complément additif
`extraits_correspondants` sur chaque résultat : au plus un extrait par champ,
dans l'ordre `intitule`, `texte_integral`, `texte_francais`, `texte_arabe`.

## Sélection et positions

Pour chaque champ, sélection du **premier terme normalisé de la requête présent**,
puis de sa première occurrence. Ce n'est ni le terme le plus précoce dans le texte,
ni un classement par pertinence, ni un relevé exhaustif des occurrences.

La position normalisée est projetée sur les points de code du texte original :
accents, casse, marques arabes/tatweel, ligatures et décompositions de compatibilité
servent à la comparaison seulement. Fragment original exact, sans normalisation,
correction ou traduction. Jusqu'à 40 points de code avant le début, puis jusqu'à
384 points de code au total. Une correspondance exceptionnellement étendue par
les caractères ignorés peut déborder du fragment ; cela est explicitement signalé.

Chaque extrait contient `champ_texte`, `terme_normalise`, `decalage`, `fragment`,
`total_caracteres`, `correspondance_debut`, `correspondance_fin` (borne exclusive),
`correspondance_entierement_visible`, `tronque_debut`, `tronque_fin` et
`unite_decalage=points_de_code_unicode_python`. Ce ne sont pas des positions en
UTF-16, octets, mots ou graphèmes. Une expansion peut faire correspondre plusieurs
lettres normalisées à un seul caractère original.

Requête vide avec filtres : aucun extrait. Champ absent ou sans terme : aucun
extrait pour ce champ. Les termes peuvent rester répartis entre plusieurs champs,
conformément à la recherche existante. Pas de repli vers une langue absente.

## Lecture et garanties

L'interface affiche les fragments en texte sûr `dir=auto`, vérifie les bornes,
refuse champs/termes/unités incohérents et ouvre le même ID de version dans le
même lot, avec champ, limite et décalage exacts via la lecture existante. Le titre
est affiché mais ne crée pas de bouton de lecture d'un champ interdit. Les actions
restent inertes après remplacement/navigation/compte ; panne audit efface tout.

Même autorisation, épinglage, rejeu, audit obligatoire et `no-store`. Export de la
recherche relu/audité et contrôle hors ligne existants ; pas de nouvelle route ou
version d'enveloppe. Les aperçus initiaux de 512 caractères sont conservés.

## Limites

Extraits de transcriptions déclarées NON VALIDÉES : aucune preuve de fidélité PDF,
authenticité, traduction ou droit applicable. Ni OCR ni validation humaine ajoutés.
Pas de surlignage d'une correspondance normalisée comme si elle était littérale.
Pas de dénombrement d'occurrences ou de recherche sémantique/IA.

Le complément travaille uniquement sur les résultats de la page mais normalise
les champs entiers. La projection s'arrête au terme sélectionné, sans table de
positions du texte entier ; cela ne rend pas le chargement/rejeu du lot ou la
recherche à mémoire/temps constants. Pas de benchmark national ni recette
visuelle/accessibilité en navigateur réel.
