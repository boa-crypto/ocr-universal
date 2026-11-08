# Rapport du lot 89 — export JSON complet depuis un snapshot de résultat

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

L'export JSON complet validait le résultat courant mais pouvait servir le
fichier `exports/result.json` antérieur à une correction/classification.
La route lit désormais une fois le résultat, applique `DocumentResult`, puis
sérialise en mémoire : **pas cache disque ou fichier partagé à réouvrir**.
`application/json`, téléchargement `result.json`, **`Cache-Control: no-store`**,
sans ETag/Last-Modified de fichier. Caches existants non lus ni réécrits ;
aucun dossier/fichier d'export créé par cette route.

Les six changements testés sont visibles dans le téléchargement malgré un
cache antérieur. Un entrelacement de sauvegarde après lecture conserve le
snapshot lu, pas une promesse d'état dernier à la fin du transfert. Forme JSON
sémantique inchangée, indentation compacte. **Autres formats/chemins hors
périmètre**, pas réparation globale des exports. [Contrat](EXPORT_JSON_SNAPSHOT.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| ExportJSON/horodatage/audit/attribution/action/statuts/annulation/révision/classification/RBAC | 816 réussis, 1 avertissement | 26,99 s |
| Ancien export HTTP, mêmes 26 nouveaux cas | **18 échecs attendus**, 8 réussis | 4,08 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 56,55 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 204 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 367,79 s |

26 nouveaux cas : cinq caches valides/invalides/vides, six changements après
cache (confirmation/correction/statut/undo/classification manuelle/auto), un
export sans chemin fichier, un entrelacement, cinq comptes autorisés, trois
refus avant résultat/cache, un job absent, un résultat indisponible malgré
cache, un résultat à statut invalide, un TXT inchangé et un ancien en-tête
conditionnel. HTTP/stores/jobs/audits réels temporaires ; caches artificiels
explicités, relecture typée/empreintes, pas navigateur réel/fournisseur OCR/charge.

Témoin : seul ancien `export_job` réinjecté en mémoire, fixtures/helper conservés.
Checkout et aperçu non remplacés. Dix-huit échecs attendus (contenu/fichier ou
contrat HTTP), huit contrôles gardes/snapshot/erreurs/autre format passent ;
code de sortie1 attendu. Pas preuve de fraîcheur de tous les chemins d'export.

JUnit complet : 4207 cas, 367.704 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot88 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `4052a247179dc7416cf027f5b6a9118742d10478`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42462885964)
sur cette révision : 797 exportJSON/horodatage/audit/attribution/démo/action/
statuts/annulation/champs/révision/classification/valeurs/cloisonnement/RBAC,
243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire. Sélections se
recouvrant, pas effectifs additionnés. Pas suite OCR complète en CI ou JUnit
distant téléchargé. Ruff global et `git diff --check` réussis.
[Recette](RECETTE_LOT89.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot89/`, `export-json.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

**Uniquement JSON complet par cette route**. TXT/CSV/XML/XLSX/PDF, sélection,
batch/archives, `_ensure_export` et exporteurs disque inchangés. Cache JSON
ancien non supprimé/réparé : autres consommateurs peuvent rester obsolètes.
no-store ne purge pas les anciens caches clients/proxies/offline ni ne prouve
qu'ils contactent le serveur. Modèle/JSON matérialisés en mémoire à chaque
requête, pas nouvelle borne ou qualification de charge/streaming.
Pas nouvelle validation universelle qualité/fiscalité ou refonte du détail des
erreurs : indisponibilité409, modèle invalide500, sans repli cache. Snapshot de
contenu, pas signature/révision ou dernier état après mutation concurrente.
Droits, autres écrivains/processus/ABA, audit best-effort et qualité inchangés.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–89 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
