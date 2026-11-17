# Import bancaire et rapprochement (2026-11-14)

Cette note décrit le format d'import bancaire réellement supporté, les règles de
rapprochement et les limites assumées. Elle complète le bilan
`docs/BILAN_RESTE_A_FAIRE_20261114.md` (chantier P1 « rapprochement bancaire »).

## 1. Endpoints

Tous les endpoints sont sous `/api/frais` et appliquent le cloisonnement RBAC par
dossier (`_exige_dossier`, filtrage des listes).

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/banque/operations?dossier_id=…` | lecture des opérations importées |
| POST | `/banque/import` | import JSON — opérateur + |
| POST | `/banque/import-csv` | import CSV (multipart) — opérateur + |
| POST | `/rapprochement/auto` | rapprochement automatique — superviseur + |
| POST | `/rapprochement/manuel` | pointage manuel facture ↔ opération — superviseur + |
| POST | `/rapprochement/annuler` | annulation d'un pointage — superviseur + |

## 2. Format JSON

```json
{
  "dossier_id": "dos_…",
  "operations": [
    {
      "date": "2026-11-11",
      "montant": 100.0,
      "devise": "EUR",
      "reference": "VIR F-1",
      "libelle": "Virement client",
      "contrepartie": "Client SARL",
      "identifiant_externe": "BANQ-123"
    }
  ]
}
```

Champs :

- `date` : ISO `AAAA-MM-JJ`, obligatoire ;
- `montant` : nombre ou chaîne décimale finie, obligatoire ; positif = crédit,
  négatif = débit. Précision maximale : deux décimales. Les formats à virgule,
  espaces insécables, séparateurs de milliers non ambigus (`1,234.56`,
  `1.234,56`) et parenthèses négatives sont acceptés. `NaN`, `Infinity`,
  booléens, `1e3`, `1,234` seul et `12.345` sont rejetés sans écriture ;
- `devise` : code ISO 3 lettres, défaut `EUR` ;
- `reference`, `libelle`, `contrepartie` : texte libre ;
- `identifiant_externe` / `id_externe` : identifiant banque stable, fortement
  recommandé pour la déduplication.

Réponse :

```json
{ "importees": 1, "doublons": 0, "rejetees": [], "operations": ["op_…"] }
```

Les lignes invalides sont rejetées individuellement avec le motif ; l'import
n'est pas atomique ligne par ligne, mais chaque opération est écrite sous
transaction SQLite.

## 3. Format CSV

Délimiteur `,` ou `;` (détecté sur l'en-tête). En-têtes acceptés (insensibles à
la casse/accents) :

- `date`, `date_operation`, `date_valeur` ;
- `montant`, `amount` ;
- `devise`, `currency` ;
- `reference`, `ref`, `reference_paiement` ;
- `libelle`, `label`, `description` ;
- `contrepartie`, `tiers`, `beneficiaire` ;
- `identifiant_externe`, `id_externe`, `id_banque`, `transaction_id`.

Les montants à virgule (`100,00`), espaces insécables et parenthèses négatives
`(50,00)` sont acceptés. Colonnes minimales : `date` et `montant`.

## 4. Déduplication

Une opération est identifiée par `op_<sha256[:24]>` :

- si `identifiant_externe` est fourni : empreinte sur `dossier + identifiant_externe` ;
- sinon : empreinte sur `dossier + date + montant + devise + reference + libelle`.

Un réimport du même relevé ne crée pas de doublon. Si un identifiant externe
est réimporté avec un contenu différent, la ligne est rejetée (`statut 409`)
au lieu d'être ignorée silencieusement. Deux opérations bancaires
réellement distinctes mais sans identifiant externe et strictement identiques
seront volontairement fusionnées : fournir un identifiant banque pour les
distinguer.

## 5. Rapprochement automatique

`POST /api/frais/rapprochement/auto` avec `dossier_id`, `date_debut`, `date_fin`.

Règles :

- seules les opérations **importées**, non rapprochées, dans la période et du
  même dossier sont candidates ;
- devise identique à la facture ;
- montant absolu égal au centime près ;
- sens attendu : facture `emisee` → crédit positif, facture `recue` → débit
  négatif ; si le type est vide, le sens n'est pas contraint ;
- score : montant/devise compatibles (1), référence facture présente dans
  référence/libellé/contrepartie (+2), date facture à ±3 jours (+1) ;
- score minimal 2 : le montant seul ne suffit pas, il faut une référence
  facture présente comme token distinct ou une date à ±3 jours ;
- une seule candidate avec le meilleur score → rapprochement automatique ;
- plusieurs candidates à score égal → `multiples_correspondances`, aucun lien
  n'est écrit ;
- aucune candidate → `aucune_correspondance`.

Effets d'un lien :

- facture : `rapprochee=true`, `operation_bancaire_id`, `statut_paiement=payee`,
  `date_paiement`, `reference_paiement` ;
- opération : `statut=rapprochee`, `facture_id` ;
- audit `rapprochement_bancaire`.

Le taux renvoyé est `(deja_rapprochees + rapprochees) / total_factures`, où
`total_factures` compte toutes les factures du dossier. La réponse distingue
`deja_rapprochees`, `factures_a_rapprocher` et `operations_disponibles`. Sans
opération importée, aucune facture nouvelle n'est liée. Le score est un indice
de règle, pas une probabilité de confiance.

## 6. Pointage manuel et annulation

`POST /rapprochement/manuel` : `dossier_id`, `facture_id`, `operation_id`, `motif`.
Refus 409 si la facture ou l'opération est déjà rapprochée ; 422 si montant ou
devise incompatible.

`POST /rapprochement/annuler` : `dossier_id`, `facture_id`, `motif`. Délie la
facture et l'opération, restaure le statut, la date et la référence de paiement
antérieurs au pointage (snapshot conservé sur l'opération), puis audite
`rapprochement_annule`. Une facture pointée ne peut pas être supprimée ni voir
ses champs de pointage modifiés ; les notes restent modifiables.

## 7. Totaux multi-devises

`GET /api/frais/dossier/{id}/resume` agrège désormais **par devise** avec
`Decimal` et arrondi au centime (`ROUND_HALF_UP`).

- dossier vide : `vide=true`, `devises=[]`, `devise=null`, `consolide=false`,
  avertissement « Aucun frais ni facture » ;
- une seule devise : les clés historiques (`total_frais`, `solde_restant`, …)
  restent renseignées, avec `devise` et `consolide=true` ;
- plusieurs devises : `consolide=false`, clés historiques à `null`, détail dans
  `par_devise`, avertissement explicite. Aucune conversion implicite n'est
  appliquée ; un taux de change doit être daté et sourcé avant toute
  consolidation (non livré ici).

L'interface dossier affiche un tableau par devise dans ce cas, au lieu d'un
total trompeur.

## 8. Limites

- Pas de connecteur bancaire automatique (agrégateur, EBICS, SWIFT) : l'import
  est fichier/JSON.
- Pas de gestion des avoirs, paiements partiels ou lettrage comptable complet.
- Pas de conversion de change automatique ; les taux restent à fournir et
  qualifier.
- Le format CSV est un format pivot simple, pas un parseur natif de chaque
  banque. Un mapping spécifique peut être ajouté sans changer le moteur de
  rapprochement.
