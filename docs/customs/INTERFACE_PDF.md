# Lecture PDF intégrée à la revue — lot 22

2026-11-06. **Texte natif non vérifié, pas visionneuse graphique ou validation juridique.**

Dans **Administration → Revue douanière · quarantaine**, choisir un lot Code.
Le panneau « Texte natif PDF reçu » accepte ID exact du document, page physique
1–10 000, limite 1–16 000 et décalage 0–67 108 864. Sur tarif, il est désactivé.
Chaque lecture utilise le [service PDF protégé](LECTURE_PDF.md), ses épingles,
son audit obligatoire et ses limites de processus/temps. Aucun chemin/URL distant,
mot de passe ou binaire PDF n’est manipulé par les commandes navigateur.

La lecture d’un article proposant `document_declare` permet **Lire le PDF reçu
ID — page 1**, uniquement pour un ID et SHA256 documentaires de forme attendue.
Ce bouton n’affirme pas que l’article est situé page 1 : aucune localisation
article→page n’est déduite du localisateur textuel ou d’un numéro du JO.

Le rapport reste affiché en JSON et le fragment en texte DOM `dir=auto`, sans
interprétation HTML. Une absence de texte natif indique explicitement « aucun OCR »
et ne prouve ni page vide ni absence de droit. Pas de correction, traduction,
consolidation, choix de version applicable ou rapprochement de transcription.

## Suites et export

- **Fragment suivant de la page PDF** reprend le décalage retourné, vérifié par
  rapport à la longueur Unicode Python du fragment, sa limite et le total.
- **Page physique PDF suivante** avance exactement d’une page jusqu’au total,
  conserve la limite et remet le décalage texte à zéro.
- Les actions reposent sur ID/SHA cohérents, méthode et unité attendues, bornes
  entières. Elles sont invalidées après changement de lot, de génération, de
  compte ou de résultat. L’API vérifie à nouveau chaque lecture.
- **Exporter ce rapport JSON non validé** relit la même requête protégée avant
  téléchargement. Il exporte le fragment/page et sa provenance, **pas le PDF brut,
  l’ensemble des pages ou le corpus**. Le contrôleur hors ligne accepte maintenant
  la route `/pdf`, dans la même enveloppe version 1 ; une ancienne version du
  contrôleur peut refuser cette nouvelle route, sans invalider les anciens exports.

Un refus/erreur efface l’ancien contenu ; une panne d’audit ne libère aucun résultat.
Les garde-fous locaux ne remplacent pas les habilitations. Un fichier déjà
téléchargé/copié ne peut pas être retiré par révocation ; confidentialité/rétention
restent à traiter par l’opérateur. Coque service worker **v49-lecture-pdf**.

## Qualification et limites

48 scénarios JSDOM, dont 8 nouveaux PDF : paramètres/texte hostile, Unicode et
suites, page sans texte, paramètres/tarif refusés sans appel, suites incohérentes,
ancien bouton après changement de lot/jeton, panne d’audit effaçant les résultats.
Le parcours JSDOM→HTTP→API réel isolé couvre article→PDF→fragment→page suivante→
export avec worker PDF réel ; les Blob PDF et tarif sont acceptés par le contrôle
hors ligne. Les URL objet et l’initiation du téléchargement sont interceptées,
pas de recette de boîte de téléchargement Chrome/Firefox ou de lecteur d’écran.
Fixtures ReportLab NON OFFICIELLES et comptes temporaires uniquement.

Pas d’OCR de page scannée, rendu graphique, téléchargement d’original, extraction
tarifaire PDF, validation humaine ou preuve d’authenticité. Aucun original officiel
nouveau. [Rapport](RAPPORT_LOT22.md).
