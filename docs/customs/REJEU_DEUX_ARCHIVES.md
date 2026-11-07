# Rejeu de comparaisons à deux archives explicites — lot 54

Contrôle local distinct du [rejeu d'une archive](REJEU_EXPORTS_TYPES.md). Les
chemins ne viennent jamais du JSON : deux dossiers, identités et types sont
fournis par l'opérateur, en conservant leur ordre.

```sh
unocr customs-review-export-replay-pair rapport.json --before-lot DOSSIER_A --before-id ID_A --before-type tarif --after-lot DOSSIER_B --after-id ID_B --after-type tarif
```

Service `verifier_rejeu_paire(fichier, avant, apres, avant_id, apres_id,
type_avant, type_apres)`. Types CLI obligatoires, aucune autodécouverte de lecteur
ou substitution d'archive depuis un paramètre. Pas nouvelle API, UI ou écriture.

## Matrice fermée

Routes sous `/api/v1/customs-review/` :

| Route | Types ordonnés avant/après | Paramètres |
|---|---|---|
| `diff` | code/code ou tarif/tarif | `avant`, `apres` requis |
| `article-diff` | code/code | `avant`, `apres`, `avant_id`, `apres_id` requis ; `field`, `limit`, `offset_avant`, `offset_apres` |
| `tariff-compare` | tarif/tarif | `avant`, `apres`, `code10` requis ; `before_limit`, `before_offset`, `after_limit`, `after_offset` |
| `tariff-measures` | tarif/mesures | `tarif`, `mesures`, `code10` requis ; `tariff_limit`, `tariff_offset`, `measures_limit`, `measures_offset` |

Les deux IDs de lots de la requête doivent correspondre exactement aux deux IDs
fournis dans le même ordre. Les IDs d'articles ne sont pas des IDs de lots.
Pour tarif/mesures, avant est la nomenclature, après le lot autonome : la requête
utilise `tarif`/`mesures`, pas une chronologie. Inversion de rôles refusée.

Même identité utilisable des deux côtés uniquement si types et arguments `Path`
sont identiques. Deux écritures différentes du chemin, même si elles pourraient
résoudre vers le même dossier, ne sont pas réconciliées automatiquement. Deux IDs
distincts peuvent désigner des copies cohérentes ; registre non authentifié.

Neuf paramètres au plus, inconnus/doublons après décodage/encodages invalides
refusés. Pagination décimale ASCII stricte ; deux offsets Unicode d'article et
deux paginations des mesures indépendantes. Mêmes validations métier et valeurs
par défaut que les services API. Code10 textuel exact, pas conversion ou zfill.

## Comparaison et provenance

Chaque service rejoue les deux archives dans l'ordre fourni. Le résultat complet
est comparé, y compris `lots_exacts` lorsque la route API l'ajoute, les rôles,
mesures, sources, compteurs, filtres, fragments, différences et drapeaux. Le diff
complet de lots, qui n'ajoute pas `lots_exacts` dans l'API, reste inchangé.

Comparaison canonique commune avec le rejeu simple : ordre des clés ignoré,
listes et types JSON conservés. Les deux manifestes exportés sont comparés à la
paire **ordonnée** des manifestes locaux ; aucun ensemble non ordonné ne remplace
cette paire. Une copie cohérente ou des fichiers recomposés peuvent satisfaire ce
contrôle, sans attester origine ou identité du registre.

Constat `rejeu_local_export_deux_archives`, champs
`manifestes_archives_fournies` et `types_lots_explicites` par rôle avant/après,
`archives_fournies_coherentes_au_rejeu`, `manifest_export_correspond` et
`rapport_identique`. Pas de champ singulier de manifeste pour une paire.
Ni texte de rapport, ni requête, ni contenu des écarts recopiés. Codes : **0**
identique, **1** différent, **2** refus. Erreur d'une archive : refus générique,
pas un rejeu partiel présenté comme exploitable.

## Limites inchangées

Avant/après n'exprime ni succession juridique ni choix de version applicable.
Juxtaposition tarif/mesures ≠ rattachement, dédoublonnage, fusion fiscale ou taux
applicable. Écart de texte ≠ consolidation ou preuve de modification juridique.
Authenticité, signature, registre et audit serveur restent non attestés.

Pas extraction native PDF dans ce contrôleur : lecture/hachage des fichiers PDF
Code possibles au contrôle d'archive, pas worker de page ou OCR. Le rejeu natif
PDF à une archive conserve son option séparée [--allow-pdf](REJEU_EXPORTS_PDF.md).

Chargement/rejeu complet des deux lots et comparaison en mémoire, pas mémoire
constante, streaming, qualification de charge nationale ou transaction multi-dossiers.
Aucune garantie contre modification concurrente après lecture, aucune publication.
L'interface et le cache v69 sont inchangés.

## Complément lot 55

[Empreintes attendues](EMPREINTES_ATTENDUES_REJEU.md) facultatives pour export et
chaque manifeste, fournies séparément. Leur égalité ne certifie pas leur origine.
