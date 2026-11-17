# Avancement — lot 16 : export JSON du rapport de revue

**2026-11-06 — rapport/page non validé, ni corpus complet ni publication officielle.**

## Audit et livraison

Inspection de la lecture commune, des gardes de requête/session, des réponses de
revue et de l’audit obligatoire du lot 15. Aucun nouvel endpoint, accès disque ou
magasin : le téléchargement réutilise les lectures protégées existantes.

- Bouton d’export après consultation, hors simple liste du registre.
- Relecture du même chemin/paramètres par l’API avant création du fichier : droits,
  registre, épingle et audit de succès à nouveau requis. Le rapport frais remplace
  l’affichage ; pas de copie aveugle d’un ancien résultat DOM.
- Enveloppe JSON UTF-8 marquée non validée/non publiée, portée rapport/page, heure
  client non certifiée, requête relative et rapport/provenance reçus.
- Nom fixe `uniocr-revue-non-validee.json`, pas de jeton d’authentification copié.
- Ancien bouton inerte après remplacement ; erreur d’audit ou d’accès sans fichier.
- Blob limité à 10 Mio après construction, URL objet temporaire révoquée ; aucune
  nouvelle persistance serveur ou cache métier. Coque service worker version 48.

[Guide, portée et confidentialité](EXPORT_REVUE.md).
Une recherche, un historique ou une lecture fragmentée n’exporte que sa page/plage.
Aucune collecte automatique de toutes les pages, aucun PDF ou original exporté.

## Qualification

**781 tests Python réussis, 1 avertissement Starlette/httpx**, data/logs isolés :
même sélection que le [lot 15](RAPPORT_LOT15.md), avec intégration UI/API étendue.
Pas de nouveau nombre de tests Python revendiqué ni de suite complète annoncée.

**40 scénarios JSDOM réussis** : 37 précédents + 3 nouveaux :

1. export qui relit le serveur et utilise la nouvelle réponse/provenance, conserve
   les marqueurs et exclut le jeton d’authentification ;
2. panne 503 d’audit empêchant la création d’un fichier et effaçant les actions ;
3. ancien bouton d’export inerte après remplacement de résultat.

```sh
npm run ui:customs-review
# Préfixer avec UNOCR_DATA_DIR et UNOCR_LOG_DIR temporaires avant import API :
python -m pytest tests/test_customs_review_ui.py -q
```

Le parcours d’intégration JSDOM → HTTP → API réelle, sur magasin temporaire, relit
une fiche tarifaire puis examine le Blob exporté : code10, marqueur de non-publication,
empreinte et absence du jeton. Seuls l’initiation du téléchargement navigateur et
l’URL objet sont interceptés ; les données métier passent par les vrais services,
les habilitations et l’audit strict. Les sources de test restent inchangées.
Fixtures NON OFFICIELLES et comptes temporaires, aucun fichier exporté depuis le
magasin réel ou compte/registre de production créé.

Ruff, syntaxe JavaScript et `git diff --check` passent. Prévisualisation existante :
coque/module/service worker 200 avec hôte de prévisualisation ; revue anonyme 403.
Changements statiques servis directement, sans redémarrage backend nécessaire.
Empreintes historiques inchangées :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et corpus

Le fichier n’est ni signé, chiffré, immuable, horodaté de confiance ou officiellement
validé. L’audit atteste une lecture locale préalable, pas la réception du fichier ;
pas de nouvel événement de livraison ou exactly-once. Le navigateur décide de
l’emplacement et des collisions de noms. La limite Blob n’est pas une garantie
mémoire globale. Un fichier déjà enregistré ne peut pas être retiré après révocation.
Textes et paramètres peuvent être sensibles et nécessitent une politique de partage.
JSDOM ne qualifie pas la boîte de téléchargement de tous les navigateurs réels.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, corpus original/modificatif exhaustif,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués ; cet export n’autorise aucun usage
réglementaire réel et ne remplace pas une sauvegarde/reprise de quarantaine.
