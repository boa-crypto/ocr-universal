# Audit maître — UniOCR face au cahier des charges (2026-10-18)

Audit réalisé sur le code réel du dépôt, sans présumer que ce qui est déclaré
fonctionne. Chaque constat indique sa preuve et la commande qui le vérifie.

## 1. Méthode

| Contrôle | Commande | Résultat |
|---|---|---|
| Suite complète | `pytest -q` | **653 passed / 23–24 failed** — les échecs sont **intégralement** l'absence du binaire Tesseract |
| Style | `ruff check src tests tools` | All checks passed |
| Rendu interface | `node tests/_dossier_render_src.js 8123` | **55 contrôles, 0 échec** |
| Rendu hub + statiques | `PORT=8123 node tests/ui_stub_check.js` | 7 statiques + 55 parcours + 21 hub, tous OK |
| Synchronisation modules web | `sync_web_module.py --check` | 5 modules OK |
| Surface API | introspection `app.routes` | ~95 routes |
| Volume | `find` + `wc` | 35 modules, **13 562 lignes** de source, 9 436 lignes de test |

Environnement : Debian 13, 2 CPU, ~1,3 Go de RAM libre, **sans GPU**, Tesseract
absent du PATH. Le moteur réellement utilisé ici est `native_pdf` (texte natif).

## 2. Inventaire par axe — état réel

| Axe | Exigence | État | Preuve |
|---|---|---|---|
| 1 | Classification de document | **Terminé** | `classification.py` (473 l.), 4 catégories + preuves + alternatives ; testé |
| 1 | Provenance champ (doc/page/zone) | **Terminé** | `FieldValue.page_num`, `bbox` ; testé |
| 1 | Valeur brute ≠ normalisée | **Terminé** | `raw_value` / `normalized_value` / `corrected_value` / `confirmed_value` |
| 1 | Différencier imprimé / manuscrit / calculé / déduit | **Partiel** | `zone_typing.py` typage structurel ; **aucun typage sémantique** imprimé/manuscrit/calculé/déduit sur la valeur |
| 2 | Règles de rapprochement | **Terminé** | `coherence.py` (295 l.) : 5 règles, tolérances explicitées, résultats expliqués |
| 2 | Règles **configurables** | **Partiel** | tolérance codée en défaut (`tolerance: float = 0.02`), **pas de point de configuration** |
| 2 | Recalcul ciblé après correction | **Terminé** | constats recalculés depuis les documents à chaque lecture |
| 3 | Confiance, auteur, horodatage, motif | **Terminé** | `field_validated` porte `acteur` + `motif` + `ancienne_valeur` |
| 3 | Interface de validation (clavier, groupée, annulation) | **Partiel** | barre de traitement par lot présente ; **aucun raccourci clavier**, **aucune annulation** |
| 4 | Formulaires + mappings versionnés | **Terminé** | `formulaire.py`, `connectors/forms.py`, `connectors/mapping.py` |
| 4 | Idempotence transmission | **Terminé** | `transmission_dossier.py` (429 l.), états explicites |
| 5 | Workflow, reprise, états | **Terminé** | 10 états, `retry`, `stale`, décisions humaines préservées |
| 6 | Mémoire opérationnelle | **Partiel** | `calibration.py` présent ; pas de tableau de bord « champs les plus corrigés » |
| 7 | Auth jeton, hachage, validation fichier | **Terminé** | `UNIOCR_TOKEN` à temps constant, zip-bomb, signatures magiques |
| 7 | **Autorisation par rôle et par dossier** | **Absent** | un seul rôle, aucun cloisonnement par dossier |
| 7 | **Limitation des tentatives / abus** | **Absent** | aucun rate limiting |
| 7 | **Sauvegarde et restauration** | **Absent** | aucune commande, aucune route |
| 8 | Tableau de bord à métriques réelles | **Terminé** | `/api/stats` calculé sur le magasin (pas de donnée fictive) |
| 8 | **Recherche globale** | **Absent** | pas de endpoint de recherche |
| 9 | Journaux structurés | **Terminé** | `logging_setup.py`, JSON Lines |
| 9 | **Identifiants de corrélation** | **Absent** | aucun `request_id` |
| 10 | Tests | **Terminé** | 676 tests, jeu de référence, benchmarks |

## 3. Défauts réels trouvés pendant cet audit — tous corrigés

| # | Défaut | Preuve | Correctif |
|---|---|---|---|
| D1 | Classification tracée sous `doc_…` introuvable par l'API | `pipeline.py` journalisait `result.id`, jamais réaligné sur `job_id` | `process_file(..., job_id=…)` + réalignement |
| D2 | `GET /api/jobs/{id}/classification` ne renvoyait ni libellé, ni preuves, ni alternatives | route ne lisible que depuis le journal | route fondée sur le résultat, journal pour l'horodatage |
| D3 | Pièces de dossier affichées `job_…` / `unknown` | repli de la route `POST /pieces` | nom et catégorie relus dans le résultat |
| D4 | Correction humaine dont `value_origin` restait `normalized` | `or "corrected"` sur une valeur déjà vraie | bascule systématique + enum `ValueOrigin` |
| D5 | `value_origin` reperdu après un `retry` | réapplication sans restauration de l'origine | restauration explicite |
| D6 | **Aucune route pour trancher un constat de cohérence** | `Constat.status` existait, rien ne l'écrivait | `POST /api/dossiers/{id}/coherence` + persistance |
| D7 | Arbitrage perdu au rechargement | `_lire()` ne restaurait pas `arbitrages` | restauration dans `_lire` |
| D8 | Classeur régénéré sans les arbitrages | route `package` recollectait les constats | reuse de `_constats_coherence` + feuille « Arbitrages » |
| D9 | `genere_zip()` / `genere_json()` sans le paramètre `arbitrages` | signature non propagée | propagation complète |

## 4. Risques restants à traiter

| Risque | Sévérité | État |
|---|---|---|
| **Aucune sauvegarde ni restauration** | **P0** | **traité** (lot 1) — `/api/backups`, `/api/backups/restore`, `/api/backups/verify`, CLI `backup`/`backups`/`restore`, conservation des 5 plus récentes |
| Aucune limitation de débit sur l'API | P1 | **traité** (lot 2) — compteur par client, routes de santé exemptées |
| Aucun identifiant de corrélation dans les journaux | P3 | **traité** (lot 2) — en-tête `X-Correlation-Id`, repris dans l'audit |
| Autorisation par rôle / cloisonnement par dossier | P2 | **traité** (lot 6, 35 tests) — `data/rbac.json` absent par défaut = comportement inchangé |
| Règles de rapprochement non configurables par fichier | P2 | **traité** (lot 4, 18 tests) — section `coherence` de `config/default.json` |
| Raccourcis clavier et annulation dans la validation | P3 | **traité** (lot 5, 7 tests) — annulation tracée sans perte |
| Recherche globale incomplète | P3 | **traité** (lot 3) — recherche inter-documents sur valeurs corrigées et dossiers |
| Crash natif observé (`free(): corrupted unsorted chunks`) sous 3 jobs concurrents, **non reproductible** | P1 | mitigation (sémaphore borné par la RAM) **testée** au lot 9 ; le crash lui-même reste non reproductible ici — `tesseract` et `pdftoppm` sont absents de cet environnement |

---

**Livrables.** Inventaire et état : § 2. Plan d'action priorisé, variables de
configuration, procédure de déploiement et retour arrière lot par lot :
`docs/DEPLOIEMENT.md`. Journal des modifications et résultats mesurés :
`ROADMAP.md`.
