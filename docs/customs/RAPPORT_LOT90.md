# Rapport du lot 90 — JSON sélectionné indépendant du fichier partagé

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

Le JSON sélectionné était régénéré mais écrit dans un chemin partagé puis rouvert
pour livraison. Deux requêtes pouvaient donc échanger leur contenu après une
correction intermédiaire. La branche JSON prépare désormais une **réponse mémoire
avant audit**, sans chemin fichier. Les fichiers préexistants restent intacts.

`application/json`, **nom fixe `selection.json`** (changement explicite),
no-store, sans ETag/Last-Modified fichier. Noms de champs non utilisés comme
chemin/pièce jointe. Politique sélection inchangée ; **seul fields est filtré,
autres sections conservées, pas redaction de confidentialité**. Autres formats
sélectionnés restent fichiers partagés. [Contrat](EXPORT_JSON_SELECTION_SNAPSHOT.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| SélectionJSON/exportJSON/horodatage/audit/attribution/action/révision/classification/RBAC | 842 réussis, 1 avertissement | 23,67 s |
| Ancienne sélection HTTP, mêmes 26 nouveaux cas | **15 échecs attendus**, 11 réussis | 5,74 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 55,34 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 230 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 359,51 s |

26 nouveaux cas : trois sélections valides, quatre refus de sélection,
une conservation des autres sections, quatre noms particuliers, un fichier
ancien intact, une primitive chemin piégée, quatre changements après export,
trois refus d'accès, un job absent, un résultat absent, un format interdit,
un TXT fichier conservé et un **entrelacement HTTP réel de deux exports et PATCH**.
TestClient/stores/jobs/audits réels temporaires, barrières de threads maîtrisées ;
pas navigateur réel, OCR fournisseur ou qualification de charge.

Entrelacement : premier export suspendu au point d'audit, correction HTTP,
second téléchargement terminé, puis premier libéré. Nouveau code : chaque
réponse conserve son cliché. Ancien code : premier contenu remplacé par celui
du second. **Assertion des corps avant en-têtes**, JUnit témoin vérifié sur cette
assertion et la valeur `AFTER90`, pas simple échec du nouveau nom/no-store.

Témoin : seul ancien handler `export_selected` réinjecté en mémoire,
autres handlers/fixtures conservés. Checkout/aperçu non remplacés. Quinze échecs
attendus contenu/fichier/contrat HTTP, onze contrôles gardes/erreurs/TXT passent ;
code de sortie1 attendu. Pas garantie de concurrence des autres formats.

JUnit complet : 4233 cas, 359.419 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot89 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `520f5f4a8fafb9dfee5bc224bb7bbe3873c75bf2`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42463606148)
sur cette révision : 823 sélectionJSON/exportJSON/horodatage/audit/attribution/
démo/action/statuts/annulation/champs/révision/classification/valeurs/cloisonnement/
RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire. Sélections se
recouvrant, pas effectifs additionnés. Pas suite OCR complète en CI ou JUnit
distant téléchargé. Ruff global et `git diff --check` réussis.
[Recette](RECETTE_LOT90.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot90/`, `selection-json.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

**JSON sélectionné uniquement**, CSV/TXT/XML/XLSX/PDF sélectionnés conservent
chemins et risques partagés. Autres formats complets, batch/archives/helpers
disque inchangés ; JSON complet corrigé89. Fichiers anciens non purgés/réparés.
Nom de pièce jointe changé explicitement. Filtrage fields pas redaction des
pages/texte/tableaux/classification. Snapshot lu pas dernier état à fin transfert.
Modèle/JSON mémoire, pas borne/streaming/charge qualifiés. no-store ne purge pas
les caches clients/proxies/offline. Audit export conservé après préparation,
pas preuve de livraison ou nouvel acteur attribué. Validation modèle existante
avant bloc génération ; erreurs génération/dossiers dans ce bloc. Pas refonte
qualité, détails erreurs, révision processus/ABA, droits ou autres écrivains.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–90 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
