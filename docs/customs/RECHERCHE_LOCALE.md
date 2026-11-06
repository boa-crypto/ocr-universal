# Recherche documentaire locale FR/AR — lot 5

2026-11-06. **Recherche dans un lot contrôlé en quarantaine, pas classement douanier.**

## Commandes

```sh
# Désignations déclarées, français/arabe :
PYTHONPATH=src python -m unocr.cli customs-tariff-search /chemin/lot-tarif --query "équipement"

# Préfixe ASCII : chapitre, position, SH6 ou subdivision, sans compléter un code :
PYTHONPATH=src python -m unocr.cli customs-tariff-search /chemin/lot-tarif --query "010100" --limit 20 --offset 0

# Textes et intitulés déclarés des articles :
PYTHONPATH=src python -m unocr.cli customs-code-search /chemin/lot-code --query "معدات"

# Numéro exact dans le document transcrit, versions distinctes :
PYTHONPATH=src python -m unocr.cli customs-code-search /chemin/lot-code --article "5 bis"

# Filtres complémentaires (valeurs à fournir selon le lot réel) :
PYTHONPATH=src python -m unocr.cli customs-code-search /chemin/lot-code --source ID_DOCUMENT --nature modificative --limit 20
```

Les commandes ne lisent qu’un lot déjà préparé. Les termes et préfixes ci-dessus
illustrent le fonctionnement du CLI ; ils n’attestent pas l’existence ou le
classement d’une marchandise dans la nomenclature nationale. Les fichiers de lot
réels doivent être fournis : aucun corpus d’exemple n’est créé ou substitué.

Code 0 = recherche techniquement effectuée, y compris zéro correspondance ; code
2 = refus. Les erreurs opérationnelles sont renvoyées en JSON ; les erreurs de
syntaxe d’arguments restent celles d’argparse (stderr). Pas de nouveau serveur,
endpoint HTTP, store, index persistant ou activation de publication.

## Sûreté et périmètre

Les fonctions centrales `customs_reference.search.rechercher_tarif` et
`rechercher_code` utilisent les lecteurs/rejeux des lots 2 et 4. **Tout le lot**
est contrôlé avant recherche, même si une seule ligne est demandée ou si le
résultat sera vide. Un lot corrompu ou incomplet provoque un refus intégral,
sans page partielle présentée comme valide. Les archives Code et tarifaires
ne sont pas interchangeables.

Le code n’écrit pas dans les lots ni les magasins métier et n’accède à aucune
source distante. L’intégrité locale n’établit ni l’origine officielle, ni
l’exactitude transcription/PDF, ni l’applicabilité. Le résultat est toujours
marqué `publication_active=false`, `validation_juridique=non_validee`,
`classement_douanier_valide=false`, `completude_reglementaire=non_etablie`, avec
validation humaine requise. Ces recherches ne sont reliées à aucun calcul fiscal.

## Comparaison textuelle, pas interprétation

Sur une **copie de comparaison uniquement** : décomposition Unicode NFKD,
casefold, suppression des marques combinantes et du tatweel arabe, expansion
`œ → oe` et `æ → ae`, puis séparation des caractères non alphanumériques.
Les textes affichés et archivés sont conservés tels que reçus. Les règles Unicode
peuvent rapprocher des graphies différentes ; cela ne prouve aucune équivalence
juridique ou technique. Pas de remplacement arbitraire des lettres arabes.

Tous les termes normalisés distincts doivent apparaître comme **sous-chaînes**
dans au moins un champ de la même ligne/version. L’ordre des termes est libre ;
un terme français et un terme arabe peuvent correspondre à deux champs de la
même ligne. Ce ne sont ni une recherche de phrase exacte, ni une lemmatisation,
ni un raisonnement SH. Les sous-chaînes peuvent produire des faux positifs.
`champs_correspondants` explique quels champs contiennent chaque terme ; ce
n’est pas une preuve réglementaire ou un score de confiance.

- Tarif : uniquement `designation_officielle_fr` et `designation_officielle_ar`.
  Les libellés de parents, mesures, restrictions et taux ne sont pas indexés.
  Les montants/taxes ne sont pas calculés ou proposés par la recherche.
- Code : `intitule`, `texte_integral`, `texte_francais`, `texte_arabe`.
  Les notes explicitement non officielles et les métadonnées de source ne sont
  pas recherchées comme du texte légal. Le numéro se filtre via `--article`.
- Pas de synonymes inventés ou dictionnaire réglementaire fourni, de traduction,
  recherche vectorielle, IA, classification, correspondance matière/fonction
  inférée ou choix d’une version applicable. Un texte déclaré abrogé n’est pas
  supprimé automatiquement des résultats : le statut reste une déclaration.

## Codes et filtres exacts

Une requête tarifaire composée uniquement de chiffres décimaux est traitée comme
un préfixe de **1 à 10 chiffres ASCII** du code 10 déjà stocké. Les chiffres arabes
indicatifs ou pleine chasse et les valeurs trop longues sont refusés dans ce mode.
Aucun cast numérique, zfill, pseudo-clé de contrôle ou validation nationale n’est
introduit. Un préfixe SH6 retrouve des lignes existantes, pas un code nouvellement
construit. Une requête mixte texte/chiffres reste une recherche de désignation,
jamais une correction implicite de code.

Pour le Code, `--article`, `--source` et `--nature` sont des filtres cumulatifs.
Le numéro et l’ID de source sont comparés littéralement, sans trim, normalisation,
traduction ni rapprochement par similarité. `5 bis`, `5 BIS` et `5` sont distincts.
Les natures permises sont `originale`, `modificative`, `consolidee_provisoire`.
Les versions trouvées restent séparées, même si leur numéro est identique.
Le numéro de la disposition modificative peut différer de sa cible dans le Code.

Au moins une requête textuelle ou un filtre Code explicite est requis ; une
requête de ponctuation seule n’est pas interprétée comme « tout afficher ».
Aucun filtre de date, de validité ou d’expiration ne choisit silencieusement une
version juridique : un tel moteur n’est pas livré.

## Pagination et restitution

- Requête : 256 caractères maximum, 16 termes distincts maximum.
- `--limit` : entier 1 à 100, 20 par défaut ; `--offset` : entier 0 à 1 000 000.
- Tri déterministe : code 10 ASCII croissant pour le tarif ; ID déclaré croissant
  pour les articles. Ce tri n’est ni un rang de pertinence, ni une chronologie.
- `total_correspondances`, `decalage_suivant` et `resultats` portent seulement sur
  les correspondances dans le lot sélectionné ; zéro ne prouve pas absence de droit.
- Le tarif restitue la ligne déclarée et sa référence ; les mesures fiscales
  séparées ne sont pas incluses. Les champs fiscaux null restent inconnus.
- Le Code restitue identité/version/nature, référence, statut et dates **déclarés**,
  avec des aperçus initiaux de 512 caractères par champ de texte au maximum.
  Ces aperçus ne sont pas centrés sur le mot trouvé : un terme peut être hors de
  l’aperçu. `tronque` le signale ; le texte complet reste dans l’archive contrôlée.
- Les empreintes et documents/sources déclarés relient le résultat à son lot.
  Aucun résultat n’est présenté comme une suggestion tarifaire officielle.

Le lecteur vérifie et parcourt le lot à chaque appel. Pas de benchmark sur un
fichier national réel, ni de garantie globale de mémoire, de temps ou de taille
de réponse ; les bornes des lecteurs de lots restent applicables.
La future API/admin devra réutiliser ces fonctions sous permissions explicites,
sans exposition libre des chemins de fichiers ni recours au RBAC legacy permissif.
