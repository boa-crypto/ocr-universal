# Bilan de réception — mission UniOCR douanière

**7 novembre 2026 — état global : PARTIEL, NON RECEVABLE POUR PRODUCTION FISCALE.**

Poursuite effectuée sans demandes d'autorisations intermédiaires : lot 44 de constat
littéral description/PDF, puis lot 45 de recette complète et corrections de tests.
Ce document est un bilan de réception technique, **pas un certificat de conformité,
une clôture juridique ou l'affirmation que tous les chantiers sont achevés**.

## État actuel — lot 76

[Valeurs humaines vides](VALEURS_CHAMPS_VIDES.md) : premier emplacement non None
au lieu d'un repli booléen, traces et garde d'annulation compatibles avec `""`.
Statut `corrected` déjà émis par l'API reconnu par le modèle ; export JSON vérifié.
**106 nouveaux cas + 2 cas existants induits / 392 ciblés réussis** ; témoins :
43 échecs attendus/63 réussis, puis annulation seule 4/102. Documentaire
**2 160 Python / 212 JSDOM historiques**. Complète : **3 778 réussis, 2 échecs
Indra, 1 ignoré, 1 avertissement, 472,85 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42414044174),
pas suite OCR complète en CI. **26/27 empreintes conformes**, même écart partagé ;
données et journaux préservés hors commit. Pas refonte multi-niveau undo,
audit exhaustif des replis JavaScript ou migration des anciennes traces.
Aperçu toujours sans RBAC configuré. [Rapport](RAPPORT_LOT76.md),
[recette actuelle](RECETTE_LOT76.json).

## Complément historique — lot 75

[Acteur des audits OCR](ACTEUR_AUDIT_OCR.md) : validation/correction transmettent
le nom du principal autorisé, et non plus la chaîne générique `utilisateur`. Entrées
client ignorées pour l'identité ; jeton global actif `environnement`, sans RBAC
`local`, pas preuve d'une personne authentifiée. Gardes 73/74 conservées.
**33 nouveaux cas / 250 attribution-corrections-cloisonnement-RBAC réussis** ;
contre-épreuve anciens handlers : 20 échecs attendus, 13 réussis. Documentaire
**2 160 Python / 212 JSDOM historiques**. Complète : **3 670 réussis, 2 échecs
Indra, 1 ignoré, 1 avertissement, 382,88 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42412823043),
pas suite OCR complète en CI. **26/27 empreintes conformes** ; données et journaux
conservés hors commit. Pas identité civile, journal signé/WORM, réattribution
historique ou refonte des autres routes. Aperçu toujours sans RBAC configuré.
[Rapport](RAPPORT_LOT75.md), [recette actuelle](RECETTE_LOT75.json).

## Complément historique — lot 74

[Correction OCR sans champ](CORRECTION_OCR_CHAMP_ABSENT.md) : plus de succès,
datation, écriture ou audit de correction pour un champ absent ; service False,
API 404. Corrections réelles et contrôles de rôle/dossier/appartenance conservés.
**38 nouveaux cas / 217 corrections-cloisonnement-RBAC réussis** ; contre-épreuve
ancienne méthode : 20 échecs attendus, 18 réussis. Documentaire **2 160 Python /
212 JSDOM historiques**. Complète : **3 637 réussis, 2 échecs Indra, 1 ignoré,
1 avertissement, 361,72 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42411808580),
pas suite OCR complète en CI. **26/27 empreintes historiques conformes** ;
données et journaux conservés hors commit. Pas transaction, audit signé/WORM,
invalidations de validation ou requalification des faux événements passés.
Aperçu toujours sans RBAC configuré. [Rapport](RAPPORT_LOT74.md),
[recette actuelle](RECETTE_LOT74.json).

## Complément historique — lot 73

