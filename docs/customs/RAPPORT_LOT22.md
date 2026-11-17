# Avancement — lot 22 : lecture PDF intégrée à la revue

**2026-11-06 — texte natif non vérifié, aucun corpus publié.**

## Audit et livraison

Inspection du module de revue, de la lecture PDF CLI/API du lot 21, des gardes de
requête/lot/session, de l’export JSON et de son schéma de contrôle hors ligne.
Extension dans le panneau administratif existant, sans nouveau shell ou magasin.

- Commandes PDF Code seulement : ID exact, page physique, limite et décalage.
- Raccourci depuis le document déclaré d’une version d’article, vers page physique 1
  explicitement, pas une localisation automatique de l’article.
- Fragment en texte DOM auto-directionnel, sans HTML, message « aucun OCR » si le
  texte natif est absent. Rapport/provenance et marqueurs non validés conservés.
- Fragment suivant vérifié en points de code Unicode Python, page suivante exacte
  avec offset remis à zéro, ID/SHA/méthode/unité/bornes contrôlés pour les suites.
- Gardes de génération/lot/compte, effacement sur erreur ou refus. Pas de résultat
  libéré si l’audit obligatoire échoue lors de la lecture suivante.
- Export JSON du rapport PDF après nouvelle lecture protégée ; route PDF admise
  dans le contrôleur/schéma d’enveloppe version 1. Pas d’export du binaire ou du
  document complet. Coque service worker version 49.

[Guide opérateur et limites](INTERFACE_PDF.md).
Aucune nouvelle route, source, habilitation ou écriture métier ajoutée.

## Qualification

**1 055 tests Python réussis, 1 avertissement Starlette/httpx**, même sélection
isolée que le [lot 21](RAPPORT_LOT21.md), avec intégration existante étendue.
Pas de nouveau compteur Python revendiqué ni de suite complète annoncée.
**48 scénarios UI JSDOM réussis : 40 précédents + 8 nouveaux PDF.**
Ruff, syntaxe des trois fichiers JavaScript modifiés et `git diff --check` passent.

Les huit cas couvrent paramètres exacts/texte hostile, suites Unicode/page suivante,
absence native sans OCR, refus locaux/lot tarifaire sans requête, suites incohérentes,
ancien bouton après changement de lot/jeton et panne d’audit qui efface le contenu.

Le pont UI/HTTP/API réel réarchive les mêmes transcriptions temporaires avec de
véritables PDF ReportLab NON OFFICIELS, dans un nouveau lot épinglé sans écraser
les précédents. Parcours : article→document PDF→fragment→page suivante→export.
Le worker natif est réellement exécuté et les magasins du test restent inchangés
après consultation. Les Blob exportés PDF **et** tarif sont transmis au contrôle
hors ligne, tous deux structurellement acceptés sans authenticité accordée.

Seules l’URL objet et l’initiation de téléchargement sont interceptées. Pas de
recette du dialogue de téléchargement Chrome/Firefox, rendu visuel ou lecteur
d’écran. Les logs JSON des exports appartiennent uniquement au harnais de test
sur fixtures, pas au navigateur de production ou à ses journaux de service.

Prévisualisation : coque/module/service worker 200 avec hôte distant, PDF anonyme
403. Changements statiques servis directement ; backend du lot 21 déjà chargé,
aucun redémarrage requis pour les commandes UI. Aucun compte/lot/registre utilisateur
créé. Journaux de service conservés hors commit. Empreintes historiques identiques :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

Pas de visionneuse graphique, OCR automatique, export d’original, rapprochement
article/page/transcription, classification ou validation juridique. Le texte natif
peut être absent, mal ordonné ou différer de l’apparence visuelle. Le contrôle
hors ligne ne certifie pas la fidélité du rapport ou son origine. Les limites du
worker/processus du lot 21 restent applicables ; pas d’antivirus ou sandbox OS.
Un export partiel déjà téléchargé ne peut pas être retiré après révocation.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, originaux/modifications exhaustifs,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués ; la mission réglementaire est partielle.
