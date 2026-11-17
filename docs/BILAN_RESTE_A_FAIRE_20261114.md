# UniOCR — bilan de ce qui reste à faire

**Date : 14 novembre 2026**  
**État inspecté :** `1ea71dad`, branche `arena/a4e8bc76-ocr-universal`.  
**Périmètre :** code, documentation, tests Python, recette Chromium et sondes API isolées. Aucun correctif fonctionnel n'a été appliqué dans ce bilan.

> **Note de suivi :** ce document est le bilan initial. Les lots P0 à P4 ont
> depuis traité une partie des blocages : voir
> `P0_IMPLEMENTATION_20261114.md`, `P1_FINANCE_IMPLEMENTATION_20261114.md`,
> `P2_FINANCE_DURCISSEMENT_20261114.md`, `P3_SOCLE_TECHNIQUE_20261114.md`,
> `P4_TRANSIT_HYGIENE_20261114.md` et `HYGIENE_DEPOT_20261114.md`. Les sections
> ci-dessous restent l'état de référence avant ces lots, pas un backlog à jour.

## 1. Verdict

**Le socle est largement implémenté, mais la mission métier n'est pas terminée.** UniOCR peut servir de base à un pilote OCR local contrôlé, après validation des moteurs natifs. **Il ne faut pas le présenter comme prêt pour une production métier multi-utilisateur ou une production fiscale en l'état.**

Le premier blocage n'est pas le nombre d'écrans : c'est le **cloisonnement par dossier**, contournable sur plusieurs routes financières et documentaires. Viennent ensuite des fonctions qui renvoient un succès sans effet persistant, le rapprochement bancaire absent, la qualification OCR sur documents réels et l'achèvement réglementaire.

**Aucun pourcentage global fiable ne peut être donné.** Les anciens chiffres « 23 % », « 101/101 écrans conformes » et les conclusions « exploitable en production » ne mesurent pas le même périmètre et ne remplacent pas les vérifications ci-dessous.

## 2. Vérifications effectuées aujourd'hui

| Contrôle | Résultat observé | Interprétation |
|---|---:|---|
| `ruff check src tests benchmarks` | Réussi | Pas d'erreur dans la sélection lint configurée ; ce n'est pas un audit de sécurité complet. |
| Suite Python complète | **4 474 réussis, 15 échecs, 13 ignorés** sur 4 502 cas, 253 s | Socle largement couvert, mais suite non entièrement verte dans cet environnement. |
| Chromium réel, recette produit | **408 passages de routes**, 4 tailles d'écran, 32 captures, **0 exception JavaScript, 0 écriture HTTP** | Navigation/rendu de base vérifiés en lecture seule, pas recette de tous les parcours métier mutants. |
| `tests/test_interface_jsdom.py` avec serveur isolé et une fixture PDF native | **2 réussis** | Smoke 15/15 et parcours justificatifs rejoués. Le smoke exige au moins un document : sur magasin vide il échoue sur le bouton Historique. |
| Sonde RBAC temporaire, deux dossiers et trois utilisateurs | Accès hors périmètre confirmés sur frais/déclarations | Défaut reproductible, détaillé ci-dessous. Aucun magasin utilisateur modifié. |
| Build Docker, OCR raster réel, CI du commit courant | Non exécutés ici | Docker/Tesseract/Poppler absents du bac à sable ; ne pas revendiquer ces validations. |

Environnement : Python 3.11.2, OpenCV headless 4.11, dépendances Python installées dans un environnement temporaire. Indra est installé mais ses modèles ne sont pas disponibles localement (`HF_HUB_OFFLINE=1`). Les 15 échecs concernent la disponibilité/exécution OCR : API santé/moteurs (2), Indra (1), OCR (3), options de traitement raster (4), pipeline raster (2), ressources moteur (2), endpoint moteur (1). Les tests photo ignorés ne constituent donc pas une validation de leur précision.

## 3. P0 — à corriger avant tout déploiement métier partagé

