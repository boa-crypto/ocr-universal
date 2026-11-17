# Avancement — lot 13 : lecture individuelle des versions d’articles

**2026-11-06 — transcription déclarée, pas texte juridiquement applicable.**

## Audit et livraison

Inspection préalable de l’historique, des modèles d’articles, des langues/champs
optionnels, du lecteur/rejeu et de la revue intégrée. La nouvelle consultation
réutilise ces archives, sans second magasin ou reconstruction du texte.

- Service commun `consulter_article` : ID de version exact, distinct du numéro,
  après contrôle/rejeu complet du lot Code.
- Métadonnées, nature originale/modificative/consolidée provisoire, hiérarchie,
  source et références JO/localisateur ; dates/statut explicitement déclarés.
- Lecture d’un champ transcrit explicite par fragments de 1 à 16000 points de code
  Unicode, sans correction, traduction, substitution de langue ou consolidation.
- Champ absent, ID absent et plage au-delà de la fin distingués ; longueur totale,
  présence des champs et décalage suivant explicites.
- CLI `customs-code-read`, GET protégé `/lots/{lot_id}/article?article_id=...`,
  groupe de lecture dans la coque existante et zone texte FR/AR sans HTML interprété.
- Droits nominatifs, épingles, audit minimal et `no-store` réutilisés ; fragments
  effacés lors des nouvelles requêtes/navigation, réponses tardives ignorées.
  Coque service worker v45 ; pas de nouvelle persistance métier ou de cache API.

[Contrat et procédure](LECTURE_ARTICLE.md). Aucun PDF brut ou fichier source servi.
La borne du fragment n’est pas une garantie globale de taille du JSON/rejeu.

## Qualification

**754 tests Python réussis, 1 avertissement Starlette/httpx**, data/logs isolés :
711 cas du lot 12 + **43 nouveaux cas de lecture d’article**. Pas de suite complète
annoncée.

```sh
python -m pytest tests/test_customs_article_detail.py tests/test_customs_tariff_tree.py \
 tests/test_customs_coverage.py tests/test_customs_tariff_detail.py tests/test_customs_history.py \
 tests/test_customs_backup.py tests/test_backup.py tests/test_customs_review.py \
 tests/test_customs_review_ui.py tests/test_customs_search.py \
 tests/test_customs_legal_comparison.py tests/test_customs_legal.py \
 tests/test_customs_reference.py tests/test_customs_xlsx.py tests/test_customs_comparison.py \
 tests/test_corrections_routes.py tests/test_referentiels.py tests/test_referentiels_base.py \
 tests/test_customs_connector.py tests/test_rbac.py tests/test_rbac_ecritures.py \
 tests/test_rbac_reprise.py tests/test_ui_premium.py tests/test_web_architecture_refactored.py -q
npm run ui:customs-review
```

Tests nouveaux : version/ID exact et refus de sélection par numéro, métadonnées et
sources distinctes, langue absente sans repli, texte arabe conservé, reconstruction
exacte par concaténation d’un texte long avec espaces/retours/diacritiques/caractères
hors BMP, séparation origine/modification/compilation, plage au-delà de la fin,
paramètres stricts/booléens, archives corrompues/symlinks, CLI et processus réel
isolé, droits HTTP, mode ouvert et épingle incohérente refusés. Sources inchangées.

**28 scénarios UI JSDOM** réussis : 26 précédents + 2 sur lecture exacte FR/AR,
rendu sûr d’un fragment contenant du balisage hostile, champ absent sans ancien
fragment, refus sans ID et désactivation sur tarif. Le parcours UI → HTTP → API
réelle lit la transcription arabe du lot temporaire avec sa provenance. Fixtures
NON OFFICIELLES, aucun compte ou lot de production créé, aucune réponse métier
simulée dans ce parcours d’intégration.

Ruff, syntaxe JavaScript et `git diff --check` passent. Prévisualisation redémarrée :
coque/module/service worker 200 avec hôte de prévisualisation, lecture anonyme 403.
Empreintes historiques inchangées après redémarrage :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et état documentaire

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** La lecture intégrale possible de la chaîne ne prouve pas
sa fidélité au PDF, l’équivalence FR/AR, son authenticité ou son applicabilité.
StarterPack, originaux/modifications exhaustifs, tarif national courant et sources
fiscales restent à acquérir, rapprocher et valider humainement.

Pas d’OCR/rapprochement PDF-texte, de consolidation à date, de validation humaine
signée, publication, API publique officielle, classification IA ou calcul. Les deux
calculs legacy non sourcés restent bloqués. JSDOM/backend isolé, pas homologation
visuelle/accessibilité complète, benchmark national, transaction globale ou WORM.
Aucun usage réglementaire réel n’est autorisé par ce lot.
