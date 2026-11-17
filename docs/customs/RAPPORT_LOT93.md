# Rapport du lot 93 — CSV groupé indépendant du fichier partagé

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Mission réglementaire partielle, non recevable pour production fiscale.**

## Correction

Le CSV groupé prépare désormais ses octets en mémoire, avant audit, sans
répertoire/fichier partagé à écrire puis rouvrir. BOM UTF-8, writer CSV,
huit colonnes92, priorité des valeurs et neutraliseur conservés. Contrat HTTP
explicitement changé : **text/csv; charset=utf-8**, **lot.csv**, no-store,
sans ETag/Last-Modified fichier. Anciens fichiers non modifiés.
JSON groupé mémoire conservé ; TXT/XLSX/archives restent fichiers.
[Contrat et limites](CSV_LOT_SNAPSHOT.md).

## Recettes

| Sélection | Résultat | Durée console |
|---|---|---:|
| CSV/exports/attribution/révision/classification/cloisonnement/RBAC | 927 réussis, 1 avertissement | 26,66 s |
| Ancien handler, mêmes 18 nouveaux cas | **9 échecs attendus**, 9 réussis | 5,72 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 58,08 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 315 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 373,74 s |

18 nouveaux cas : contrat HTTP/BOM/colonnes, chemin piégé, anciens fichiers
intacts, ordre/doublons, Unicode/quoting/multiligne, trois refus, job/résultat
absents, deux listes invalides, contrôles JSON/TXT, deux changements humains,
limite200, entrelacement HTTP. Les 41 cas92 restent inclus. Stores/jobs/audits
et HTTP TestClient réels temporaires ; pas navigateur/tableur/fournisseur réel.

Course : horodatage de nom fixé à même seconde, premier export arrêté à l'audit,
PATCH, second fini, premier libéré. Nouveau code : clichés indépendants.
Ancien handler : premier CSV contient AFTER93 du second. **Comparaison des corps
avant en-têtes**, JUnit témoin contrôlé sur cette assertion et AFTER93.
Seul ancien export_batch réinjecté en mémoire ; fixtures/autres handlers conservés,
checkout/aperçu non remplacés. Code de sortie1 attendu, pas seulement nouveau nom
ou média manquant. Neuf contrôles de compatibilité restent réussis.

JUnit complet : 4318 cas, 373.64 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot92 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present`, ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. **Complète non verte**.

## Traçabilité

Code `a2ad14314f92a050cec0d94957a8eaebfb41b783` ; [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42466377924)
sur cette révision : 908 CSV/JSON/horodatage/audit/attribution/démo/action/statuts/
annulation/champs/révision/classification/valeurs/cloisonnement/RBAC,
243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire. Sélections se
recouvrant, pas somme d'effectifs ou complète OCR distante ; pas JUnit distant
téléchargé. Ruff global et diff-check réussis. [Recette](RECETTE_LOT93.json).
Artefacts hors Git : `/home/user/recettes-unocr/lot93/`, `csv-memoire.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`, `ciblee/recette-*/`,
`github-run.json`, `empreintes.json`, ancienne API et plugin témoin.

**26/27 empreintes historiques conformes**, même écart référentiels : attendu
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`, observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`. Pas restauration pour forcer le
vert ; données/dossiers partagés, journaux et exploratoires préservés hors commit,
sans attribution nouvelle de leurs modifications aux tests.

## Limites conservées

CSV groupé HTTP seulement ; autres formats non JSON restent partagés/possiblement
obsolètes. Anciens fichiers/caches non purgés. no-store pas purge clients/offline/
proxies. Séquence de lectures par document, pas transaction lot ou dernier état
à fin transfert. Texte/octet-réponse matérialisés en mémoire, limite200 pas borne
d'octets/CPU/mémoire, pas streaming/charge qualifiés. Neutraliseur/origine92 pas
protection universelle tableur, preuve humaine ou validation fiscale.
Audit post-préparation pas livraison attestée, identité nouvelle ou transaction.
Droits, validation universelle/qualité, détails erreurs, révision processus/ABA
et autres écrivains non refondus.

**Aperçu backend76 maintenu**, code77–93 poussé/testé mais non chargé avant
redémarrage maîtrisé pour préserver les traitements, RBAC absent/ouvert.
**0 nouvel original officiel, 0 article/code officiellement validé, aucune
publication active.** Mission réglementaire non déclarée achevée.