### P0.1. Fermer le contournement du périmètre RBAC

**Constat reproduit avec RBAC réellement actif :** un opérateur affecté uniquement au dossier A reçoit **HTTP 200** pour lire la liste et le détail de frais/déclarations du dossier B, puis modifier ces objets. Les routes de contrôle et de workflow du dossier B acceptent également ses requêtes. En comparaison, `GET /api/dossiers/B` renvoie bien **403**, et une transition demandée par un lecteur renvoie **403**. Le rôle minimal central fonctionne donc, mais le périmètre n'est pas appliqué partout.

**Code concerné :**

- `src/unocr/routes/frais.py:153-190` : listes non filtrées par utilisateur, détail sans garde de dossier ; mêmes vérifications à faire sur modification, suppression, factures et justificatifs.
- `src/unocr/routes/declarations.py:176-213` : listes/détails sans garde de dossier ; étendre aux liquidations et aux mutations.
- `src/unocr/routes/controle_doc.py:31-130` et `routes/workflow.py:185-280` : pas de contrôle de périmètre.
- Étendre l'audit aux routes terminal, expéditions, transport, marchandises et exports liées à un dossier.

**À faire :** garde commune sur l'objet et son dossier d'origine, filtrage des listes avant réponse, contrôle des deux dossiers lors d'une réaffectation, refus tracé avec acteur serveur. Vérifier aussi les téléchargements et exports, pas seulement les écrans.

**Aligner les politiques :** le middleware exige globalement `operateur` pour les écritures financières, alors que la matrice `ACTIONS` prévoit des droits plus élevés pour `frais_creation`/gestion financière. Les alias et la hiérarchie dans `rbac.py` ne sont pas cohérents avec leur documentation. Choisir une matrice unique et la tester.

**Critère de clôture :** matrice automatisée rôle × dossier × lecture/liste/écriture/suppression/export, avec deux dossiers réels temporaires ; aucun accès croisé, aucun faux succès, refus audités.

### P0.2. Remplacer le workflow de démonstration par un workflow persistant

`routes/workflow.py` est enregistré dans l'API, mais :

- `get_workflow()` renvoie `None` et aucune sauvegarde n'est faite ;
- le statut renvoie toujours `creation` et `12.5 %` ;
- une transition vers un état inexistant répond `success: true` sans changer d'état ;
- l'historique renvoie toujours `[]` ;
- les URL comportent un double segment `/api/workflow/workflow/...`.

Parallèlement, `dossier.py` possède déjà des états, recalculs, verrouillages et arbitrages persistants. **Ne pas construire un second moteur indépendant :** converger vers ce magasin ou définir explicitement la relation entre les deux modèles.

**Critère de clôture :** création/lecture après redémarrage, transitions autorisées et refusées, préconditions métier, permissions, motif obligatoire, acteur serveur, historique, concurrence et blocage réel des étapes interdites. Supprimer les réponses de succès simulées.

### P0.3. Persister les résolutions d'anomalies documentaires

`POST /api/controle/{dossier_id}/resoudre` écrit seulement un événement d'audit puis répond « anomalie marquée comme résolue ». Aucun état de résolution n'est enregistré ou réappliqué au contrôle suivant (`routes/controle_doc.py:99-113`).

Le mécanisme d'arbitrage de `DossierStore.trancher_constat()` est une base existante pour les constats de cohérence, mais il ne couvre pas automatiquement ce endpoint.

**À faire :** résolution liée à la règle et aux documents/version concernés, distinction correction / acceptation motivée du risque, réapplication ou expiration explicite lors d'un nouveau contrôle, permissions adaptées et audit. Tester la persistance après reprise et la réapparition d'une anomalie réellement non corrigée.

## 4. P1 — fonctions métier à terminer

