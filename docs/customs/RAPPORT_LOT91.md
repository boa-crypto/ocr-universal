# Rapport du lot 91 — JSON groupé indépendant du fichier horodaté

Mesures datées `2026-11-08` par l'horloge de l'environnement
(JUnit). **Livraison technique ; mission réglementaire partielle,
non recevable pour production fiscale.**

## Correction et contrat explicite

Le JSON groupé écrivait puis rouvrait un chemin commun à une liste d'IDs et une
seconde. Deux requêtes pouvaient donc remplacer leur contenu. La branche JSON
prépare maintenant sa **réponse en mémoire avant audit**, sans répertoire ou
fichier d'export. Fichiers anciens laissés inchangés.

Contrat explicite : **application/json et nom fixe lot.json** (ancien octet-stream/
nom horodaté), no-store, sans ETag/Last-Modified fichier. Tableau brut, ordre,
doublons, nettoyage tokens et limite200 conservés. **Séquence de lectures par
document, pas snapshot atomique du lot**, limite démontrée par test. Contrôle
par job avant sa lecture ; une entrée tardive refusée ne publie pas le lot,
mais des entrées autorisées antérieures peuvent avoir été lues.
Autres formats groupés inchangés. [Contrat](EXPORT_JSON_LOT_SNAPSHOT.md).

## Résultats mesurés

| Sélection | Résultat | Durée console |
|---|---|---:|
| LotJSON/sélectionJSON/exportJSON/horodatage/audit/attribution/révision/classification/RBAC | 868 réussis, 1 avertissement | 24,98 s |
| Ancien lot HTTP, mêmes 26 nouveaux cas | **14 échecs attendus**, 12 réussis | 5,65 s |
| Documentaire, 66 fichiers | 2 160 réussis, 1 avertissement | 56,91 s |
| Interface documentaire historique | 212 scénarios JSDOM réussis | journal conservé |
| Complète locale | **4 256 réussis, 2 échecs, 1 ignoré**, 1 avertissement(s) | 365,76 s |

26 nouveaux cas : quatre ordres/doublons, tokens nettoyés, fichiers anciens
intacts, chemin piégé, en-têtes conditionnels, quatre changements, trois refus,
job absent, résultat absent, quatre listes invalides/trop longues, limite200
répétée, forme brute, TXT fichier, lectures non atomiques et entrelacement HTTP.
TestClient/stores/jobs/audits temporaires réels, barrières maîtrisées ; pas
navigateur, fournisseur OCR ou qualification de charge.

Entrelacement : nom horodaté fixé pour reproduire la même seconde, premier lot
suspendu à l'audit, PATCH, second lot terminé, premier libéré. Chaque réponse
conserve son contenu avec le nouveau code ; ancien handler sert la seconde
valeur au premier. **Assertion de corps avant en-têtes**, JUnit témoin contrôlé
sur cette assertion et `AFTER91`, pas simple échec nom/media/no-store.

Témoin : seul ancien `export_batch` réinjecté en mémoire, autres handlers et
fixtures conservés ; checkout/aperçu non remplacés. Quatorze échecs attendus
contenu/fichier/contrat HTTP et douze contrôles de compatibilité passent ;
code de sortie1 attendu. Pas preuve de concurrence pour les autres formats.

JUnit complet : 4259 cas, 365.668 s ; compteurs
cohérents, pas authenticité attestée. Échecs et ignoré identiques au lot90 :
`tests.test_indra_ocr::test_indra_engine_availability`,
`tests.test_ocr::test_selection_prefers_native_when_present` ; ignoré
`tests.test_indra_ocr::test_indra_engine_recognize`. Indra indisponible,
**suite complète non verte**. Avertissements conservés dans le journal.

## Code, CI et preuves

Code `b175aeb22254b6a445aef2ccb5e4941fb1377426`. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42464600616)
sur cette révision : 849 lotJSON/sélectionJSON/exportJSON/horodatage/audit/
attribution/démo/action/statuts/annulation/champs/révision/classification/valeurs/
cloisonnement/RBAC, 243 qualité/Baidu, 24 ingestion/PDF, 10 UI et documentaire.
Sélections se recouvrant, pas effectifs additionnés. Pas suite OCR complète en CI
ou JUnit distant téléchargé. Ruff global et `git diff --check` réussis.
[Recette](RECETTE_LOT91.json).

Artefacts hors Git : `/home/user/recettes-unocr/lot91/`, `lot-json.{log,xml}`,
`contre-epreuve.{log,xml,exit}`, `complete/pytest.{log,xml}`,
`ciblee/recette-*/`, `github-run.json`, `empreintes.json`, ancienne API et témoin.

## Intégrité et limites

**26/27 empreintes historiques conformes**, même écart partagé : référentiels
attendus `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observés `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration pour forcer le vert. Référentiels, dossiers partagés modifiés,
journaux et exploratoires préservés hors commit sans attribution nouvelle de
leurs modifications aux présents tests.

**JSON groupé seulement**. TXT/CSV/XLSX/archives groupés restent sur fichiers
partagés ; autres formats complets/sélectionnés non JSON inchangés. Anciennes
sorties non réparées/purgées. Pas transaction multi-documents : versions mixtes
possibles, pas dernier état garanti à fin transfert. Résultats bruts sans nouvelle
validation métier/redaction, JSON standard plus strict pour nombres non finis.
Nom/media modifiés explicitement. Limite200 pas borne d'octets/mémoire/CPU,
réponse matérialisée, pas streaming ou charge qualifiés. no-store ne purge pas
les caches clients/proxies/offline. Audit après préparation, pas livraison
attestée ni nouvel acteur authentifié. Autres écrivains, révision processus/ABA,
droits et gestion globale des erreurs non refondus.

**Aperçu backend76 maintenu** pour préserver les traitements : code77–91 poussé/
testé, non chargé avant redémarrage maîtrisé. RBAC absent de l'aperçu historique
ouvert, aucun compte/jeton/protection créé implicitement. **0 nouvel original
officiel, 0 article/code officiellement validé, aucune publication active.**
Mission réglementaire non déclarée achevée.
