# Export JSON d’un rapport de revue — lot 16

2026-11-06. **Rapport ou page non validé, pas corpus réglementaire complet.**

Après une consultation réussie, hors simple liste du registre, le bouton
**Exporter ce rapport JSON non validé** relance exactement la lecture protégée
ayant produit le rapport, avec ses paramètres. Il ne sérialise pas simplement une
ancienne copie DOM. Autorisation nominative, registre, épingle du manifeste et
audit obligatoire du lot 15 sont donc vérifiés à nouveau. Une révocation, un lot
incohérent ou une panne d’audit empêche le téléchargement.

Le rapport frais remplace l’affichage et peut différer du précédent si la
configuration/les données ont changé. Les paramètres sont ceux du rapport qui a
créé le bouton, pas ceux de champs modifiés depuis. Les protections de requête,
session et génération empêchent l’usage d’un ancien bouton après remplacement
ou navigation. Aucune nouvelle route HTTP ou commande CLI n’est ajoutée.

## Fichier et portée

Le navigateur reçoit une demande de téléchargement de
`uniocr-revue-non-validee.json`, UTF-8, type JSON. L’enveloppe contient :

- `schema_version="1"`, `type_export="rapport_revue_documentaire_non_valide"` ;
- `lecture_seule=true`, `publication_active=false`, `validation_juridique="non_validee"` ;
- `perimetre="rapport_ou_page_uniquement_pas_corpus_complet"` ;
- `horodatage_client_non_certifie` : heure du navigateur, pas horodatage de confiance ;
- `requete_relative` : route et paramètres relus, sans en-tête d’authentification ;
- `resultat` : rapport frais avec sa provenance, ses marqueurs, avertissements et
  empreintes lorsqu’ils figurent dans le rapport du service.

Aucun jeton n’est copié depuis les en-têtes/session. Les valeurs documentaires et
paramètres peuvent néanmoins être sensibles : textes, recherches, codes, acteurs
ou identifiants présents dans les sources doivent être protégés selon la politique
du déploiement. Ne pas diffuser le fichier comme une publication officielle.
La liste de registre seule n’offre pas d’export de prétendu corpus contrôlé.

Les pages de recherche, relations, mesures, enfants et fragments restent **partiels**
avec leurs compteurs/décalages. Aucune pagination automatique, concaténation globale,
collecte de tous les lots ou téléchargement d’originaux/PDF. Ce fichier n’est pas
une sauvegarde/reprise de quarantaine ; utiliser le guide du lot 7 pour cela.

## Contrôle local après téléchargement (lot 17)

[CLI et schéma de contrôle](CONTROLE_EXPORT_REVUE.md) : contrôle de structure
sans import, comparaison aux archives ou authentification du fichier. Un code 0
ne certifie ni son origine, ni sa remise, ni sa validité réglementaire.

## Audit, stockage et limites

La relecture est auditée sous son opération existante. Il n’y a pas de nouvel
événement certifiant la remise du fichier, ni d’accusé de téléchargement : un
audit 200 peut précéder un échec navigateur ou un refus d’enregistrement local.
Le navigateur choisit son répertoire et sa gestion des collisions de noms ; aucun
fichier serveur ou archive existante n’est écrit/écrasé par cet export.

Taille du Blob JSON limitée à **10 Mio** ; un rapport plus grand est refusé. Ce
n’est pas une garantie globale de mémoire : le rapport/JSON sont déjà construits
avant le contrôle. L’URL objet temporaire est révoquée après la demande de
téléchargement. Pas de localStorage, nouveau cache API, chiffrement, signature,
preuve d’authenticité, WORM ou retrait d’un fichier déjà enregistré par l’utilisateur.
La coque service worker passe à v49 depuis le lot 22. Politique navigateur, protections de poste,
rétention et partage des fichiers restent à qualifier. JSDOM vérifie le contenu
et l’initiation, pas la boîte de dialogue/téléchargement réel dans tous les navigateurs.

[Rapport et qualification](RAPPORT_LOT16.md). Le corpus officiel et sa validation
humaine restent nécessaires ; aucun calcul réglementaire n’est autorisé.


[Lot 22 : export JSON du fragment de texte natif PDF](INTERFACE_PDF.md), après
relecture protégée. Pas d’export du binaire PDF ou de toutes ses pages.

Lot 25 : `/lots/{lot_id}/article-diff` est également admise dans l’enveloppe
partielle version 1 ; comparaison littérale et provenance déclarée seulement,
jamais consolidation ou validation juridique. Les anciens contrôleurs stricts
peuvent refuser cette nouvelle route.

Lot 26 : `/lots/{lot_id}/code-tree` est admise dans l’enveloppe partielle
version 1 ; navigation des chemins transcrits uniquement, pas hiérarchie
juridique validée. Les anciens contrôleurs stricts peuvent refuser cette route.

Lot 27 : `/lots/{lot_id}/article-pdf-match` est admise dans l’enveloppe partielle
version 1. Constat littéral d’un fragment seulement, sans attestation humaine.
Les anciens contrôleurs stricts peuvent refuser cette nouvelle route.

Lot 28 : `/api/v1/customs-review/article-diff` (hors chemin de lot) est admise
avec provenance double `archives.avant/apres`, comme `/diff`. La route intra-lot
`/lots/{lot_id}/article-diff` conserve une provenance simple. Une provenance
ambiguë est refusée ; anciens contrôleurs stricts susceptibles de refuser l’ajout.