[Cloisonnement des routes OCR de dossiers](CLOISONNEMENT_OCR_DOSSIERS.md) :
sept opérations avec rôle/périmètre avant service, appartenance des extractions,
job source autorisé et corps/chemin cohérents à la création. Stores corrigés,
résultat contrôlé transmis au service, deux factories de dates OCR réparées.
**59 nouveaux cas / 179 cloisonnement-RBAC réussis** ; contre-épreuve six anciens
handlers : 10 échecs attendus, 35 réussis, 14 désélectionnés (création exclue).
Documentaire **2 160 Python / 212 JSDOM historiques**. Complète :
**3 599 réussis, 2 échecs Indra, 1 ignoré Indra, 1 avertissement, 357,52 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42411082360),
pas suite OCR complète en CI. **26/27 empreintes historiques conformes** ;
données et journaux conservés hors commit. Pas transaction, concurrence, audit
exhaustif ni activation automatique du RBAC ; aperçu toujours sans RBAC configuré.
[Rapport](RAPPORT_LOT73.md), [recette actuelle](RECETTE_LOT73.json).

## Complément historique — lot 72

[Cloisonnement corrections et annulations](CLOISONNEMENT_CORRECTIONS_CHAMPS.md) :
rôle et visibilité documentaire contrôlés avant lecture/réécriture du résultat
sur PATCH champ et POST annulation. Refus hors périmètre 403, résultat inchangé,
refus audité sans correction réussie. Politique partagée/non classée et jeton global
conservés ; **sans RBAC actif, pas nouvelle protection automatique**.
**44 nouveaux cas / 120 cloisonnement-RBAC réussis** ; contre-épreuve anciens
handlers : 12 échecs attendus, 32 réussis. Documentaire **2 160 Python /
212 JSDOM historiques**. Complète : **3 540 réussis, 2 échecs Indra,
1 ignoré Indra, 1 avertissement, 351,22 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42409835955),
nouvelle étape cloisonnement, pas suite OCR complète en CI. **26/27 empreintes
historiques conformes**, même écart partagé ; données et journaux préservés hors
commit. Pas audit exhaustif des rattachements, transaction ou verrou fiscal.
[Rapport](RAPPORT_LOT72.md), [recette actuelle](RECETTE_LOT72.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément historique — lot 71

[Revue des champs à zéro et rapport final](REVUE_CHAMPS_CONFIANCE_NULLE.md) :
filtre sans test de vérité, seuil strict configuré et exclusion `NOT_DETECTED`
conservés ; rapport construit après recalcul final des champs par le pipeline.
Aucune valeur confirmée, origine ou statut humain révoqué. **27 nouveaux cas /
241 qualité-Baidu réussis** ; contre-épreuve ancien couple qualité/pipeline :
16 échecs attendus, 11 réussis. Stockage/API/export JSON et quatre scénarios de
recalcul vérifiés sur contrats injectés, pas OCR réel qualifié. Documentaire
**2 160 Python / 212 JSDOM historiques**. Complète : **3 496 réussis,
2 échecs Indra, 1 ignoré Indra, 1 avertissement, 498,24 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42404996500),
pas suite OCR complète en CI. **26/27 empreintes historiques conformes**, même
écart partagé et données/journaux préservés hors commit. Pas calibration, migration
historique, garantie après toute édition API ou verrou fiscal.
[Rapport](RAPPORT_LOT71.md), [recette actuelle](RECETTE_LOT71.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément historique — lot 70

[Pages sans sortie dans la qualité](PAGES_SANS_SORTIE_DANS_QUALITE.md) : la limite
constatée au lot 69 est corrigée. Sans mots, non déclarée vide et texte blanc après
`str.strip()`, la page contribue zéro aux moyennes et figure dans
`pages_low_confidence`, même au seuil zéro, avec `OCR_FAILED` conservé.
**27 nouveaux cas / 214 qualité-Baidu réussis** ; contre-épreuve ancien calcul :
24 échecs attendus, 3 réussis. Stockage/API/export JSON et pipeline PNG vérifiés,
registre explicitement vide dans le test, pas faux OCR. Documentaire **2 160 Python /
212 JSDOM historiques**. Complète : **3 469 réussis, 2 échecs Indra, 1 ignoré Indra,
1 avertissement, 429,96 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42403664023),
pas suite OCR complète en CI. **26/27 empreintes historiques conformes**, même
écart partagé et données/journaux préservés hors commit. Pas calibration, migration
historique, changement des champs ou verrou fiscal. Le repli texte sans mots 0,95
reste historique et non requalifié. [Rapport](RAPPORT_LOT70.md),
[recette actuelle](RECETTE_LOT70.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément historique — lot 69

[Localisations Baidu fournies contrôlées](LOCALISATIONS_BAIDU_DECLAREES.md) :
coordonnées requises numériques finies, boîtes positives dans l'image envoyée,
sans clipping, sortie invalide entièrement refusée avec erreur neutre.
**Sans `location`, approximation pleine image conservée**, pas géométrie mesurée.
**54 nouveaux cas / 187 Baidu-provenance réussis** ; contre-épreuve ancien adaptateur :
41 écarts attendus, 6 réussis, 7 désélectionnés. Documentaire **2 160 Python /
212 JSDOM historiques**. Complète : **3 442 réussis, 2 échecs Indra, 1 ignoré Indra,
1 avertissement, 363,12 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42402932739),
pas suite OCR complète en CI. **26/27 empreintes historiques conformes**, même
écart partagé ; données et journaux préservés hors commit. Page échouée sans texte :
anomalie `OCR_FAILED`, mais toujours absente de `pages_low_confidence` et des
moyennes mixtes — limite non corrigée. Pas fournisseur réel ou précision qualifiée.
[Rapport](RAPPORT_LOT69.md), [recette actuelle](RECETTE_LOT69.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément historique — lot 68

[Provenance visible dans le panneau moteurs](AFFICHAGE_PROVENANCE_SCORES.md) :
exécutions séparées, même avec un seul moteur, compteurs Baidu cohérents affichés
et provenance historique/invalide signalée indisponible, sans requalification.
**2 nouveaux tests Python / 47 scénarios JSDOM**, sélection UI/Baidu **143 réussis**.
Témoin ancien renderer : intégration moteur unique échoue comme attendu après
45 contrôles préalables. Documentaire **2 160 Python / 212 JSDOM historiques**.
Complète : **3 388 réussis, 2 échecs Indra, 1 ignoré Indra, 1 avertissement,
362,00 s**. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42402144812),
pas suite OCR complète en CI. **26/27 empreintes historiques conformes**, même
écart partagé et données/journaux préservés hors commit. Pas fournisseur réel,
calibration, navigateur réel, correction géométrique ou recalcul historique des
jauges de qualité. [Rapport](RAPPORT_LOT68.md), [recette actuelle](RECETTE_LOT68.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément historique — lot 67

[Provenance des scores persistée](PROVENANCE_SCORES_PERSISTEE.md) : compteurs
Baidu typés, associés au run et conservés dans résultat/API/export JSON ; pas
copie du raw, pas statut individuel par mot ni provenance inventée pour les
anciens résultats. **43 nouveaux cas**, sélection Baidu/provenance **133 réussis**,
contre-épreuve ancien pipeline **3 échecs attendus sur 3**. Scores et revue humaine
inchangés. Sélection documentaire **2 160 Python / 212 JSDOM**. Complète :
**3 386 réussis, 2 échecs Indra, 1 ignoré Indra, 1 avertissement, 354,33 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42401056646),
pas suite OCR complète en CI. **26/27 empreintes historiques conformes**, même
écart partagé ; données et journaux préservés hors commit. Pas fournisseur réel,
calibration, nouvelle UI ou correction de la géométrie Baidu.
[Rapport](RAPPORT_LOT67.md), [recette actuelle](RECETTE_LOT67.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément historique — lot 66

[Scores Baidu sans valeur inventée](SCORES_BAIDU_SANS_VALEUR_INVENTEE.md) :
plus de constante 0,95 sans score fournisseur ; valeur déclarée finie conservée,
sinon zéro conservateur, pas score mesuré. **30 nouveaux cas**, 90 tests Baidu
hors réseau réussis, 30/30 contre-épreuves négatives attendues sur l'ancien code.
Mots/runs/qualité restent à zéro et page à revoir lorsque le score manque.
Compteurs de provenance sur `EngineOutput.raw`, **non persistés par le pipeline**.
Sélection documentaire **2 160 Python / 212 JSDOM**. Complète : **3 343 réussis,
2 échecs Indra, 1 ignoré Indra, 1 avertissement, 353,43 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42400091694),
pas suite OCR complète en CI. **26/27 empreintes historiques conformes**,
écart partagé et dossiers du lot 64 conservés hors commit. Pas probabilité
calibrée, nouvelle UI de provenance ou fournisseur réel qualifié.
[Rapport](RAPPORT_LOT66.md), [recette actuelle](RECETTE_LOT66.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément — lot 65

[Transport Baidu et diagnostics privés](CONFIDENTIALITE_TRANSPORT_BAIDU.md) :
**59 nouveaux tests**, 60/60 hors réseau réussis. Réponses bornées, TLS vérifié,
redirections refusées, erreurs distantes/exceptions non réémises. **Secrets OAuth
encore présents dans la query envoyée**, traces externes et connectivité réelle
non qualifiées. Sélection documentaire **2 160 Python / 212 JSDOM**. Complète :
**3 313 réussis, 2 échecs Indra, 1 ignoré Indra, 1 avertissement, 342,37 s**.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42399498261),
avec nouvelles étapes Baidu/PDF/UI, pas suite OCR complète en CI. **26/27 empreintes
historiques conformes**, écart partagé du lot 64 et dossiers conservés hors commit.
[Rapport](RAPPORT_LOT65.md), [recette actuelle](RECETTE_LOT65.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément — lot 64

[Concurrence PDFium et durée de vie native](CONCURRENCE_INGESTION_PDF.md) : crash
natif reproduit en processus isolé, ingestion désormais sérialisée par processus,
fermeture des documents/pages/bitmaps sous verrou. **16 nouveaux tests**, 60
chargements/90 pages et quatre dépôts HTTP concurrents réels sur PDF synthétiques.
Sélection PDF/ingestion/UI **32/32**, documentaire **2 160 Python / 212 JSDOM**.
Complète finale : **3 254 réussis, 2 échecs Indra, 1 ignoré Indra,
1 avertissement, 333,52 s**. [CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42398432474),
pas suite OCR complète en CI. **Intégrité : 26/27 empreintes historiques conformes**,
écart `data/referentiels.json` et quatre dossiers partagés modifiés, préservés hors
commit sans restauration ni attribution certaine. Pas certificat d'intégrité du
magasin ni qualification de charge/PDF hostiles.
[Rapport](RAPPORT_LOT64.md), [recette actuelle](RECETTE_LOT64.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément — lot 63

[Contrôle des modules réellement servis](RENDU_MODULES_SERVIS.md) : le test de
rendu en échec au lot 62 passe maintenant sur serveur isolé, **55 assertions
Dossier / 21 Hub** conservées. **6 nouveaux cas Python et 24 contrats Node
imbriqués**, sélection de rendu 8/8 réussie sans ignoré. Sélection documentaire
inchangée : **2 160 Python / 212 JSDOM**. Complète finale : **3 238 réussis,
2 échecs Indra, 1 ignoré Indra, 1 avertissement, 328,63 s**. Aucun nouvel échec,
le rendu documentaire est exécuté et réussi. Pas navigateur réel ni qualification
métier des réponses de cohérence simulées pour l'affichage.
[CI réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42396949741) :
rendu isolé ajouté puis sélection documentaire ; pas suite OCR complète en CI.
[Rapport](RAPPORT_LOT63.md), [recette actuelle](RECETTE_LOT63.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément — lot 62

[Tesseract local réel et suspension du cache non contextuel](OCR_LOCAL_ET_CACHE.md).
**14 nouveaux tests**, 88 régressions réussies ; sélection documentaire inchangée
**2 160 Python / 212 JSDOM**. Complète finale : **3 231 réussis, 2 échecs OCR,
2 ignorés, 1 avertissement, 313,01 s** ; 16 des 18 échecs du lot 61 passent.
Les deux échecs concernent Indra absent. Un contrôle supplémentaire du rendu UI,
forcé séparément sur le port 8000, **échoue aussi** : helper inline historique
incompatible avec les modules externes. Ce résultat n'est pas caché ni inclus
artificiellement dans les totaux de la complète. Cache conservateur désactivé,
pas purgé ; binaire local PNG/PNM seulement, pas déploiement de production.
[CI ciblée réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42395442147)
(ne qualifie ni OCR complet ni les nouveaux tests unitaires hors sélection).
[Rapport](RAPPORT_LOT62.md), [recette actuelle](RECETTE_LOT62.json).
Mission réglementaire inchangée, partielle et non recevable pour production fiscale.

## Complément — lot 61

[Cohérence JUnit](COHERENCE_JUNIT.md) vérifiée sur les cas/statuts réels avant
bilan positif ; pas seulement les totaux déclarés. **2 160 tests Python / 212
scénarios JSDOM** réussis. Nouvelle complète finale avec aperçu actif : **3 192
réussis, 18 échecs, 11 ignorés, 1 avertissement, 218,99 s**, mêmes 18 échecs que 60.
CI ciblée réussie : [run 42393053789](https://github.com/boa-crypto/ocr-universal/actions/runs/42393053789).
Reprise d’environnement et substitution OpenCV headless locale documentées, pas
modification des dépendances projet. Aucun échec OCR déclaré résolu.
[Rapport](RAPPORT_LOT61.md), [recette complète actuelle](RECETTE_LOT61.json).

## Complément — lot 60

[Interface des pistes documentaires](INTERFACE_PISTES_TARIFAIRES.md), action
explicite distincte de la recherche stricte, résumé non validé, fiches/pagination
et export relu/audité. **2 124 tests Python / 212 scénarios JSDOM** réussis,
**74 exports UI/API contrôlés/rejoués**. SW v70 et aperçu actualisés.
Nouvelle suite complète : **3 156 réussis, 18 échecs, 11 ignorés,
1 avertissement, 220,78 s**, mêmes 18 échecs qu'au lot 58 ; suite non verte.
CI ciblée réussie : [run 42391862178](https://github.com/boa-crypto/ocr-universal/actions/runs/42391862178).
[Rapport](RAPPORT_LOT60.md), [recette complète actuelle](RECETTE_LOT60.json).

## Complément — lot 59

[API des pistes documentaires et rejeu](API_PISTES_TARIFAIRES.md), nominatif,
allowlist, provenance épinglée, audit de succès obligatoire ; aucun classement ou
publication. **2 124 tests Python / 186 scénarios JSDOM** réussis ; cinq rapports
API de pistes contrôlés/rejoués en plus des 70 exports UI/API existants. Pas UI de
pistes ajoutée. Complète non relancée : dernière complète lot 58 ci-dessous,
18 échecs OCR toujours ouverts.
[Rapport](RAPPORT_LOT59.md), [recette ciblée actuelle](RECETTE_LOT59.json).
CI ciblée du code 59 réussie : [run 42391189119](https://github.com/boa-crypto/ocr-universal/actions/runs/42391189119).

## Complément — lot 58

[Pistes documentaires partielles](PISTES_TARIFAIRES.md) Python/CLI explicites,
tri de correspondances vérifiable ; pas IA, confiance, attribut produit ou
classement validé. Recherche AND conservée, sans fallback. **2 079 tests Python /
186 scénarios JSDOM** réussis. Nouvelle suite complète : **3 111 réussis,
18 échecs, 11 ignorés, 1 avertissement, 214,61 s** ; mêmes 18 échecs qu'au lot 56.
[Rapport](RAPPORT_LOT58.md), [recette complète actuelle](RECETTE_LOT58.json).
CI ciblée du code 58 réussie : [run 42390539305](https://github.com/boa-crypto/ocr-universal/actions/runs/42390539305),
pas une CI OCR globale verte.

## Complément — lot 57

[Lanceur commun local/CI](LANCEUR_RECETTE_CIBLEE.md) : Ruff, sélection Python,
JSDOM, journaux et JUnit séparés ; codes non masqués, aucun succès avec JUnit absent
ou tests ignorés. **2 043 tests Python / 186 scénarios JSDOM réussis localement**.
**Workflow ciblé réussi sur GitHub Actions**, run [42370535241](https://github.com/boa-crypto/ocr-universal/actions/runs/42370535241),
Ubuntu 24.04 / Node 24. Cela ne rend pas la CI générale verte. Suite complète non
relancée : dernière complète du lot 56 ci-dessous, 18 échecs toujours ouverts.
[Rapport](RAPPORT_LOT57.md), [recette ciblée actuelle](RECETTE_LOT57.json).

## Complément — lot 56

[Isolation des générations de documents de test](RECETTE_ISOLEE.md) : génération
pytest dans des répertoires temporaires, sans réécrire les fixtures suivies.
**27/27 empreintes inchangées après suite complète, sans restauration**.
Sélection : **2 025 tests Python et 186 scénarios JSDOM** réussis. Suite complète
actuelle : **3 057 réussis, 18 échecs, 11 ignorés, 1 avertissement, 211,56 s**.
Même liste de 18 échecs qu'au lot 55. Aucun code de production modifié.
[Résultats machine actuels](RECETTE_LOT56.json), [rapport](RAPPORT_LOT56.md).
Les recettes antérieures sont conservées comme historiques. Mission partielle.

## Complément — lot 55

[Références d’empreintes fournies séparément](EMPREINTES_ATTENDUES_REJEU.md) pour
exports et manifestes : préconditions de rejeu, pas authenticité des références.
Sélection : **2 016 tests Python et 186 scénarios JSDOM** réussis ; 70 exports des
parcours UI/API rejoués avec épingles de test. **Nouvelle suite complète : 3 048
réussis, 18 échecs, 11 ignorés, 1 avertissement, 206,23 s**. Mêmes 18 identifiants
d’échec qu’au lot 50 ; aucun échec OCR annoncé résolu.
[Détail machine actuel](RECETTE_LOT55.json), [rapport](RAPPORT_LOT55.md).
Les recettes complètes 45 et 50 ci-dessous sont historiques. Mission partielle.

## Complément — lot 54

[Rejeu de comparaisons à deux archives](REJEU_DEUX_ARCHIVES.md), dossiers/IDs/types
explicitement ordonnés, sans consolidation ou fusion fiscale. Sélection : **1 989
tests Python et 186 scénarios JSDOM** réussis. Les quatre parcours UI/API ont
produit **70 exports contrôlés structurellement et rejoués identiquement** (58
simples, 12 comparaisons), pas un corpus national ou une conformité intégrale.
Dernière suite complète : lot 50, 18 échecs OCR non résolus.

## Complément — lot 53

[Rejeu natif PDF sur opt-in local](REJEU_EXPORTS_PDF.md), désactivé par défaut,
sans OCR ou droit juridique/fiscal déduit. Sélection : **1 958 tests Python**,
**186 scénarios JSDOM** réussis ; **58 exports réels UI/API rejoués identiquement,
dont 14 PDF**. Interface et droits HTTP inchangés. Dernière suite complète : lot 50,
avec ses 18 échecs OCR toujours non résolus.

## Complément — lot 52

[Rejeu de provenance et relations déclarées](REJEU_PROVENANCE.md) : contrôles,
sources, couverture, historique, relations, écarts du même lot et navigations,
sans interprétation juridique. Sélection : **1 924 tests Python**, **186 scénarios
JSDOM** réussis ; **44 exports réels UI/API rejoués identiquement**. Aucune nouvelle
fonction UI. Dernière suite complète : lot 50, toujours non verte.

## Complément — lot 51

[Rejeu typé des lectures documentaires](REJEU_EXPORTS_TYPES.md) : Code, tarif et
mesures selon matrice fermée, type non deviné. Sélection : **1 888 tests Python**
et **186 scénarios JSDOM** réussis ; 20 exports des quatre parcours UI/API rejoués
identiquement. Pas authenticité, registre ou validation juridique attestés.
La dernière suite complète demeure celle du lot 50 ci-dessous, non relancée
intégralement pour cette extension.

## Recette complète historique — lot 50

[Rejeu local d'exports multicritères](REJEU_EXPORT_CRITERES.md) ajouté contre une
archive fournie explicitement : comparaison complète du résultat, sans authenticité,
registre, signature ou audit serveur attestés. Sélection : **1 853 tests Python**,
**186 scénarios JSDOM** réussis ; quatre exports réels UI/API rejoués identiquement.

**Nouvelle suite complète exécutée au lot 50 : 2 885 réussis, 18 échecs, 11 ignorés,
2 avertissements, 208,03 s.** Mêmes 18 identifiants d'échec qu'au lot 45, tous
conservés ; Tesseract/Indra non provisionnés. Détail machine actuel :
[RECETTE_LOT50.json](RECETTE_LOT50.json), [rapport](RAPPORT_LOT50.md).
Les sections suivantes conservent l'historique ; les chiffres 45 ne sont pas la
nouvelle recette. Mission toujours partielle et non recevable en production fiscale.

## Complément lot 46

[Recherche tarifaire multicritère explicite](RECHERCHE_TARIF_CRITERES.md) ajoutée
après ce bilan : 1 769 tests sélectionnés et 158 scénarios JSDOM réussis, 70 exports
JSON contrôlés sur quatre parcours réels. Pas de matière/fonction/usage certifiés,
synonymes ou IA de classement. La matrice et la suite complète ci-dessous décrivent
la réception 45 ; ses 18 échecs OCR ne sont ni corrigés ni masqués par cet ajout.

## Complément lot 47

[Positions et extraits tarifaires](EXTRAITS_TARIF_CRITERES.md) : chaque terme est
localisé dans le libellé original ; 16 contextes maximum par ligne et affichage
Unicode contrôlé. Sélection : 1 782 tests Python et 169 scénarios JSDOM réussis.
Pas de preuve PDF ou classement validé ajouté. La recette globale reste celle
du lot 45 ; aucun échec OCR annoncé comme résolu.

## Complément lot 48

[Mode mots entiers normalisés](MODES_CORRESPONDANCE_TARIF.md) optionnel, sous-chaînes
par défaut, localisation et pagination cohérentes. Correctif de retrait complet des
outils lors des refus 401/403/503. Sélection : 1 806 tests Python et 178 scénarios
JSDOM réussis ; aucune qualification OCR ou sémantique ajoutée.

## Complément lot 49

[Diagnostic documentaire des critères](DIAGNOSTIC_CRITERES_TARIF.md) : compteurs
par terme et critère ; distingue périmètre vide, absence de conjonction et page
hors résultats. Sélection : 1 820 tests Python et 186 scénarios JSDOM réussis.
Ne déduit aucun attribut technique manquant ou absence de droit. Recette complète
et échecs OCR restent ceux du lot 45.

## Résultats vérifiés au lot 45

| Recette | Résultat |
|---|---|
| Douane, revue, intégrité, interfaces et intégration sélectionnées | 1 741 tests réussis, 52 fichiers, 43,01 s |
| Interface isolée JSDOM | 152 scénarios réussis |
| Pont interface → HTTP → API réelle, quatre formats | 66 exports JSON contrôlés hors ligne, 4 copies PDF Code |
| Configuration et connecteurs corrigés | 97 tests ciblés réussis |
| Suite complète du dépôt après corrections | **2 773 réussis, 18 échecs, 11 ignorés**, 204,32 s |

Un avertissement préexistant Starlette/httpx. Les 18 échecs concernent les moteurs
OCR et les parcours qui en dépendent. Binaire Tesseract et module Indra absents ;
aucune disponibilité simulée ni test d'échec masqué. Détails lisibles par machine :
[RECETTE_FINALE.json](RECETTE_FINALE.json). La suite globale n'est pas entièrement verte.
Les tests réels API/PDF utilisent des **fixtures NON OFFICIELLES**, pas un corpus
réglementaire national ni des connexions administratives réellement qualifiées.

## État des dix phases demandées

| Phase | Livré et vérifié techniquement | Non terminé / non établi |
|---|---|---|
| 1 — Audit préalable | Architecture, stocks historiques, blocages et provenance documentés | StarterPack original absent ; audit officiel national impossible à conclure |
| 2 — Code douanier | Modèles de versions/sources, import PDF + transcriptions, historique, navigation et relations déclarées | Corpus FR/AR exhaustif, modifications/rectificatifs et fidélité non constitués/validés |
| 3 — Tarif et fiscalité séparée | Code10 textuel, hiérarchies, mesures autonomes JSON/CSV/XLSX/XLS/PDF transcrit, consultation séparée | Nomenclature nationale intégrale et sources fiscales réelles non acquises/qualifiées ; rattachements non validés |
| 4 — Recherche et IA | Recherche littérale normalisée FR/AR, filtres, extraits et pistes documentaires partielles explicites | Recherche métier technique/sémantique et IA de classement sourcée non livrées ; pas de candidats juridiquement validés |
| 5 — Relations prouvées | Relations déclarées, inspection des justifications et constats littéraux PDF | Liens juridiques transversaux prouvés entre articles, codes, notes, taxes/régimes/procédures non établis |
| 6 — Administration existante | Revue intégrée, RBAC/allowlist, types explicites, audit, exports, sauvegarde/reprise | Décisions humaines habilitées, contrôle de fidélité complet et workflow de publication non réalisés |
| 7 — API centrales | API privée de quarantaine et adaptateur douanier explicite, refus hors contrat | Connexion administrative réelle autorisée/testée et API métier sur corpus validé non qualifiées |
| 8 — Intégrité et humain | SHA, rejeu, provenance épinglée, audit obligatoire et refus fermés | Authenticité, WORM/signature, attestation humaine et transaction multi-dossiers non établis |
| 9 — Tests réels | Tests isolés, PDFium réel et HTTP/API réels, suite complète exécutée | OCR système non provisionné, charge nationale, navigateurs/accessibilité, cas juridiques et recette métier non qualifiés |
| 10 — Livrables | Code, schémas, CLI/API/UI, contrats et rapports 1–61, bilan et résultats JSON | Corpus officiel, qualification juridique et réception de production non fournis |

Il reste **du développement** (notamment IA métier, consolidation, validation et
publication), pas seulement des pièces externes. L'absence d'originaux ne permet
pas de déclarer les autres phases terminées par défaut. Aucune date ou aucun taux
applicable n'est choisi automatiquement.

## Inventaire réel et conservation

- Quarantaine locale `data/customs-quarantine` absente : aucun lot réel n'y a été
  inscrit par cette campagne. Fixtures uniquement en répertoires temporaires.
- Base historique : **9 codes legacy**, **9 règles**, **4 types de certificats** ;
  ces entrées ne constituent pas une nomenclature nationale validée code10.
- Référentiels : **11 collections vides**. Aucun remplissage fictif de production.
- **0 nouvel original officiel acquis, 0 article/code national officiellement validé,
  0 publication active** au titre de ces travaux.
- SHA base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`.
- SHA référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
- Les anciennes recettes régénéraient des fixtures suivies, restaurées après
  vérification. Depuis le lot 56, générations pytest hors corpus suivi ; recettes
  58/60 sans restauration. Journaux préexistants hors commit ; aucun corpus lourd ajouté.

## Conditions de clôture globale non satisfaites

1. Acquisition/inventaire des originaux autorisés, StarterPack et exports nationaux,
   langues/versions/compteurs et provenance documentaire complète.
2. Qualification des lecteurs sur ces fichiers, fidélité des transcriptions et
   rapprochement des mesures, avec décisions humaines traçables.
3. Développement/qualification du droit à date, des relations transversales, de la
   recherche métier/IA et du workflow de validation/publication/retrait.
4. Référentiels validés intégrés au transit/OCR/marchandises/facturation et aux API
   métier, autorisations centrales réellement testées.
5. Provisionnement OCR puis recette globale, juridique, opérationnelle, de charge
   et de navigateurs ; réception habilitée avant tout calcul réel.

Les points ci-dessus restent ouverts. Ils ne sont remplacés ni par un nombre de
lots, ni par un taux de tests verts. Aucune demande de permission supplémentaire
n'est nécessaire pour lire ce bilan ; il consigne simplement les limites réelles
de ce qui a été exécuté et livré.
