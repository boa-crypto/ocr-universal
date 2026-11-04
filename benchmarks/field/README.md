# Vraies photos terrain (port d'Oran, plaques, cartes grises…)

Ce dossier est le point d'entrée pour mesurer le moteur sur **vos** photos
réelles. Aucun chiffre « terrain réel » n'est produit tant que ce dossier est
vide — les mesures publiées par défaut viennent d'échantillons *synthétiques*
dégradés (voir `run_field_benchmark.py --help`).

## Mode d'emploi

1. Déposez vos photos ici (`.jpg`, `.png`, `.webp`, `.tif`, `.bmp` — 50 Mo max).
   Exemples de sujets : numéros de conteneurs, plaques d'immatriculation,
   cartes grises, connaissements photographiés.

2. Générez le gabarit de vérité terrain :
   ```bash
   python run_field_benchmark.py --init-template
   ```
   Cela crée/remet à jour `ground_truth.json` avec une entrée par photo.

3. Complétez chaque entrée — **uniquement ce que vous avez vérifié vous-même** :
   ```json
   {
     "ma_photo.jpg": {
       "profile": "container",
       "text": "CSQU 3054383",
       "fields": { "container_number": "CSQU 3054383" }
     }
   }
   ```
   - `profile` : `container`, `vehicle_plate`, `carte_grise`, `generic`…
   - `text` : le texte réel du document (sert au CER/WER) — facultatif
   - `fields` : les valeurs réelles des champs (servent à l'exactitude) —
     facultatif, mais au moins l'un des deux est recommandé
   - Laissez une valeur à `""` si vous ne savez pas — jamais de valeur devinée.

4. Lancez la mesure :
   ```bash
   python run_field_benchmark.py --suite real
   ```
   Le rapport `results/field_latest.md` distingue explicitement les mesures
   réelles des mesures synthétiques.

## Confidentialité

Tout reste local : les photos ne quittent jamais la machine. Si vos documents
contiennent des données sensibles, vous pouvez les retirer du dossier après la
mesure ; les résultats ne conservent que les scores et vos textes de référence.
