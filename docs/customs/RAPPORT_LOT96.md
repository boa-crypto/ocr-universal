# Rapport consolidé96 — justificatifs textuels et citations contrôlées

**Fonctions intégrées et testées sur fixtures ; mission globale toujours partielle,
non recevable pour production fiscale.** Aucun nouvel original officiel reçu,
aucun article/code officiellement validé, aucune publication active.

## Travaux réalisés

1. **Pièces techniques rattachées aux dossiers** : API et UI, textes UTF8 saisis,
   collés ou importés localement depuis `.txt`, métadonnées et critères déclarés.
   Ajout/retrait d'abord local, puis sauvegarde explicite par création/révision.
2. **Citations de déclarations d'attributs** : sélection humaine d'un extrait et
   d'une valeur ; contrôle serveur des bornes Unicode et de l'égalité exacte à
   la copie conservée. Conversion des indices UTF16 du navigateur en points de
   code. Aucun attribut déduit ni certifié.
3. **Traçabilité** : SHA256 et taille UTF8 calculés côté serveur, auteur et date
   non fournis par le client. Conservation des pièces identiques, remplacement
   explicite, retrait sans effacer les anciennes versions. Même CAS, transaction
   SQLite et outbox récupérable que les dossiers95.
4. **Consultation historique** : `GET .../assessments/{id}?version=N`, source et
   droits revalidés ; texte ancien accessible sans répéter tous les textes dans
   les sommaires. UI historique en lecture seule, retour à l'état courant possible.
5. **Protection locale du stockage** : base et sidecars présents contrôlés,
   permissions0600 sur POSIX, propriétaire du processus/lien unique/fichier
   régulier exigés ; liens symboliques et FIFO refusés sans blocage. Compatibilité
   avec dossiers anciens sans pièces. Pas de migration destructive.
6. **Reprise** : sauvegarde et restauration du texte et de l'outbox en attente
   sur une cible neuve, après panne de journal simulée. Aucune restauration réelle.

Contrat et limites : [PIECES_TECHNIQUES_DOSSIERS.md](PIECES_TECHNIQUES_DOSSIERS.md).

## Fichiers et intégration

- Nouveau `src/unocr/customs_reference/technical_evidence.py` : contrats bornés,
  citations, intégrité et conservation de l'attribution.
- `assessment.py` : état/versionnement, historique et sécurisation des fichiers.
- `routes/customs_review.py` : pièces dans les écritures et lecture de version.
- `web/customs-assessments.js`, `web/sw.js` : formulaire, import local, citations,
  lecture historique et cache96 ; pas de nouvelles API de publication.
- `tests/test_customs_technical_evidence.py`, scénarios JSDOM/HTTP et contrat de
  cache ; sélection CI et documentation actualisées.

Code fonctionnel `bfd75aca`, durcissement/correction `f12c57c5` sur la branche de
session. Les données/journaux partagés ne sont pas inclus dans les commits.

## Résultats de validation finale

| Vérification | Résultat |
|---|---|
| Nouveaux cas Python | **48** |
| Métier, revue, sauvegarde, UI et permissions | **164 réussis**, aucun échec/ignoré |
| JSDOM métier | **26 scénarios réussis** ; les16 de95 restent inclus |
| JSDOM historique | **212 scénarios réussis**, toujours distincts |
| HTTP/API réelle isolée | POST avec pièce, PATCH, GET courant et GET version1 réussis |
| Recette documentaire | **2244 réussis**, aucun échec/ignoré |
| Suite complète finale | **4399 réussis, 2 échecs Indra historiques, 1 ignoré**, 388,50s |
| CI sur `f12c57c5` | [42472069963 : réussie](https://github.com/boa-crypto/ocr-universal/actions/runs/42472069963) |
| Ruff source/tests/recette, syntaxe JS, diff | Réussis |
| Empreintes historiques | **26/27**, même écart préexistant du référentiel partagé |

Les échecs restent `tests/test_indra_ocr.py::test_indra_engine_availability` et
`tests/test_ocr.py::test_selection_prefers_native_when_present`. Le test de
reconnaissance Indra demeure ignoré. Aucun succès complet ou modèle Indra réel
n'est revendiqué ; aucun échec masqué.

Recette couvre notamment citations inventées/bornes incorrectes, Unicode arabe
et caractères hors BMP, champs d'auteur/SHA/vérification usurpés, dépassements de
taille, critères/identifiants répétés, contrôle des transitions, concurrence CAS,
altération même après recalcul de l'enveloppe externe, lecture sans autorisation,
source modifiée, compatibilité94/95, reprise après503, FIFO, multilien et sidecar
symbolique. Le fichier cible d'un lien refusé n'est ni modifié ni chmodé.

La vérification UI a également corrigé le verrou de création persistant après
consultation historique puis saisie d'un nouvel identifiant. Les permissions et
ce cas ont été ajoutés après une première passe exploratoire : **suite complète
et recette documentaire réexécutées sur la révision finale** ; seules ces dernières
mesures qualifient la livraison. Artefacts préparatoires conservés hors dépôt.

Preuves détaillées : [RECETTE_LOT96.json](RECETTE_LOT96.json), artefacts bruts
`/home/user/recettes-unocr/lot96/`. L'écart SHA du référentiel est inchangé :
attendu `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`,
observé `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.
Aucune restauration destinée à rendre les tests verts.

## Ce que cela ne résout pas

Une citation exacte ne prouve pas que l'attribut est vrai ni qu'un texte est
applicable à la marchandise. Les pièces restent **non vérifiées** ; elles ne
complètent pas automatiquement le produit et ne modifient pas l'admission/tri
des candidats. Pas d'IA, ontologie, comparaison technique sémantique, expertise,
moteur RGI ou consolidation juridique livré sous une autre étiquette.

La conservation porte sur le texte, pas les octets d'un original PDF/image ou
sur une signature. Un BOM peut être retiré par le décodage navigateur. Les
versions conservent les pièces retirées : pas de purge de données personnelles,
chiffrement, quota global de base ou archivage WORM. Les contrôles POSIX ne sont
pas une défense contre le propriétaire/same UID hostile ou une substitution
d'ancêtre du chemin ; ACL Windows et exploitation réelle non qualifiées.

La mission restante exige corpus officiel exhaustif FR/AR et versions, règles
qualifiées et cas d'évaluation, ontologie/IA et droit à date, gouvernance de revue
et publication, contrats/comptes d'intégration centrale et réception habilitée.
Les sites officiels sont hors des hôtes réseau autorisés dans cet environnement.
Du développement reste ouvert : ne pas le confondre avec des tâches achevées.

L'API de l'aperçu partagé reste **backend76**, sans redémarrage ni activation du
RBAC réel. Les fichiers Web sur disque ont changé et peuvent être servis après
rechargement : l'aperçu n'est donc pas une qualification bout-en-bout des API96.
Aucun déploiement/publishing, traitement fournisseur réel supplémentaire ou
manipulation irréversible des données d'exploitation n'a été exécuté.
