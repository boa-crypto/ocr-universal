# Rapport d'avancement et de complétude — lot 1

2026-11-04. **Livraison partielle ; mission réglementaire non achevée.**

**Suite du 2026-11-06 :** [rapport du lot 2 : XLSX et comparaison locale](RAPPORT_LOT2.md).
[Lot 3 : archivage documentaire du Code et transcriptions déclarées](RAPPORT_LOT3.md),
également daté du 2026-11-06.
[Lot 4 : vérification/rejeu et comparaison des lots Code](RAPPORT_LOT4.md), 2026-11-06.
[Lot 5 : recherche documentaire locale FR/AR](RAPPORT_LOT5.md), 2026-11-06.
[Lot 6 : API de revue administrative strictement autorisée](RAPPORT_LOT6.md), 2026-11-06.
[Lot 7 : sauvegarde/reprise explicite de la quarantaine](RAPPORT_LOT7.md), 2026-11-06.
[Lot 8 : interface de revue intégrée en lecture seule](RAPPORT_LOT8.md), 2026-11-06.
[Lot 9 : historique documentaire des articles](RAPPORT_LOT9.md), 2026-11-06.
[Lot 10 : fiche tarifaire documentaire](RAPPORT_LOT10.md), 2026-11-06.
[Lot 11 : diagnostic de couverture documentaire](RAPPORT_LOT11.md), 2026-11-06.
[Lot 12 : navigation hiérarchique tarifaire documentaire](RAPPORT_LOT12.md), 2026-11-06.
[Lot 13 : lecture individuelle des versions d’articles](RAPPORT_LOT13.md), 2026-11-06.
[Lot 14 : navigation assistée dans les résultats](RAPPORT_LOT14.md), 2026-11-06.
[Lot 15 : audit obligatoire des succès de revue](RAPPORT_LOT15.md), 2026-11-06.
[Lot 16 : export du rapport/page non validé](RAPPORT_LOT16.md), 2026-11-06.
[Lot 17 : contrôle hors ligne des exports](RAPPORT_LOT17.md), 2026-11-06.
[Lot 18 : préparation XML tabulaire explicite](RAPPORT_LOT18.md), 2026-11-06.
[Lot 19 : préparation depuis un membre ZIP explicite](RAPPORT_LOT19.md), 2026-11-06.
[Lot 20 : préparation XLS textuelle OLE/BIFF8](RAPPORT_LOT20.md), 2026-11-06.
Le présent document conserve les résultats historiques du lot 1.

## Complétude réelle

| Élément | Preuve disponible | État |
|---|---|---|
| Corpus du Code des douanes | Consultations partielles et références candidates | Non constitué intégralement |
| Textes originaux binaires | Aucun original éditeur archivé dans ce lot | Manquants |
| Chronologie des modifications/rectificatifs/LF | Liste initiale + pistes documentaires | Non exhaustive, non validée |
| Consolidation à une date | Contrat des versions seulement | Moteur non implémenté |
| Tarif national intégral à 10 chiffres | Interface DGD consultée ; export complet non acquis | **0 ligne nationale vérifiée importée** |
| Dénominateur national courant | Non établi par contrôle de fichier | Inconnu ; aucun pourcentage affiché |
| Validation juridique humaine | Aucune | Non réalisée |
| Publication active | Aucun lot | Interdite dans ce socle |

Le nombre de lignes techniquement préparées à partir d'un fichier n'est **pas**
une preuve de complétude nationale. Les neuf exemples legacy restent en place,
non vérifiés, sans migration silencieuse. Voir DONNEES_NON_VERIFIEES.json.

## Livrables et limites

| Livrable demandé | Ce lot | À réaliser |
|---|---|---|
| 1. Code structuré JSON | Modèle ArticleVersion | Collecte et structuration article par article |
| 2. Originaux | Registre de recherche, aucun binaire officiel | Acquisition/empreintes/contrôle FR et AR |
| 3. Tarif national JSON | Importateur local de préparation | Import intégral officiel, comparaison au fichier |
| 4. JSON Schema | TariffBatch, ArticleVersion, Mesure | Schémas de publication, revue et consolidation |
| 5–6. Métadonnées/provenance | Contrats, registre, archive des fichiers remis, empreintes | Authentification documentaire, archives éditeur complètes |
| 7. Importation | CSV UTF-8/JSON, mapping explicite, quarantaine | XLSX/XLS/PDF/XML/ZIP qualifiés, registre des imports |
| 8. Recherche | Non ajoutée ; recherche legacy non vérifiée conservée | Index central FR/AR, synonymes et critères techniques séparés |
| 9. IA tarifaire | Non livrée | Candidats sourcés, RGI/notes/exclusions, abstention, validation humaine |
| 10. API | Ancien calcul non sourcé bloqué en 503 | API v1 de consultation/histoire/recherche, publication sécurisée |
| 11. Administration | DS existant audité, aucun second shell | Extension écrans, diff de versions, habilitations explicites |
| 12. Tests | 89 tests ciblés réussis | Recette import officiel complet, versions concurrentes actives, articles abrogés/modifiés à date, IA et dossiers transit |
| 13–14. Rapports | Présent rapport, audit, données non vérifiées | Mesure de couverture après acquisition des sources |
| 15. Technique | README, audit, schémas et présente feuille de route | Procédures juridiques/opérationnelles de validation et publication |

