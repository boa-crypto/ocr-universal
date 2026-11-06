# Avancement — lot 9 : historique documentaire des articles

**2026-11-06 — sources et relations déclarées, aucun droit applicable déduit.**

## Audit et périmètre

Inspection préalable des modèles `ArticleVersion`/`CodeDocumentaireBatch`, des
relations documentées, des lecteurs/rejeux, de la recherche, du CLI, de l’API et
de l’écran du lot 8. Les articles et relations déjà archivés sont réutilisés,
sans seconde base, modification de schéma d’entrée ou nouvelle reconstruction.
Le numéro d’une disposition modificative peut différer de celui de sa cible :
l’affichage ne se limite donc pas à une liste de numéros identiques.

## Livré

- Service commun `historique_article`, opérant sur un lot Code contrôlé/rejoué.
- Sélection exacte des numéros, versions séparées, références/localisateurs,
  hiérarchie, JO et aperçus FR/AR. Statuts et dates d’article restent **déclarés**.
- Chronologie de publication des sources : dates inconnues en fin, départage
  déterministe par IDs ; aucune substitution d’une date d’effet ou de transcription.
- Relations transcrites incidentes aux versions du numéro exact, avec sens,
  justification et référence de preuve. Contexte des extrémités visible même si
  leur numéro diffère. Aucun lien inféré par ressemblance ou égalité de numéro ;
  aucune propagation transitive du graphe.
- Paginations indépendantes des versions et des relations, compteurs explicites,
  sources de page et signalement des documents sans article transcrit.
- CLI `customs-code-history`, GET de revue `/lots/{lot_id}/history?article=...`
  et bouton dans la coque administrative existante. Mêmes droits nominatifs,
  épingles de manifestes, audit minimal, erreurs génériques HTTP et `no-store`.
- Contrôles désactivés pour un lot tarifaire, filtres de recherche explicitement
  distingués de l’historique. Coque service worker version 41, pas de cache API.

[Guide, contrat, commandes et limites](HISTORIQUE_DOCUMENTAIRE.md).
Les relations ont une justification déclarée, pas une preuve vérifiée contre
le PDF. Même numéro, ordre des dates et statut déclaré ne valent pas succession,
consolidation ou validation juridique.

## Qualification

**609 tests Python réussis, 1 avertissement Starlette/httpx**, avec data/logs
isolés : 559 cas sélectionnés au lot 8 + **50 nouveaux cas** d’historique.
Pas de suite complète du dépôt annoncée.

```sh
python -m pytest tests/test_customs_history.py tests/test_customs_backup.py \
 tests/test_backup.py tests/test_customs_review.py tests/test_customs_review_ui.py \
 tests/test_customs_search.py tests/test_customs_legal_comparison.py \
 tests/test_customs_legal.py tests/test_customs_reference.py tests/test_customs_xlsx.py \
 tests/test_customs_comparison.py tests/test_corrections_routes.py \
 tests/test_referentiels.py tests/test_referentiels_base.py tests/test_customs_connector.py \
 tests/test_rbac.py tests/test_rbac_ecritures.py tests/test_rbac_reprise.py \
 tests/test_ui_premium.py tests/test_web_architecture_refactored.py -q
npm run ui:customs-review
```

Les nouveaux tests couvrent : séparation originales/modificatives/compilations,
relation vers un autre numéro, absence de relation inventée, dates distinctes ou
inconnues/égales, statut `applicable` non validé, aperçus bilingues/troncature,
paginations indépendantes, contexte hors page, exclusion des liens transitifs,
absence d’articles transcrits, correspondance exacte sans conversion, paramètres
stricts et booléens refusés, lots corrompus/symlinks, CLI dans un vrai processus
isolé, authentification/autorisation HTTP et empreintes avant/retournée par lecture.
Les instantanés des fichiers vérifient l’absence de modification des sources.

**21 scénarios UI JSDOM** réussis (19 précédents + 2 nouveaux : historique exact
et ses paramètres, refus d’entrée vide/tarif). L’intégration UI → HTTP → API réelle
existante est étendue : retrouve deux versions de même numéro et une disposition
modificative d’un autre numéro, sans succession juridique établie. Les fixtures
sont NON OFFICIELLES et temporaires, jamais installées sur le magasin réel.

Ruff, syntaxe JavaScript et `git diff --check` passent. Prévisualisation redémarrée
avec le code actuel : coque/module/service worker 200, historique anonyme 403.
Aucun compte ou registre de production créé. Empreintes historiques inchangées :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et complétude

Un seul lot en quarantaine, pas d’historique global officiel, de sélection à date,
de consolidation, de validation humaine, de publication, de classement IA ou de
calcul. Aperçus seulement, pas de nouvel accès HTTP aux textes intégraux/PDF.
JSDOM ne remplace pas une qualification visuelle/accessibilité complète dans un
navigateur réel ; pas de benchmark national, de transaction globale ou de WORM.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, originaux et actes modificatifs exhaustifs,
tarif national courant et sources fiscales restent à acquérir et vérifier.
Les calculs legacy non sourcés restent bloqués ; aucun résultat présenté ici ne
doit servir à déterminer des droits ou une règle douanière réelle.
