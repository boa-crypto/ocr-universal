# Pièces techniques textuelles des dossiers de proposition

## Périmètre et invariants

Extension additive des dossiers94/95, uniquement en quarantaine. Une pièce est
un **texte UTF8 déclaré**, pas un PDF original authentifié, une expertise ni une
validation juridique. Aucun téléchargement distant, chemin de fichier serveur,
HTML exécutable, OCR de pièce ou calcul fiscal n'est introduit.

Chaque pièce contient : `piece_id`, `nom`, `nature`, `criteres_declares`,
`localisateur_declare`, `texte`, éventuellement `declarations_attributs`. Le
serveur ajoute format, SHA256 du texte encodé UTF8, nombre d'octets, auteur
nominatif et horodatage. `verification` reste `non_verifiee`. Ni auteur, ni SHA,
ni statut de vérification ne sont acceptés depuis le client.

Les critères associés sont déclaratifs : la présence d'une notice ne remplit
pas un champ produit et ne supprime aucune question de complétude. Les pistes
restent littérales FR/AR ; aucune extraction d'attribut ou IA n'est revendiquée.

## Citations d'attributs

Une déclaration facultative contient critère, valeur attribuée humainement,
`debut`, `fin` et `citation`. Le serveur exige :

- critère effectivement associé à cette pièce, au plus une déclaration par
  critère et cinq par pièce ;
- indices en **points de code Unicode Python**, début inclus/fin exclue, bornés
  au texte reçu ;
- égalité exacte `texte[debut:fin] == citation`, maximum4096 points de code.

L'interface convertit les indices UTF16 de la sélection en points Unicode.
Modifier le texte, le critère ou la valeur invalide la sélection locale. Cette
vérification prouve seulement que la citation figure dans la copie textuelle
conservée ; elle ne prouve ni l'original, ni la vérité de la valeur, ni le lien
physique au produit. Elle ne résout pas les négations, contradictions ou RGI.

## API et versionnement

- POST `/api/v1/customs-review/lots/{lot}/assessments` accepte
  `pieces_techniques` (liste facultative, vide par défaut).
- PATCH `/api/v1/customs-review/lots/{lot}/assessments/{id}` : champ omis/null =
  conserver ; liste fournie = remplacement complet explicite ; `[]` = retrait
  dans la nouvelle version, **sans effacer les versions antérieures**.
- Même CAS `version_attendue`, RBAC/allowlist, validation de source et outbox que
  pour le produit. Pièces et état sont commis dans une même transaction SQLite.
- En état proposition humaine ou rejet, les pièces ne peuvent pas changer
  pendant la réouverture : rouvrir d'abord, puis modifier dans une autre révision.
- GET sans `version` renvoie l'état courant et l'historique sommaire. Les anciens
  textes/citations ne sont pas répétés dans tous les sommaires.
- GET `...?version=N` renvoie le contenu exact de cette version, toujours après
  autorisation et revalidation de l'archive courante épinglée. Version absente404,
  borne hors1–100 ou valeur non entière422. Ce GET réconcilie aussi l'outbox.

Les dossiers94/95 sans champ de pièces restent lisibles sans réécriture de leur
contenu. Leur révision crée une version au nouveau format. Aucune migration
forcée ou suppression de base réelle n'a été effectuée.

## Interface opérateur

Saisie/collage du texte, ou lecture **locale** d'un fichier `.txt` UTF8 strict.
L'import local n'ajoute ni n'enregistre automatiquement la pièce : renseigner
identifiant, nature, critère et localisateur, éventuellement sélectionner une
citation et sa valeur déclarée, puis **Ajouter au brouillon local**. Créer ou
réviser explicitement le dossier pour sauvegarder.

Le retrait est également local jusqu'à la révision. Recharger un dossier
remplace le brouillon local ; changer de lot le remet à zéro. Les textes sont
rendus par `textContent`, sans interprétation HTML ni stockage navigateur du
contenu. Les téléchargements de sources externes ne sont pas autorisés.

La lecture d'une version ancienne désactive les écritures UI. Recharger la
version courante pour reprendre la revue ; le serveur CAS reste l'autorité.

L'import peut enlever un BOM UTF8 lors du décodage navigateur : **l'empreinte
porte sur le texte conservé**, pas sur les octets du fichier d'origine. Pas de
signature, scan antivirus, preuve de réception de l'original ni PDF binaire.

## Bornes, confidentialité, reprise

Cinq pièces par version ; identifiants uniques et simples ; nom simple sans
chemin ; texte limité à16384 points Unicode et32768 octets UTF8 par pièce ;
contrôles interdits hors tabulation/retours de ligne. Le plafond512Kio de l'état
complet et100 versions reste applicable ; les anciennes versions augmentent
la taille globale de la base. Aucun quota global de dossiers n'est introduit.

Les versions historiques contiennent les textes retirés : ce n'est pas un
mécanisme d'effacement de données personnelles. Ne joindre que le nécessaire,
selon une politique de conservation à établir par l'exploitant. SQLite n'est
pas chiffré par cette extension. Les journaux outbox ne dupliquent ni texte ni
citation, seulement les identités et l'empreinte de l'état complet.

La sauvegarde95 conserve les pièces et sorties d'audit en attente dans le même
instantané SQLite. Reprise vérifiée sur cible neuve avec une panne de livraison
simulée ; aucune reprise du magasin réel. Les limites d'atomicité distribuée,
d'archivage probant et d'exploitation du contrat95 restent inchangées.

## Hors périmètre

PDF/images/binaire, pièces originales signées, vérification par expert,
comparaison technique sémantique, ontologie, moteur RGI/droit à date, publication
et intégration aux systèmes centraux ne sont pas livrés par cette extension.

## Permissions du stockage local

Avant ouverture SQLite, création en0600 et restriction des bases existantes
à0600 sur POSIX, sans changer leur contenu ; même contrôle des sidecars présents.
Fichiers réguliers, lien unique et propriétaire du processus exigés ; liens
symboliques et FIFO refusés. Ouverture non bloquante et `O_NOFOLLOW` lorsque
le système les fournit. Les journaux supprimés concurremment par SQLite sont
ignorés après ouverture s'ils n'ont plus de lien.

Ces contrôles ne protègent pas contre un autre processus hostile du **même
compte système**, une substitution d'ancêtre du chemin ou le propriétaire du
support ; isoler le compte de service et protéger toute l'arborescence. Les
permissions POSIX ne valent pas une qualification des ACL Windows. Aucune
base métier réelle n'a été ouverte par cette campagne pour modifier ses modes.
