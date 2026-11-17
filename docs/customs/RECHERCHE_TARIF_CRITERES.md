# Recherche tarifaire multicritère explicite — lot 46

Recherche documentaire dans **les libellés FR/AR reçus d'un seul lot tarifaire**,
jamais dans un référentiel national supposé complet ou des attributs produits
certifiés. Aucun LLM, synonymes implicites, traduction, RGI ou score de confiance.

## Contrat

```sh
unocr customs-tariff-criteria LOT --designation équipement --matiere acier --fonction pompage --code-prefix 84 --limit 20 --offset 0
```

Exemple de termes de requête, pas exemple de classement officiel.

API autorisée :
`GET /api/v1/customs-review/lots/ID/tariff-criteria?designation=...&matiere=...&fonction=...&usage=...&caracteristiques=...&code_prefix=...&limit=20&offset=0`.

- Cinq critères indépendants et facultatifs : `designation`, `matiere`, `fonction`,
  `usage`, `caracteristiques`. Au moins un critère ou un préfixe explicite requis.
- Un critère fourni doit être non blanc, 256 caractères maximum, 16 termes au plus,
  sans contrôle interdit ni surrogate. Même normalisation que la recherche existante :
  casse, accents, marques arabes et tatweel pour comparaison seulement. Maximum
  cinq fois seize termes ; aucun champ ou code source corrigé.
- `code_prefix` : 1 à 10 chiffres **ASCII** exacts ; pas de notation scientifique,
  conversion numérique, espaces ou zfill. Peut être utilisé seul.
- Limite entière 1–100, offset entier 0–1 000 000. Validation du service avant lecture
  de l'archive ; contrôle central d'autorisation/épingle en amont inchangé.
- Tous les critères sont requis simultanément (**ET**). Pour chaque critère, tous
  ses termes doivent apparaître comme sous-chaînes dans au moins un des deux
  libellés de **la même ligne**. FR/AR peuvent contribuer à la même ligne, jamais
  deux lignes différentes réunies artificiellement. Pas de traduction : « pompe »
  ne recherche pas implicitement « مضخة » sur une autre ligne.
- Ne cherche ni taxes, mesures autonomes/natives, dates, notes ou unités. Le mot
  saisi sous « matière » n'est pas extrait comme une propriété matière : ce n'est
  qu'une étiquette explicite de requête dans les désignations.

## Preuves, pagination et interface

Rapport `tarif_criteres_documentaires`, source et provenance du lot, filtres exacts,
termes normalisés par critère, total et pagination. Chaque résultat conserve la
ligne reçue (code10, libellés, référence) et `correspondances_par_critere` : pour
chaque terme, les noms des libellés correspondants. Pas preuve PDF ni vérification
juridique. Ordre : code10 croissant ; aucun classement de pertinence ou de confiance.

`attributs_techniques_certifies`, `classement_ia_effectue`, `taux_calcules` et
`classement_douanier_valide` restent false. Une absence de résultat signifie absence
de correspondance dans ce périmètre, pas absence de droit, exclusion ou classement.

Interface intégrée : fieldset distinct activé pour les lots tarif seulement,
critères séparés, préfixe et pagination propres ; fiche documentaire disponible
pour les codes trouvés. La suite réapplique les critères du rapport, pas un brouillon
modifié depuis. Anciennes actions invalidées par changement de lot/audit en échec.
Les rapports sont affichés comme texte, pas HTML. Cache v66-tariff-criteria.

Opération d'audit `recherche_tarif_criteres`, no-store et épingle/provenance habituels.
Code et mesures refusés ; aucune exception mixte supplémentaire. Export partiel
JSON à provenance simple accepté par whitelist/schéma et contrôleur hors ligne.
Aucune écriture des archives, publication, appel distant ou connexion administrative.

## Limites

Rejeu complet du lot et parcours des libellés avant pagination : pas index,
streaming, mémoire constante ou benchmark national. Préparation et recherche sur
fixtures NON OFFICIELLES ne qualifient aucune source nationale. Cette étape
structure les requêtes métier, mais ne livre pas la compréhension technique,
l'IA de classement, les synonymes sourcés, les notes/exclusions, la consolidation
à date, la validation humaine ou la fiscalité applicable.

## Complément lot 47

[Positions Unicode et extraits originaux par critère](EXTRAITS_TARIF_CRITERES.md) :
positions de chaque terme/libellé, 16 extraits au plus par ligne, affichage intégré
et cache v67. Contrat de sélection ci-dessus inchangé ; aucune validation ajoutée.

## Complément lot 48

[Mode mots entiers normalisés](MODES_CORRESPONDANCE_TARIF.md) optionnel :
`match_mode=mots_entiers` / CLI `--match-mode mots_entiers`. Défaut sous-chaînes
conservé. Même mode pour preuves, positions et pagination ; cache v68.

## Complément lot 49

[Diagnostic documentaire des critères](DIAGNOSTIC_CRITERES_TARIF.md) : compteurs
par terme/critère avant pagination, absence de conjonction distinguée du périmètre
vide et de la page hors résultats. Pas cause métier ou attribut produit déduit.

## Complément lot 50

[Rejeu local des exports](REJEU_EXPORT_CRITERES.md) contre archive explicite par
CLI ; compare le rapport entier sans authentifier source, registre ou utilisateur.
