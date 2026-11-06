# Interface de revue douanière — lot 8

2026-11-06. **Lecture seule, quarantaine, non validée juridiquement, non publiée.**

## Accès et intégration

Dans la coque UniOCR existante : **Administration → Revue douanière · quarantaine**,
route `#admin/revue-douaniere`. Le module réutilise la navigation, les classes du
design system, la session personnelle `uniocr_token` et les routes de
[l’API de revue](API_REVUE.md). Pas d’application séparée, de copie de magasin,
de création automatique de compte, de registre ou de lot.

Le menu n’est pas une frontière de sécurité : son comportement RBAC legacy
reste inchangé. L’API exige un administrateur nominatif, un RBAC actif et son
inscription dans `reviseurs`. Le lien direct n’accorde aucun droit supplémentaire.
Dans la prévisualisation sans registre RBAC, le refus d’accès est attendu.
Configurer les habilitations et lots **hors HTTP**, selon le guide API.

## Utilisation

1. Ouvrir l’écran avec son compte personnel. « Actualiser les lots » relit le
   registre, sans réutiliser une liste conservée dans le navigateur.
2. Consulter les IDs, types et empreintes **attendues**. Une entrée de registre
   n’est pas une preuve que son lot est cohérent ou authentique.
3. Sélectionner le lot puis « Contrôler l’intégrité / rejouer ». Le serveur
   relance les contrôles existants, avec vérification de l’épingle du manifeste.
4. Rechercher du texte FR/AR, un code ou une désignation. Les filtres article,
   source déclarée et nature sont disponibles seulement pour un lot Code.
   Limite 1–100, décalage 0–1000000 ; les compteurs et éventuels décalages suivants
   figurent dans la réponse. La recherche garde ses limites de normalisation,
   sans traduction ni classification juridique.
5. Choisir un lot avant et un lot après de même type pour comparer. Une
   différence n’est ni une abrogation ni une date d’effet ou un droit applicable.

Les rapports sont présentés en **JSON lisible**, avec champs/provenance et
marqueurs de non-validation du service commun, sans transformation juridique.
Le texte est inséré comme texte DOM, pas comme HTML ; les résultats ont une
direction automatique FR/AR et une zone défilable. Ce premier écran n’est pas
un éditeur ou une visionneuse du PDF, ni une restitution consolidée à date.
Aucun bouton d’import, de validation humaine, de publication ou de calcul.
Pas d’export documentaire ajouté.

## Erreurs et confidentialité

Messages distincts pour authentification requise (401), accès refusé (403), lot
inconnu (404), incohérence/épingle modifiée (409), paramètres incompatibles (422),
registre indisponible (503). Le corps d’erreur serveur n’est pas affiché.
Une erreur remplace le résultat précédent ; un refus d’accès/registre indisponible
enlève aussi les sélecteurs. Un registre vide est annoncé sans conclure à la
complétude ou à l’absence de documents officiels.

Requêtes relatives de même origine, GET uniquement, jeton personnel existant,
`cache: no-store`. Pas de nouvelle persistance des documents dans localStorage,
sessionStorage ou un cache applicatif. Le service worker conserve seulement la
coque et continue d’exclure les API. La nouvelle ressource statique est incluse
au précache de coque version 40. Une panne réseau ne donne aucun résultat métier
hors ligne.

Navigation/départ de page : la zone documentaire est vidée ; les réponses
asynchrones d’une navigation ou requête antérieure ne remplacent pas la réponse
courante. Un retour depuis le cache de navigation relit le registre. Un changement
de jeton détecté au prochain appel/retour de réponse entraîne un effacement.
Les permissions sont réévaluées **côté serveur à chaque appel** ; une révocation
ne peut pas retirer une information déjà lue/copieuse ou encore affichée sans
nouvel appel. Pas de garantie DLP, d’effacement forensique de la mémoire navigateur,
de secret vis-à-vis des extensions ou d’un poste compromis.

Les recherches sont transmises dans l’URL, comme le prévoit l’API ; les logs
HTTP/proxy peuvent les contenir. Ne pas y envoyer de secrets. Audit best-effort
existant, non WORM ; stockage et gouvernance du serveur à sécuriser séparément.

## Qualification reproductible

- `npm ci` puis `npm run ui:customs-review` : **19 scénarios JSDOM** de contrat,
  avec réponses explicitement NON OFFICIELLES, isolées et jamais livrées au client.
- `pytest tests/test_customs_review_ui.py` : intégration JSDOM → pont HTTP éphémère
  → véritable TestClient/middleware/API, avec lots et comptes de test temporaires.
  Vérifie navigation réelle, liste, contrôle, recherche filtrée, comparaison et
  refus d’un compte lecteur ; les fichiers du corpus temporaire restent inchangés.
  Nécessite Node et jsdom, sinon test marqué ignoré explicitement.
- Non-régression douane/RBAC/sauvegarde/coque : voir [rapport lot 8](RAPPORT_LOT8.md).

JSDOM ne qualifie pas le rendu réel Chrome/Firefox, la navigation clavier complète,
les lecteurs d’écran ou la charge d’un corpus national. Ces validations restent
à effectuer sur le déploiement. Aucun nouveau corpus officiel acquis ici.
