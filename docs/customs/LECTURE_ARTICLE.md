# Lecture d’une version d’article — lot 13

2026-11-06. **Transcription déclarée en quarantaine, ni texte applicable ni PDF vérifié.**

## Sélection et contenu

`customs_reference.article_detail.consulter_article` contrôle/rejoue le lot Code
entier puis sélectionne un **ID de version exact**, et non un numéro d’article.
L’ID provient de la recherche ou de l’historique ; aucune sélection automatique
de version originale/modificative/consolidée ou « actuellement applicable ».
Une version consolidée reste explicitement provisoire et non validée.

La réponse contient les métadonnées de cette version (numéro, nature, hiérarchie,
références/localisateur/JO, dates et statut déclarés), son document source et
l’empreinte du manifeste effectivement utilisée. Aucune date de source ne remplit
une date d’article absente ; statut déclaré `applicable` ne vaut pas validation.
Les relations/historiques restent consultables via les vues dédiées, pas reconstruits
par cette lecture.

Un seul champ textuel est demandé par appel : `texte_integral`, `texte_francais`,
`texte_arabe`, `texte_origine` ou `texte_modificatif`. Les champs ne sont ni fusionnés
ni substitués : langue ou champ absent → `texte_renseigne=false`, `fragment=null`,
`total_caracteres=null`. Une traduction n’est jamais produite automatiquement.
L’absence de langue structurée ne prouve pas son absence dans le PDF/texte intégral.

Un ID absent donne `article_trouve=false`, métadonnées/document nulls et fragment
null. Cela signifie uniquement « absent de ce lot », pas absence d’article ou de
règle douanière nationale. Les marqueurs de non-validation restent présents.

## Fragments exacts et Unicode

`limit` : entier 1–16000, défaut 4000 ; `offset` : entier 0–67108864, défaut 0.
La borne de décalage reste cohérente avec le plafond de fichier du lecteur actuel.
ID : chaîne exacte non blanche de 1–256 caractères, sans contrôle. Pas de trim,
recherche floue ou conversion du numéro en identifiant.

`total_caracteres` compte les **points de code Unicode Python**, pas octets,
unités UTF-16 JavaScript, mots ou graphèmes. `decalage_suivant` indique où continuer,
ou null en fin. Utiliser cette valeur retournée, pas `fragment.length` côté JavaScript
(qui compte autrement les caractères hors BMP). Une limite peut séparer une lettre
et son signe combiné ; la concaténation ordonnée des fragments restitue exactement
la chaîne transcrite, sans normalisation ni perte d’espaces/retours/diacritiques.

Une plage au-delà du texte présent donne `texte_renseigne=true`, `fragment=""`,
longueur totale conservée et décalage suivant null : ce n’est pas une langue absente.
La borne concerne le fragment, **pas une garantie globale de taille du JSON** :
les métadonnées déclarées et le rejeu gardent leurs limites existantes.

## Accès

```sh
PYTHONPATH=src python -m unocr.cli customs-code-read /chemin/lot-code \
  --id "$ID_VERSION_EXACT" --field texte_arabe --limit 4000 --offset 0
```

Sortie JSON en lecture seule ; code retour 0 si consultation réussie, même si ID
absent, 2 si paramètres ou lot refusés. Le CLI requiert un accès local au disque.

GET `/api/v1/customs-review/lots/{lot_id}/article` : `article_id` requis, `field`,
`limit`, `offset`. Mêmes droits nominatifs, registre épinglé et audit que les autres
lectures de revue : opération `lecture_article`, IDs de lots sans ID d’article ni
texte dans l’événement métier. Comparaison de l’épingle avant lecture à celle du
manifeste effectivement utilisé. Réponse `no-store`. ID absent → 200 explicite ;
lot inconnu → 404 ; lot tarifaire ou paramètres invalides → 422 ; autres refus
401/403/409/503 selon le guide API. Aucun chemin local ou URL source ne peut être
choisi via cette route. Aucun PDF brut ni fichier source n’est servi.

Dans Administration → Revue douanière · quarantaine : choisir un lot Code puis
le groupe **Lire une version d’article**, saisir son ID exact, choisir le champ
et la plage, puis **Lire le fragment d’article**. Le rapport JSON garde provenance,
statuts et plage ; une zone distincte affiche le fragment comme texte avec direction
automatique FR/AR, sans interprétation HTML. Copier le décalage suivant pour continuer, ou utiliser le bouton « Fragment
suivant de l’article » du [lot 14](NAVIGATION_ASSISTEE.md).
Les paramètres sont indépendants de la recherche/histoire et le groupe est désactivé
sur un lot tarifaire. Toute nouvelle requête efface le fragment précédent ; les erreurs de réponse
et la navigation le laissent effacé. Protections des réponses tardives conservées.
Coque service worker v45 ; les API ne sont toujours pas cachées.

Les limites de confidentialité de l’écran restent applicables : les URL HTTP
contiennent l’ID et les paramètres, un document déjà lu/copié ne peut pas être repris
automatiquement après révocation, et aucune protection DLP/forensique n’est fournie.

## Limites et qualification

La chaîne peut être lue intégralement par plusieurs appels, mais sa correspondance
au PDF, son authenticité, la fidélité FR/AR et son applicabilité ne sont pas établies.
Ni OCR, rapprochement PDF/texte, traduction, consolidation, validation humaine,
publication, téléchargement PDF, classification ou calcul. Aucun nouveau corpus
officiel acquis. Limites des lecteurs/rejeu et concurrence conservées ; qualification
JSDOM/backend isolé, pas homologation visuelle/accessibilité complète ou benchmark
national. [Rapport](RAPPORT_LOT13.md).
