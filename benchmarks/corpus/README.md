# Corpus de référence — documents réels annotés

Ce dossier est le **seul** endroit d'où peuvent sortir des chiffres de
performance honnêtes sur des documents réels. Tant qu'il est vide, le
benchmark terrain le dit explicitement :

```
[real] AUCUNE photo réelle fournie dans benchmarks/field/ —
aucun chiffre terrain réel n'est produit.
```

**Aucun chiffre réel n'est jamais inventé pour combler ce vide.**

## Où déposer les documents

| Dossier | Contenu |
|---|---|
| `benchmarks/field/` | photos de documents réels (`.png`, `.jpg`, `.jpeg`, `.webp`, `.tif`, `.bmp`) |
| `benchmarks/field/ground_truth.json` | les valeurs attendues, une entrée par fichier |
| `benchmarks/corpus/` | ce dossier : documentation, notes de collecte, comptes rendus |

## Étape 1 — déposer les photos

```bash
cp ~/mes_documents/*.jpg benchmarks/field/
```

## Étape 2 — générer le gabarit d'annotation

```bash
python3 benchmarks/run_field_benchmark.py --init-template
```

Cette commande lit les photos présentes et écrit `ground_truth.json` avec,
pour chaque fichier, les champs du profil à remplir. Elle **n'invente aucune
valeur** : elle prépare la structure.

## Étape 3 — annoter à la main

Éditez `ground_truth.json`. Chaque entrée ressemble à :

```json
{
  "facture_acme.jpg": {
    "profile": "invoice",
    "fields": {
      "invoice_number": "FA-2024-00123",
      "invoice_date": "2024-03-14",
      "total_ttc": "1240.50"
    }
  }
}
```

Règles d'annotation :

- la valeur est celle **qu'un humain lit sur le document**, pas celle que le
  moteur pourrait produire ;
- on annote ce qui est **lisible avec certitude** ; un champ illisible reste
  absent plutôt que deviné ;
- les formats suivent ceux du profil (`date` en ISO, montants avec un point
  décimal) ;
- un document par photo, cadrée et lisible.

## Étape 4 — lancer la mesure

```bash
./benchmarks/run_all.sh
```

ou seulement la suite terrain :

```bash
python3 benchmarks/run_field_benchmark.py --suite real
```

Le rapport est écrit dans `benchmarks/results/` avec l'horodatage, et
`latest.md` pointe toujours sur le dernier.

## Confidentialité

Les photos de documents réels contiennent des données personnelles ou
commerciales. Avant de les déposer :

- **anonymiser** : masquer noms, adresses, numéros de téléphone, IBAN ;
- ne verser que des documents dont vous avez le droit de disposer ;
- `benchmarks/field/` et `benchmarks/corpus/` sont des dossiers de travail :
  ne les intégrez pas à un dépôt public sans anonymisation préalable.

## Ce que le corpus permet de mesurer

| Mesure | Ce qu'elle dit |
|---|---|
| CER moyen par document | taux d'erreur caractère sur document réel |
| Précision par champ | part des champs extraits correctement |
| Champs manqués | part des champs non détectés |
| Champs faux positifs | part des champs détectés à tort |

Ces mesures alimentent la proposition A2 de la feuille de route (calibration
des scores de confiance) : sans corpus, une probabilité annoncée par le
système ne peut pas être considérée comme calibrée.
