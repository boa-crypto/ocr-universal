# Rapport lot 35 — copie contrôlée du PDF source reçu

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Audit des archives Code, du lecteur PDF natif, du pipeline autorisation/empreintes/
audit de revue, de l'inventaire et des exports. Constat : le lecteur ne remettait
pas le binaire pour contrôle visuel externe. Ajout sans magasin ni import actif :

- Service `copier_pdf_source`, octets originaux relus et empreinte recontrôlée.
- API protégée `/lots/{lot_id}/pdf-source?document_id=…`, Code seulement, nom ASCII
  dérivé du SHA, pièce jointe non validée/no-store/nosniff/sandbox, provenance.
- Extension optionnelle du constructeur de réponse du pipeline existant : réponse
  construite et contrôlée avant audit obligatoire, jamais remise en cas de 503.
  Routes JSON et leurs exports inchangés.
- Bouton dans l'inventaire des sources : vérification Web Crypto avant création du
  téléchargement, gardes d'obsolescence/compte, refus du navigateur sans SHA256.
- Pas de rendu dans l'application, d'URL distante ou de jeton dans le lien ; cache v61.

[Guide, sécurité et limites](COPIE_PDF_SOURCE.md), [tableau des restes](TABLEAU_LOTS.md).

## Vérifications exécutées

- **1 395 tests Python réussis**, sélection étendue de **43 fichiers**, **25,58 s**,
  **1 avertissement** préexistant Starlette/httpx. Pas la suite OCR entière.
- **22 nouveaux cas Python** : octets exacts/provenance/corpus inchangé, paramètres
  avant lecture, document absent, relecture modifiée, MIME/nom/headers, droits,
  audit obligatoire 503 sans binaire, manifeste/résultat/octets altérés refusés.
- **122 scénarios JSDOM réussis**, dont **8 nouveaux** : téléchargement/hash/nom,
  provenance ou contenu altérés, limite, audit 503, lot/compte modifié pendant
  réception et absence Web Crypto.
- Pont interface/API réelle : **12 exports JSON** toujours vérifiés hors ligne,
  plus **1 téléchargement PDF binaire**, SHA navigateur égal aux octets de l'archive
  et à l'inventaire ; navigation par source et lecture native ensuite conservées.
  Le pont de test retransmet désormais les en-têtes réels de l'API.
- Ruff, syntaxe des trois JS, `git diff --check` : succès.
- Empreintes historiques inchangées :
  - base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  - référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission globale

**0 nouvel original officiel acquis, 0 article/code10 officiel validé, 0 publication
active.** Copie d'archive ≠ acquisition officielle. StarterPack, corpus national,
import fiscal autonome, validation humaine et droit à date restent manquants.
Aucun calcul activé. PDF non validé et non analysé par antivirus ; ne pas l'ouvrir
dans un environnement non protégé. Pas de streaming, mémoire constante, quota
global ou recette des téléchargements en navigateur réel.

## Aperçu et conservation

Aperçu redémarré sur `0.0.0.0:8000` ; smoke avec Host distant de prévisualisation :
racine/module/service worker 200, cache v61 ; route binaire anonyme 403 sans PDF.
Empreintes historiques revérifiées après démarrage. Journaux préservés hors commit.
