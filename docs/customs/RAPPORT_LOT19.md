# Avancement — lot 19 : préparation depuis un membre ZIP explicite

**2026-11-06 — quarantaine documentaire, aucune publication réglementaire.**

## Audit et livraison

Inspection des lecteurs CSV/JSON/XLSX/XML, du mapping, des formats du modèle source,
du chargeur avec rejeu et du CLI. Le modèle prévoyait `zip`, mais aucun lecteur
national n’était qualifié et les lots ZIP n’étaient pas rechargeables. Extension
du chemin central : aucune nouvelle table, duplication métier ou dépendance.

- Sélection exacte `membre_zip` + `format_contenu` requis, parmi les quatre formats
  déjà lus. Pas d’auto-détection, fusion de membres ou récursion ZIP générique.
- Lecture en mémoire, **aucune extraction sur disque**. Contrôles des noms,
  doublons, membres spéciaux, chiffrement déclaré, compression et bornes.
- Conservation du ZIP reçu intégral, source format ZIP et SHA256 du ZIP ; SHA256
  distinct du membre lu, sélection/périmètre et membres exclus dans le rapport.
- Mêmes contrôles métier sans zfill ou taux inventé. Localisateurs générés préfixés
  du membre ; références JSON conservées sans réécriture.
- Plan sans écriture, sortie neuve sur option explicite, empreintes et rejeu central.
  Revue API épinglée et auditée réutilisée, sans route d’import/activation ajoutée.

[Guide et limites de confiance](IMPORT_ZIP.md).

## Qualification

**966 tests Python réussis, 1 avertissement Starlette/httpx**, données/journaux
isolés : sélection du [lot 18](RAPPORT_LOT18.md) + `tests/test_customs_zip.py`, soit
**911 + 55 nouveaux cas**. **40 scénarios UI JSDOM réussis** ; pas de nouvelle
qualification visuelle/téléchargement réel ou de suite complète revendiquée.
Ruff et `git diff --check` passent.

Cas nouveaux : plan/archivage/rejeu des quatre formats, conservation des octets,
absence de répertoire extrait, zéros initiaux et absence de TVA inventée,
empreintes ZIP/membre distinctes, non-écrasement, noms hostiles même hors sélection,
options absentes/incompatibles, ZIP ambigu/concaténé/chiffré/corrompu, CRC du membre
lu, bornes, sélection explicite et contenus invalides sans sortie partielle.
Le test CRC hors sélection confirme explicitement la limite du contrat, pas une
validation globale du paquet. Altération du normalisé puis re-hachage refusée par
rejeu. Cinq cas API réels sur lot ZIP temporaire : contrôle, recherche, fiche,
arbre et couverture, avec épingle et audit, corpus identique après lecture.
Fixtures NON OFFICIELLES uniquement ; aucun compte/lot/registre réel créé.

La première recette ZIP ciblée a donné 49 réussites / 1 échec de fixture : le
writer Python tronquait le NUL du nom avant même lecture. Le test injecte désormais
le défaut dans les en-têtes binaires, sans changer leur longueur ; le lecteur le
refuse. Après ajout des contrôles de contenu/rejeu, la sélection complète ci-dessus
passe avec 966 réussites.

Prévisualisation backend redémarrée sur 0.0.0.0:8000 avec le lecteur à jour :
coque/module/service worker 200 avec hôte distant, revue anonyme 403. Coque v48
inchangée. Journaux de service conservés hors commit. Empreintes historiques après
redémarrage identiques :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

**Les autres membres ne sont pas validés : métadonnées ZIP uniquement, pas CRC,
contenu, antivirus, ni authenticité documentaire.** Le ZIP reçu reste une source
non fiable, jamais un paquet assaini. Les bornes ne garantissent pas mémoire/temps
constants. Pas d’archive nationale réelle qualifiée, ni XLS, PDF tarifaire,
déchiffrement, preuve d’éditeur, signature, WORM, consolidation ou validation humaine.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, originaux/modifications exhaustifs,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués. Ce lot ne clôture pas la mission.
