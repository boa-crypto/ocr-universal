# Sauvegarde/reprise de la quarantaine — lot 7

2026-11-06. **Copie technique locale, aucune publication ou validation juridique.**

## Choix de sécurité

Le mécanisme UniOCR existant inclut désormais `data/customs-quarantine`, mais
seulement avec l’option locale explicite `--include-customs-quarantine`.
Si ce dossier existe et que l’option manque, la sauvegarde est **refusée**, pas
silencieusement amputée des lots. Les routes HTTP legacy ne raccordent pas cette
option : elles ne peuvent pas créer ou restaurer une sauvegarde de quarantaine,
même si un appelant ajoute un champ homonyme au JSON. Cela évite de contourner
les habilitations strictes du lot 6 via le mode ouvert historique.

Il s’agit d’une sauvegarde du **magasin complet**, pas uniquement des lots : elle
peut contenir des jetons RBAC, clés et autres documents. Par défaut, l’option
choisit `data_dir/../sauvegardes-quarantaine`, distinct du répertoire de sauvegardes
legacy et de sa purge HTTP habituelle. Nouveau dossier demandé en mode 0700,
archive en mode 0600 ; effets réels des permissions dépendants de la plateforme.
Aucun chiffrement ou stockage WORM ajouté. Réserver l’accès au compte opérateur.

Un `--out` explicite reste possible ; choisir un emplacement protégé, hors du
répertoire soumis aux purges automatiques legacy. Les permissions d’un dossier
préexistant ne sont pas réécrites automatiquement. `--keep 0` désactive la purge
CLI ; une politique de rétention indépendante reste nécessaire.

## Commandes

Arrêter les écritures et les modifications manuelles de lots/registre pendant la
copie. Le verrou SQLite existant n’est **pas** un verrou transactionnel du corpus
sur le système de fichiers.

```sh
# Source : magasin effectif configuré ; inclusion explicite, sans purge :
PYTHONPATH=src python -m unocr.cli backup --include-customs-quarantine --keep 0

# Lister les copies de ce répertoire dédié :
PYTHONPATH=src python -m unocr.cli backups --dir /chemin/sauvegardes-quarantaine
```

Avant reprise : arrêter le service et choisir des répertoires **data et logs
neufs**. Ne pas pointer les journaux actifs : la restauration générale reste
celle du module existant pour les fichiers hors quarantaine.

```sh
UNOCR_DATA_DIR=/chemin/reprise-neuve/data UNOCR_LOG_DIR=/chemin/reprise-neuve/logs PYTHONPATH=src python -m unocr.cli restore /chemin/sauvegarde.zip --include-customs-quarantine
```

Les chemins ci-dessus sont des indications à remplacer, pas un nouveau magasin
créé dans le dépôt. Sans option, une archive contenant la quarantaine est refusée
avant écriture. Le code Python partage le même garde-fou :
`creer_sauvegarde(..., inclure_quarantaine=True)` et
`restaurer_sauvegarde(..., inclure_quarantaine=True)`.

## Ce qui est conservé et vérifié

Tous les fichiers de la quarantaine sont copiés : registre, manifeste, PDF,
transcription reçue, sidecar, lot normalisé et rapport. Les fichiers cachés et
`.tmp` y sont également conservés : une sauvegarde ne doit pas effacer les traces
d’une interruption ou réparer silencieusement une préparation incomplète.
Les liens symboliques directs/internes et fichiers spéciaux de ce dossier sont
refusés, de même que les membres ZIP marqués comme symlinks de quarantaine.

Chaque fichier reçoit une taille et un SHA256 dans le manifeste de sauvegarde.
L’archive est relue par `verifier_sauvegarde` **avant** de signaler la création
réussie. Deux sauvegardes dans la même seconde sont réservées en création
exclusive, avec suffixe distinct si nécessaire ; la précédente n’est pas écrasée.

Une reprise vérifie l’archive entière avant extraction. Si la cible contient déjà
`customs-quarantine` (même si l’archive est ancienne et n’en contient pas), la
reprise est refusée **même avec `--force`**. Aucun nettoyage ou déplacement
automatique de la cible. Les fichiers de quarantaine sont restaurés en création
exclusive dans un nouveau dossier demandé en mode 0700. Les autres fichiers du
magasin conservent les règles de restauration legacy ; utiliser un magasin neuf.

Les octets et empreintes des manifestes de lot sont conservés : les épingles du
registre restent vérifiables après déplacement. Les dates mtime, inodes, ACL et
propriétés système complètes ne sont pas garantis identiques.

## Après reprise

1. Contrôler chaque lot avec `customs-code-check` ou le lecteur tarifaire existant.
2. Vérifier le registre et ses empreintes de manifeste ; garder les versions
   non validées en quarantaine.
3. Relire le RBAC restauré avant de redémarrer le serveur sur ces nouveaux chemins.
4. Vérifier la revue administrative avec les habilitations nominatives effectives.

Une préparation incomplète peut être sauvegardée et restaurée **telle quelle** ;
son lecteur continue de la refuser. L’intégrité du ZIP n’est pas une preuve de
cohérence des lots, d’authenticité du PDF, de correspondance transcription/PDF ou
d’applicabilité juridique. Aucun compteur de fichiers ne prouve une complétude
réglementaire. Aucun texte, taux, statut de validation ou compte n’est inventé.

## Limites de reprise

Pas de garantie de panne électrique, fsync, transaction multi-fichiers ou reprise
exactly-once. Un échec de copie/extraction peut laisser une archive ou un magasin
partiel : conserver pour inspection et repartir vers une cible neuve. Une archive
non validée n’est pas une sauvegarde exploitable, même si son nom apparaît dans
une liste. Pas d’effacement automatique des traces d’échec.

La sauvegarde vérifie ses octets, pas un instantané global de tous les fichiers
face à un écrivain concurrent hostile. Suspendre les écritures pendant les
opérations. Tester périodiquement la reprise sur un environnement isolé ; la
qualification par fixtures ne remplace pas un exercice sur les fichiers officiels
réels et sur les supports de stockage du déploiement.
