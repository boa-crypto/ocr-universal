# Rapport du lot 92 — valeur retenue dans le CSV groupé

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

Le CSV groupé exposait brute/normalisée, pas la valeur humaine retenue.
Deux colonnes **ajoutées à la fin** : `valeur_retenue`, `origine_valeur`.
Les six précédentes gardent ordre et sens ; clients imposant six colonnes à adapter.
Priorité du helper existant : première non None confirmation/correction/
normalisation/brut, y compris valeurs vides/zéro/False legacy. Origine copiée
du résultat, **pas recalcul ou certification** ; brute/normalisée non écrasées.

Huit colonnes passées par le neutraliseur CSV existant : extension à confiance/
statut et aux nouvelles colonnes. Apostrophe devant les six préfixes reconnus,
**pas protection universelle de tous les tableurs**. UTF-8 BOM et format CSV
conservés. **Fichier partagé inchangé**, pas correctif concurrence CSV ici.
[Contrat](CSV_LOT_VALEUR_RETENUE.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| CSV/lotJSON/sélectionJSON/exportJSON/audit/attribution/révision/classification/RBAC | 909 réussis, 1 avertissement | 27,19 s |
| Ancien CSV, mêmes 41 nouveaux cas | **38 échecs attendus**, 3 réussis | 5,48 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 60,97 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 297 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 385,72 s |

41 nouveaux cas : quatre priorités, quatre vides, quatre zéros/False legacy,
toutes null, aucun champ, 12 confiance/statut avec six préfixes, six valeurs
retenues neutralisées, une origine neutralisée, trois gardes, un contrat de
colonnes, un ordre/doublons et trois chaînes HTTP confirmation/correction/undo.
CSV réel relu avec DictReader/BOM ; stores/jobs/audits temporaires, empreintes
conservées hors changements intentionnels. Malformations legacy explicites,
pas entrées invalides acceptées par PATCH ou tableur réel qualifié.

Témoin : seul ancien export_batch réinjecté en mémoire, autres handlers/fixtures
conservés, checkout/aperçu non remplacés. Trente-huit échecs attendus pour colonnes/
valeurs/neutralisation, trois gardes passent ; code de sortie1 attendu.
Pas preuve de concurrence ou sécurité universelle de tous les formats.

JUnit complet : 4300 cas, 385.598 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot91 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `059c0b0faa2c9af2c226b8b613dd59a501c58738`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42465651618)
sur cette révision : 890 CSV/lotJSON/sélectionJSON/exportJSON/horodatage/audit/
attribution/démo/action/statuts/annulation/champs/révision/classification/valeurs/
cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire.
Sélections se recouvrant, pas effectifs additionnés. Pas suite OCR complète en CI
ou JUnit distant téléchargé. Ruff global et `git diff --check` réussis.
[Recette](RECETTE_LOT92.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot92/`, `valeurs-csv.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

CSV groupé contenu seulement. Chemin horodaté partagé, risque de collision entre
requêtes inchangé. Autres formats/archives/sélections inchangés, JSON groupé
isolé91. Deux colonnes nouvelles pas compatibilité avec clients exigeant six.
Origine/statut déclarés peuvent rester incohérents, pas migration/validation
universelle ou machine à états. Neutraliseur sans normalisation Unicode/espaces,
peut préfixer les nombres négatifs, pas qualification Excel/LibreOffice.
Valeur retenue pas preuve humaine/fiscale. Pas redaction/confidentialité ou
nouvelle borne mémoire/charge/streaming. Lectures par document non atomiques,
limite200, droits, audit, détails erreurs, révision processus/ABA inchangés.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–92 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
