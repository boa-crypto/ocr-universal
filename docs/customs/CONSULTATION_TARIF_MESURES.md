# Nomenclature et mesures autonomes séparées — lot 38

Consultation documentaire d'un code10 exact dans **un lot tarifaire et un lot de
mesures autonome explicitement choisis**. Les valeurs ne sont ni fusionnées ni
publiées comme fiscalité applicable. Égalité textuelle du code demandé seulement,
pas validation d'un rattachement réglementaire.

## Contrats

```text
customs-tariff-measures LOT_TARIF LOT_MESURES --code CODE10 [--tariff-limit 20] [--tariff-offset 0] [--measures-limit 20] [--measures-offset 0]
GET /api/v1/customs-review/tariff-measures?tarif=LOT_TARIF&mesures=LOT_MESURES&code10=CODE10&tariff_limit=20&tariff_offset=0&measures_limit=20&measures_offset=0
```

Deux lots contrôlés, dans cet ordre de types exact : `tarif`, `mesures`. Seule
cette opération autorise cette paire hétérogène ; les comparaisons Code/tarif et
les autres opérations ne gagnent aucune permission implicite. Code chaîne de dix
chiffres ASCII sans conversion ou préfixe ; limites entières 1–100, offsets
0–1000000. Le service vérifie les deux paginations avant de lire le premier lot.

Rapport `type_rapport=consultation_documentaire_tarif_mesures_autonomes` :

- `fiche_nomenclature` : ligne/parents/source et mesures natives du lot tarifaire,
  avec pagination propre `limite_mesures/decalage_mesures/...` ;
- `mesures_autonomes` : recherche par code exact dans le seul lot autonome, avec
  sa source, ses mesures et pagination `limite/decalage/...`. Chaque résultat
  conserve `ligne_declaree=null` : aucune copie de ligne ou jointure persistante ;
- `archives.avant` = nomenclature, `archives.apres` = mesures autonomes. Les clés
  communes du contrat de double provenance sont précisées par `roles_archives` ;
  **avant/après n'est pas une chronologie** ;
- API : `lots_exacts.tarif/mesures` identifient les deux entrées inscrites ; le
  service/CLI n'expose pas les chemins locaux ;
- drapeaux de fusion/identité juridique/rattachement/applicabilité/calcul false.

Les métadonnées et taux restent dans leur bloc d'origine, avec dates de publication
et périodes reçues distinctes. Les taux sont des chaînes décimales exactes ; null
n'est pas zéro. Une même chaîne d'ID dans les deux lots ne dédoublonne rien.

Code absent de la nomenclature reçue : `ligne_trouvee=false` mais les mesures
sélectionnées restent visibles. Cela ne prouve ni existence nationale de ce code
ni suppression, erreur ou exonération. Absence de mesure ne prouve pas absence
nationale de taxe/restriction. Aucun code intermédiaire ou taux applicable inventé.

## Revue et export

Dans la revue existante, sélectionner le lot tarifaire principal, le code exact
de la fiche et un lot autonome inscrit dans le sélecteur dédié. Sans lot autonome
ou sur Code/mesures comme sélection principale, l'outil est désactivé. Pagination
native = celle de la fiche ; pagination autonome dédiée. Suites indépendantes ;
ouverture de la fiche si présente ou consultation séparée du lot autonome.
Changement du lot autonome invalide la réponse et les anciennes actions.

Même administrateur/habilitation de revue, deux manifestes épinglés, deux rejeux,
empreintes de résultat contrôlées et audit obligatoire `consultation_tarif_mesures`.
`no-store`, 422 si paire/paramètres invalides, 409 si intégrité refusée, 503 sans
résultat si audit indisponible. Aucun accès à une URL distante ou écriture métier.

Export partiel relu/audité, enveloppe 1 à **double provenance obligatoire**. Route et
schéma mis à jour ; provenance simple ou ambiguë refusée. Les anciens contrôleurs
à whitelist stricte peuvent refuser cette nouvelle route. Vérification hors ligne
structurelle seulement, pas preuve de fidélité ou authenticité des deux archives.

## Limites

Pas de rapprochement juridique validé, priorité des sources, cumul/remplacement
fiscal, héritage de date, choix à date ou calcul. Pas de validation humaine ajoutée,
publication, import officiel national ou extension CSV/XLSX/PDF autonome. Deux lots
chargés/rejoués entièrement avant pagination : pas mémoire constante, transaction
multi-dossiers, index national ou benchmark de charge. Tests sur fixtures NON
OFFICIELLES avec JSDOM/API réelle, pas recette nationale ou visuelle/accessibilité.
