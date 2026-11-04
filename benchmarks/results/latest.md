# Rapport de benchmark UniOCR

- Exécution : 2026-10-18 06:53:30 UTC
- Machine : Linux 6.1.158+ x86_64 — 2 cœurs
- Python : Python 3.13.16
- Tesseract : tesseract 5.5.0

> Les chiffres de la suite **synthétique** sont mesurés sur des documents
> générés programmatiquement. Ils ne valent **pas** promesse sur des
> documents réels. La suite **terrain** ne produit un chiffre que si des
> photos réelles annotées sont fournies dans `benchmarks/field/`
> (voir `benchmarks/corpus/README.md`).

## Tests

_Étape ignorée (--no-tests)._

## Contrôle statique de l'interface (syntaxe, DOM simulé, identifiants)

```
  [OK]   syntaxe du script
  [OK]   chargement sur DOM simulé sans ReferenceError
  [OK]   98 identifiants utilisés par le script, tous présents
  [OK]   aucune ressource externe (polices embarquées)

Tous les contrôles statiques de l'interface passent.
```

**Résultat : OK**

## Suite synthétique (documents générés)

```
# Résultats de benchmark UniOCR

- Date : 2026-10-18 06:53:54
- Taille du jeu : 9 fichiers
- CER moyen : 0.0161
- WER moyen : 0.0455
- Exactitude des champs (profil BL) : 1.0 (7/7)
- Champs nécessitant une revue humaine : 0/7
- Mémoire RSS fin de run : 302.6 Mo

| fichier | pages | ms/page | CER | WER | conf. moteur | conf. globale |
|---|---|---|---|---|---|---|
| text_pdf.pdf | 2 | 3685.8 | 0.0 | 0.0 | 0.95 | 0.727 |
| scanned_pdf.pdf | 1 | 2822.1 | 0.0 | 0.0 | 0.941 | 0.47 |
| bl_port.pdf | 1 | 6560.7 | 0.0 | 0.0 | 0.95 | 0.727 |
| skewed.png | 1 | 1644.1 | 0.0968 | 0.2727 | 0.87 | 0.666 |
| dark.png | 1 | 2472.2 | 0.0 | 0.0 | 0.924 | 0.707 |
| table_pdf.pdf | 1 | 1594.2 | 0.0 | 0.0 | 0.95 | 0.727 |
| qr_code.png | 1 | 519.7 | — | — | 0.0 | 0.0 |
| letter.docx | 1 | 31.3 | — | — | 0.95 | 0.95 |
| data.csv | 1 | 11.7 | — | — | 0.95 | 0.95 |

## Limites

- Le jeu est synthétique (documents générés) : les scores mesurés ne sont
  pas une promesse de performance sur documents réels.
- CER/WER ne sont calculés que sur les documents avec vérité terrain texte.
- Normalisation de mesure : espaces uniques et séparateurs « | » neutralisés
  des deux côtés (référence et hypothèse) avant calcul des distances.
- Environnement : 2 CPU, 2 Go RAM, sans GPU.
```

**Résultat : OK**

## Suite terrain (photos réelles annotées)

```
[synth] 16 échantillons — CER moyen 0.008 — champs 31/32
[real] AUCUNE photo réelle fournie dans benchmarks/field/ — aucun chiffre terrain réel n'est produit.
rapport : /home/user/ocr-universal/benchmarks/results/field_latest.md
```

**Résultat : OK**

---

Rapport : /home/user/ocr-universal/benchmarks/results/report_20261018_065330.md