| Chantier | Ce qui existe | Ce qui reste / critère de clôture |
|---|---|---|
| **Rapprochement bancaire** | Factures persistantes, bouton et endpoint de rapprochement, test du cas sans import. | `operations_bancaires = []` dans `routes/frais.py:393`. Définir le format bancaire, importer et dédupliquer les opérations, gérer ambiguïtés et rapprochement manuel, conserver références et audit. Un taux de 0 sans import ne doit pas être présenté comme une fonction opérationnelle. |
| **Cohérence financière** | CRUD frais/factures, justificatifs, liquidations et résumé. | Les totaux additionnent des montants de devises différentes sans conversion (`routes/frais.py:335-360`) et les modèles utilisent des flottants. Fixer règles de devise/taux daté et sourcé, arrondis, HT/TVA/TTC, avoirs et paiements partiels ; agréger par devise ou convertir explicitement. Recette comptable sur cas réels. |
| **OCR terrain** | Pipeline, profils, prétraitement, consensus, exports et nombreux tests synthétiques. | Rejouer avec Tesseract/langues et modèles Indra réellement installés ; constituer un jeu annoté de vrais BL, factures, photos de conteneurs/plaques/cartes grises et documents arabes. Mesurer CER/WER et exactitude par champ, corriger les échecs documentés sous Windows, calibrer les scores. Le consensus multi-moteur doit être mesuré avec de vrais moteurs, pas seulement des moteurs simulés. |
| **Connecteurs externes** | Simulateur, export assisté et adaptateur `customs_api` testé hors réseau. | Obtenir spécifications officielles, environnement de test et accès autorisés ; renseigner les champs cibles, auth, idempotence, statuts, accusés et rejets. Réussir une transmission/reprise réelle de bout en bout. L'adaptateur générique ne vaut pas intégration ALCES/ERP/portail déjà livrée. |
| **Référentiels douaniers** | Import en quarantaine, provenance, diff, recherche, lecture PDF, revue, versions et propositions humaines. | Corpus officiel exhaustif FR/AR et tarif national à 10 chiffres, mesures et textes modificatifs ; consolidation et droit à date, conflits/abrogations, RGI/notes/exclusions, ontologie sourcée et critères techniques discriminants. Le moteur de classement IA n'est pas livré. Publication/retrait contrôlés par personnes habilitées, puis raccordement transit/marchandises/facturation sur versions validées. |

### Blocages externes du chantier douanier

- Le **StarterPack** annoncé reste absent du checkout.
- Les répertoires `data/customs-quarantine` et `data/legal-receipts` sont absents ici : les deux PDF de 221 pages décrits dans les rapports ne peuvent pas être rejoués depuis ce seul checkout. Il faut leur support de conservation/transfert sécurisé et leurs empreintes.
- Aucun corpus officiel complet ni validation juridique habilitée n'est démontré. Les anciens calculs à taux hypothétiques sont bloqués : **ne pas les réactiver pour « finir » un écran**.
- Les règles d'effet, exceptions, synonymes admissibles et responsabilités de publication doivent être fournies et qualifiées. Une partie est du développement possible ; ce n'est pas uniquement un blocage d'accès réseau.

## 5. P2 — fiabilisation et finition