## Résultats de tests réellement obtenus

Environnement isolé pour les données et journaux, sans accès au magasin utilisateur :

```sh
iso=$(mktemp -d /tmp/unocr-customs-test-XXXXXX)
UNOCR_DATA_DIR="$iso/data" UNOCR_LOG_DIR="$iso/logs" .venv/bin/python -m pytest \
  tests/test_customs_reference.py tests/test_corrections_routes.py \
  tests/test_referentiels.py tests/test_referentiels_base.py tests/test_customs_connector.py -q
.venv/bin/ruff check src tests
```

Résultat : **89 passed**, un avertissement de dépendance Starlette/httpx ; Ruff OK.
Dont **46 tests nouveaux** du socle douanier : syntaxe stricte, parents indépendants,
doublons, désignations FR/AR, périodes, provenance, absence de taux implicites,
mesures non sourcées/incohérentes, séparation des versions juridiques, comptes de
lignes observées, archives/empreintes, sortie existante refusée, CSV tronqué et CLI,
blocage API du calcul hypothétique. Fixtures explicitement NON OFFICIELLES : aucun
jeu de test n'est publié comme référentiel.

Une première exécution élargie a donné **88 passed / 1 failed** : UNOCR_DATA_DIR
hérité court-circuitait tmp_cfg et partageait les référentiels entre tests. Le
harnais tmp_cfg isole désormais les variables données/journaux/profils par test ;
la réexécution de la même sélection a donné les 89 réussites ci-dessus. Cette
correction évite également les écritures de tests dans un magasin du poste.

**Suite complète non rejouée pour ce lot** : les anciens tests UI peuvent cibler
le serveur actif. Ne pas exposer les données utilisateur à cette recette sans
harnais global isolé. Dernière suite complète antérieure (passe 43) : 1227 passed,
23 failed, 11 skipped ; ce n'est pas un résultat des changements présents.
Les tests OCR environnementaux en échec ne sont pas déclarés corrigés ici.

## Sécurité et non-destruction

Aucun fichier data/reglementation/base.json ou data/referentiels.json réécrit,
aucune migration, aucun import officiel prétendu, aucun taux de remplacement.
Empreintes avant/après identiques (audit initial). La nouvelle préparation écrit
uniquement sur option explicite dans un répertoire neuf ; une sortie existante
est refusée et un lot interrompu ne doit pas être considéré complet.

Les fichiers locaux restent modifiables par l'administrateur : pas d'historique
inviolable, de stockage WORM ou de signature juridique revendiqués. Le futur
registre append-only/revues/publication reste à implémenter avant production.
Les liquidations saisies manuellement et la recherche legacy ne sont pas certifiées
par cette livraison ; le blocage concerne les anciens calculs automatiques de taux.

## Déblocage documentaire prioritaire

1. Fournir UniOCR_Referentiels_StarterPack original (absent) et son origine.
2. Acquérir via canal autorisé les PDF originaux du JO et le fichier tarifaire
   national intégral courant, avec ses versions antérieures et parents SH.
3. Conserver octets, URL, date d'acquisition, SHA256 et conditions d'accès ; ne pas
   utiliser un texte retourné par moteur de recherche comme pièce réglementaire.
4. Contrôler toutes modifications jusqu'à la date de référence (dont LF 2026),
   dates d'effet, rectificatifs, abrogations et dispositions transitoires.
5. Désigner les validateurs réglementaires habilités. Aucune valeur d'IA ni simple
   formulaire d'import ne doit pouvoir auto-publier un texte applicable.

Tâches indépendantes suivantes : adaptateur XLSX strict sur format réel ou contrat
explicite, magasin versionné non destructif, diff de lots et tests d'incohérences,
puis moteur de consultation à date et recherche sur versions validées. Le moteur
IA et les calculs ne seront raccordés qu'à cette publication contrôlée.


Aperçu redémarré sur le backend de ce lot (port 8000, UNOCR_PREVIEW=1), hôte
distant vérifié HTTP 200. La désactivation des calculs est ainsi chargée par le
serveur, et pas seulement présente dans les fichiers source. Les journaux de
service sont conservés et peuvent recevoir les entrées ordinaires de démarrage ;
aucune restauration destructive de ces journaux pour nettoyer Git.
