# Recherche documentaire des mesures tarifaires déclarées — lot 32

Recherche distincte de celle des désignations. Seulement `mesure.description`,
normalisée comme la recherche existante FR/AR : casse/accents/diacritiques arabes,
tatweel et ligatures usuelles. Tous les termes doivent être des sous-chaînes de
la description ; pas de traduction, synonymes, IA, score, expression régulière
utilisateur ou recherche de taux. Le texte original n'est pas modifié.

## Contrats

```text
customs-tariff-measure-search DOSSIER_LOT --query TEXTE [--code CODE10] [--type restriction] [--limit 20] [--offset 0]
GET /api/v1/customs-review/lots/{lot_id}/measure-search?q=TEXTE&code10=CODE10&measure_type=restriction&limit=20&offset=0
```

Les filtres sont facultatifs : `code10` chaîne exacte de dix chiffres ASCII,
sans préfixe/conversion/extension SH6 ; `measure_type` parmi `droit`, `tva`,
`autre_taxe`, `restriction`, `autorisation`, `regime`. Requête vide autorisée
seulement avec au moins un filtre. Une requête non vide doit contenir un terme
alphanumérique ; maximum 256 points de code et 16 termes. Les substituts Unicode
isolés et contrôles interdits sont refusés. Limite entière 1–100, décalage
0–1000000, booléens refusés par le service. Paramètres vérifiés avant chargement
du lot par le service ; la route contrôle aussi registre/droits/empreintes.

Rapport `type_recherche=mesures_tarifaires_documentaires`, résultats en ordre
code10 ASCII puis ID de mesure Unicode croissants (pas pertinence ou date).
Chaque résultat contient :

- `mesure_declaree` complète : type, description, référence, taux/unité et période
  reçus ; Decimal sérialisé en chaîne exacte sans arrondi ; null ≠ zéro ;
- `ligne_declaree` : ID, code exact, désignations et référence pour contexte ;
- `champs_correspondants` : termes normalisés → champ `description`.

`source_declaree` et `archive` restituent source et provenance du lot ; les
compteurs décrivent ce lot seulement. Filtres cumulés avec la requête. Les
localisateurs, IDs, désignations et taux ne sont pas des champs recherchés.

Même revue administrative autorisée, épinglage/rejeu/recontrôle d'empreinte,
audit obligatoire de succès `recherche_mesures`, réponse `no-store`. Refus d'un
lot Code ou des paramètres invalides : 422 ; panne audit : 503 sans résultat.
Export partiel relu/audité, enveloppe 1 et vérificateur hors ligne mis à jour.
L'interface propose la suite et la fiche du code source ; les anciennes actions
sont invalidées après navigation/compte/changement du résultat.

## Limites impératives

- Résultat documentaire non validé, pas règle applicable, exonération ou autorisation
  d'importer. Une description contenant « autorisation » ne requalifie pas le type.
- Absence de mesure/résultat ≠ absence de taxe ou restriction nationale.
- Aucune sélection à date, fusion fiscale, identité inter-sources ou calcul.
- Les mesures restent dans le contrat TariffBatch ; pas d'import fiscal autonome.
- Chargement/rejeu/sort du lot entier avant pagination : pas mémoire constante,
  index national, quota global ou qualification de charge.
- Enveloppe export inchangée ; anciens contrôleurs à whitelist stricte peuvent
  refuser la nouvelle route. Contrôle structurel hors ligne ≠ authenticité.
- Tests sur fixtures explicitement NON OFFICIELLES, sans ajout de données actives.
