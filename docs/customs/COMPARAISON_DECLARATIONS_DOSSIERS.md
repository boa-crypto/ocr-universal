# Comparaison des déclarations et pistes d'un dossier

## Ce que fait cette vue

`GET /api/v1/customs-review/lots/{lot}/assessments/{id}/comparison`
avec `?version=N` facultatif retourne une juxtaposition en lecture seule d'une
version enregistrée :

- cinq critères du produit déclaré ;
- pièces associées, leur auteur, localisateur et empreinte du texte ;
- déclarations d'attributs et citations exactes sélectionnées par l'opérateur ;
- égalité exacte de chaque valeur déclarée avec la valeur du produit, ou null
  si celle-ci n'est pas renseignée ;
- valeurs textuellement distinctes entre les déclarations d'un même critère ;
- candidats littéraux du snapshot de cette version, références, termes retrouvés
  ou non retrouvés et extraits ; au maximum les20 candidats déjà enregistrés ;
- questions à examiner : champ produit manquant, absence de citation déclarée,
  valeurs textuellement différentes.

Aucune normalisation n'est appliquée à l'égalité des valeurs déclarées : casse,
espaces, accents et graphies arabes différentes peuvent donc signaler un écart.
Ce n'est **pas** une contradiction technique établie, une traduction ou une
interprétation de la négation. Deux valeurs identiques ne constituent pas non
plus une expertise ou une corroboration indépendante.

La présence d'une pièce sans citation n'est pas traitée comme preuve d'attribut.
Une citation n'alimente jamais automatiquement le produit. Les déclarations
n'élargissent, ne trient et ne retiennent pas les candidats. La matrice des
correspondances candidates provient de la recherche littérale du **produit**
enregistré, non d'une recherche des citations dans le tarif.

## Provenance et contrôles

Le rapport identifie dossier, version, lot, manifeste et SHA256 canonique de
l'état enregistré (sans le sommaire `historique` ajouté par certaines lectures).
Cette empreinte n'est ni signature ni preuve d'authenticité. Le calcul Python
interne attend un dossier déjà vérifié ; ce n'est pas un point d'entrée de
validation d'un JSON arbitraire.

L'API réutilise les contrôles de la revue : compte nominatif et rôle autorisé,
allowlist des réviseurs, lot tarifaire épinglé, relecture complète de l'archive,
intégrité état/version/pièces, source cohérente et audit obligatoire. Les sorties
d'audit de versions en attente sont réconciliées avant réponse. Une panne peut
donc retourner503, sans création de nouvelle version par cette lecture.

Absence du dossier/version404 ; version hors1–100 ou invalide422 ; archive ou
état altéré refusé. API same-origin/no-store, pas de mise en cache des réponses
par le service worker. Pas de liste globale ni élargissement des habilitations.

## Interface

Après chargement, cliquer explicitement sur **Comparer les déclarations de la
version enregistrée**. L'interface demande cette version précise, pas une version
courante susceptible d'avoir changé entre-temps. Le rapport indique clairement
qu'il ne compare **pas le brouillon local non enregistré**.

La consultation d'une comparaison historique ne réactive pas les écritures.
Une modification concurrente reste protégée par le CAS lors d'une révision.
Les valeurs reçues sont affichées comme texte, sans HTML exécutable ; les réponses
prétendant certifier un attribut ou calculer un taux sont refusées. Le contexte
lot/identifiant/compte/route et les réponses tardives restent contrôlés.

## Limites

Vue documentaire, pas comparaison technique sémantique discriminante. Pas IA,
ontologie, synonymes sourcés, décision RGI, preuve d'équivalence de produits,
classement ou taux applicable. Les questions ne sont pas des règles juridiques
et ne modifient pas les conditions de proposition humaine.

Les champs `attributs_techniques_certifies`, `contradiction_semantique_etablie`,
`classement_ia_effectue`, `candidat_retenu_automatiquement`, `taux_calcules` et
`publication_active` restent false. L'archive et les pièces restent non validées.
Les limites de conservation, confidentialité, sauvegarde et outbox96 demeurent.