1. **Exploitation et récupération :** les sauvegardes et plusieurs tests SIGKILL existent déjà. Étendre aux interruptions upload/backup, créations de journaux, rotations et autres écrivains ; définir collecte contrôlée des résidus, antivirus si requis, sauvegarde externalisée et exercice de restauration. Ne pas promettre l'exactly-once distribué ou l'audit infalsifiable.
2. **CI reproductible :** distinguer prérequis manquants et régressions ; exécuter la suite OCR complète avec binaires et modèles épinglés, pas seulement la recette documentaire ciblée. Ajouter les parcours navigateur mutants sur magasin jetable, mesurer la couverture et vérifier le build Docker. La recette ciblée ne se déclenche automatiquement au push que sur une liste de branches qui ne comprend pas la branche courante ; une PR déclenche les workflows.
3. **Installation/Docker :** `config/default.json` n'est pas copié dans l'image, qui retombe sur les défauts Python, différents notamment pour l'ordre des moteurs. Expliciter la configuration embarquée et tester la parité hors dépôt. Le fichier `requirements.lock.txt` mélange dépendances applicatives et outils d'environnement (Jupyter, `e2b-charts`, etc.) : prévoir un verrouillage minimal et reproductible par cible de déploiement.
4. **Données d'exploitation :** saisir tarifs de frais, règles documentaires, équipes, paramètres métier et natures de marchandise ; terminer les séries historiques longues et exports planifiés si retenus au périmètre. Revoir l'i18n des modules récents.
5. **Qualité UI :** poursuivre les tests clavier/lecteurs d'écran et parcours complets création → contrôle → validation → export → clôture. La recette Chromium réussie est en lecture seule ; elle ne certifie ni WCAG complet ni tous les comportements métier. Le smoke doit amorcer sa fixture ou déclarer explicitement son prérequis.
6. **Hygiène du dépôt :** environ 19 905 fichiers `.venv-agency`, 1 034 fichiers `tmp_packages` et 1 880 fichiers `data` sont suivis malgré les règles d'ignore actuelles. Inventorier puis séparer source, données et artefacts ; vérifier les fichiers de clés/journaux et révoquer tout secret réellement exposé. Ne pas purger les données métier sans sauvegarde ni décision explicite.

## 6. Ce qu'il ne faut pas refaire depuis zéro

Sont déjà présents et largement couverts : ingestion multi-formats, pipeline OCR et prétraitement, profils métier, champs/tableaux/provenance, exports, jobs/lots, recherche/révision, dossiers et pièces, contrôles de cohérence, persistance métier et justificatifs, sauvegarde/restauration, RBAC central, audit, chiffrement optionnel, PWA/thèmes/RTL et coque produit responsive. Le chantier douanier dispose déjà d'un socle documentaire conséquent en quarantaine.

**Le travail restant est surtout de fermer les trous transversaux, remplacer les succès simulés, qualifier sur données réelles et intégrer des sources/services validés — pas de réécrire tout le moteur ou tous les écrans.**

## 7. Ordre d'exécution recommandé

1. **Sécuriser et assainir la base de validation :** P0.1 à P0.3, tests de non-régression, environnement OCR complet et CI verte sur le périmètre annoncé.
2. **Fermer un parcours métier exploitable :** dossier → documents → OCR → contrôle persistant → workflow → validation → export/clôture ; terminer finance/rapprochement avec règles comptables.
3. **Qualifier le terrain :** corpus OCR réel, mesure des moteurs, puis un connecteur externe prioritaire avec son environnement autorisé.
4. **Achever la production réglementaire :** corpus et validation habilitée, droit à date et publication contrôlée, intégration centrale, recette opérationnelle et restauration réelle.

### Informations à réunir pour avancer sans inventer

- Originaux officiels FR/AR, tarif national, mesures, versions et StarterPack ; responsables habilités et politique de publication.
- Documents de terrain annotés et critères d'acceptation par champ.
- Format/exemple anonymisé d'import bancaire et règles de rapprochement/comptabilité.
- Spécifications API, mappings, comptes de test et autorisations du système cible.
- Environnement de déploiement, politique de rôles, conservation, sauvegarde et reprise.

## 8. Reproduire les contrôles principaux

```bash
python -m pip install -e '.[dev,baidu]'
# Sur Linux sans libGL, utiliser une variante OpenCV headless compatible.
npm ci
ruff check src tests benchmarks
python -m pytest tests/ -q --no-header
```

Pour la recette UI, démarrer une instance **isolée** avec `scripts/run_preview.sh`, amorcer un PDF natif dans son magasin temporaire, puis :

```bash
python -m pytest tests/test_interface_jsdom.py -q
npm run ui:product -- http://127.0.0.1:8000 /tmp/unocr-browser-audit
```

Les chiffres de ce bilan sont des observations locales datées, pas un pourcentage d'achèvement ni une certification de production.
