# Rapprochement littéral d’une justification avec son PDF source

Lot 30 — 7 novembre 2026. Constat documentaire en lecture seule, pas preuve juridique.

## Sélection et sens du constat

Choisir un **ID exact de relation**, un fragment de sa justification et une page
physique explicite. Le PDF est imposé par `relation.reference.source_id`, et non par
l’article cible, le numéro d’article, le localisateur libre ou le lecteur PDF ouvert.
La source de preuve reste celle contrôlée par le contrat documentaire existant.

La justification peut être un commentaire ou une paraphrase, pas une citation du
PDF. Sa présence littérale ne prouve pas le lien juridique entre les articles ;
son absence ne prouve pas une erreur. Aucun jugement sémantique n’est produit.

Le noyau du lot 27 est mutualisé : recherche stricte sur le texte natif entier
d’une seule page bornée, première occurrence seulement. Sans normalisation,
traduction, OCR, recherche floue, coordonnées visuelles ou découpage juridique.
La lecture et le rapprochement des articles existants conservent leur contrat.

## CLI et API

```sh
unocr customs-code-relation-pdf-match CHEMIN_LOT \
  --id ID_RELATION_EXACT --page 1 --limit 4000 --offset 0
```

```text
GET /api/v1/customs-review/lots/{lot_id}/relation-pdf-match
    ?relation_id=ID_RELATION_EXACT&page=1&limit=4000&offset=0
```

Page obligatoire en CLI/API, entière 1–10 000. ID non blanc de 256 points de code
maximum sans contrôle/substitut Unicode isolé. Limite entière 1–16 000 ; décalage
entier 0–67 108 864 relatif à la **justification**, pas à l’article ou au PDF.
Paramètres invalides refusés avant lecture du lot.

Même administrateur nominatif habilité, registre épinglé, rejeu, audit obligatoire
et `no-store`. Tarif/paramètres invalides : 422 ; PDF/page illisible ou hors limites :
409 ; audit indisponible : 503 sans résultat. CLI hors contrat d’audit HTTP.
Les URLs peuvent être journalisées par l’infrastructure ; l’audit métier de cette
lecture ne conserve ni ID de relation ni justification.

## Résultat

`relation_trouvee` distingue la relation inconnue. `relation_declaree` conserve
origine/cible/type/référence/statut, mais pas la justification intégrale dupliquée :
seul `fragment_justification` est restitué, avec total/limite/décalage/suite.
La justification entière reste accessible par l’inspection documentaire existante.

| Constat | Présence littérale | Extraction |
|---|---|---|
| `correspondance_litterale_trouvee` | `true` | Oui ; première occurrence retournée |
| `correspondance_litterale_non_trouvee` | `false` | Oui ; aucune correspondance stricte |
| `texte_natif_absent` | `null` | Oui ; page sans texte natif non blanc |
| `relation_absente_du_lot` | `null` | Non |
| `fragment_vide` | `null` | Non |
| `fragment_sans_caractere_non_blanc` | `null` | Non |

Sans extraction, l’existence de la page demandée n’est pas vérifiée ; empreinte
PDF lue/nombre de pages restent `null`. Pas de correspondance positive sur chaîne
vide. Une page absente lors d’une extraction demandée entraîne un refus 409.

`sha256_pdf_lu` identifie les octets remis au worker après recontrôle contre le
lot ; `position_debut_pdf` et `position_fin_pdf_exclusive` encadrent la première
occurrence dans le texte extrait. Unités Unicode Python, pas UTF-16/octets/graphèmes.
Le décalage suivant concerne un autre fragment sur la même page, sans localisation
automatique de la suite dans le PDF ni dénombrement des occurrences.

Même si trouvé : `preuve_juridique_verifiee=false`,
`relation_juridique_etablie=false`, `transcription_verification=non_verifiee`,
`validation_juridique=non_validee`, `publication_active=false`.
Aucun lot, relation ou statut humain n’est écrit/modifié par cette lecture.

## Interface et export

Le formulaire « Rapprochement littéral justification / PDF » permet de saisir
relation/page/limite/décalage. Dans l’inspection des relations, « Préparer le
rapprochement de justification… » remplit le formulaire sans extraction ni appel
HTTP. La page est initialisée à 1 sans interpréter le localisateur : l’opérateur
choisit explicitement sa page puis lance le rapprochement.

Les actions permettent de rapprocher le fragment suivant sur la même page et de
lire la page PDF rapprochée, à la première occurrence trouvée ou au début si absent.
Les anciennes actions deviennent inertes après changement de lot/compte, navigation
ou remplacement de résultat. Tarif désactivé ; textes non interprétés en HTML.

Export JSON partiel existant : relecture sous droits/audit courants, whitelist et
schéma d’enveloppe version 1 étendus à `relation-pdf-match`. Contrôle hors ligne
structurel/déclaratif seulement ; anciens contrôleurs stricts susceptibles de
refuser la nouvelle route. Ni corpus complet ni PDF binaire remis au navigateur.

## Limites

Un seul rejeu par rapprochement, extracteur partagé sans nouveau parseur : PDF
64 Mio, 10 000 pages, 200 000 caractères/page, worker 15 s et gardes Unix best-effort
inchangés. Pas de sandbox OS/antivirus, quota global de concurrence ou RAM constante.
L’ordre natif, les espaces et glyphes peuvent différer du PDF visible. Une
justification retrouvée n’est ni authentifiée, intégralement vérifiée ou validée
juridiquement. Pas de consolidation, droit à date ou calcul douanier réel autorisé.
