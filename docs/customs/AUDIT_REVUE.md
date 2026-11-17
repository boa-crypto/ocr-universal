# Audit des succès de revue — lot 15

2026-11-06. **Écriture locale exigée avant réponse, pas journal WORM ou signature juridique.**

## Changement de frontière

Auparavant, le journal d’audit existant était best-effort, y compris pour les
lectures réussies de quarantaine. Désormais, toutes les réponses métier réussies
du routeur `/api/v1/customs-review` exigent un événement écrit puis un appel local
`fsync` réussi avant remise de la réponse. La réponse JSON est d’abord sérialisée,
puis l’événement est écrit ; un défaut de sérialisation n’enregistre pas un succès.

Si cette écriture/synchronisation échoue : **503**, code
`audit_revue_indisponible`, `Cache-Control: no-store`, aucun `resultat` documentaire.
L’écran mentionne l’indisponibilité du registre ou de l’audit, efface résultats,
fragments/actions et demande une intervention serveur. Aucun corps d’erreur interne
ou chemin du journal n’est affiché.

Périmètre : liste, contrôle, recherche, historique, fiche tarifaire, navigation,
diagnostic, lecture d’article et comparaison. Les commandes CLI de lecture ne
passent pas par ce routeur et ne reçoivent pas cette garantie nouvelle.

## Événement et données exclues

Le journal JSONL reste `<log_dir>/audit.log`, partagé avec l’audit existant.
Événement `revue_douaniere`, horodatage local, acteur nominatif, opération, IDs des
lots, statut et, sur succès, `manifestes` : dictionnaire ID → SHA256 épinglé et
comparé au manifeste effectivement utilisé par le lecteur.

La liste seule ne contrôle pas les contenus des lots : son `manifestes={}` ne
devient pas une preuve d’intégrité de leurs archives. Les autres opérations
conservent leurs contrôles de lots et épingles avant audit.

Aucun jeton, requête de recherche, ID/numéro d’article, code tarifaire, texte ou
corps de document n’est ajouté à cet événement métier. Les logs HTTP/proxy peuvent
contenir les URL et leurs paramètres : leur rétention reste à configurer.

## Mécanisme et protection limitée

`audit_obligatoire` est distinct de `audit`, dont le comportement legacy reste
inchangé. Sous verrou thread local, il crée si nécessaire le dossier (mode 0700
demandé), ouvre en ajout sans troncature le journal (0600 demandé si nouveau),
vérifie un fichier régulier sans lien multiple et une fin de fichier terminée
par saut de ligne, écrit un événement UTF-8 en une opération, contrôle sa longueur,
puis appelle `fsync`. Taille d’événement limitée à 16 Kio. Symlinks directs du
dossier/journal, fichiers spéciaux, liens physiques multiples et fin interrompue
sont refusés. `O_NOFOLLOW`/`O_NONBLOCK` sont utilisés lorsqu’ils existent.

La vérification de fin exige la lecture du journal en plus du droit d’ajout ;
un journal seulement inscriptible peut donc rendre la revue indisponible.
Les permissions d’un journal/dossier existant ne sont **pas** réinitialisées.
Les composants ancêtres, ACL et droits de l’opérateur doivent être sécurisés au
déploiement. Le verrou ne coordonne que ce writer strict dans le même processus,
pas les writers legacy, autres processus, rotations ou un écrivain hostile.
Il ne valide pas rétroactivement tout le JSONL historique.

Un événement refusé ne provoque aucun nettoyage automatique : écriture partielle,
échec de `fsync`/fermeture ou panne peuvent laisser un fragment ou un événement déjà
présent. La prochaine tentative refuse une fin interrompue. **Ne pas tronquer ou
supprimer automatiquement le journal** : sauvegarder et investiguer hors service,
avec une procédure approuvée de rotation/rétention. Aucun outil de réparation
silencieuse n’est livré.

## Refus, disponibilité et sémantique

Les refus d’accès/lot/paramètres conservent leur statut 401/403/404/409/422/503
même si leur tentative d’audit échoue. L’authentification/middleware et les événements
`revue_douaniere_acces_refuse` restent best-effort. L’objectif est de ne pas
**libérer un résultat documentaire réussi sans audit**, pas de prétendre tracer
exhaustivement chaque attaque ou échec. Une panne d’audit peut donc rendre la
revue indisponible alors que les lots sont cohérents : surveiller l’espace disque,
les permissions, latences et politiques de rotation.

Le statut de succès dans un événement n’est pas un accusé de livraison réseau.
Après écriture, un échec tardif peut laisser un événement avec statut 200 mais
une réponse 503 ou non reçue. Les retries peuvent produire plusieurs événements.
Pas de transaction globale lot/journal/réseau, exactly-once, garantie matérielle de
panne électrique, synchronisation du répertoire parent, signature, horodatage de
confiance, registre inaltérable ou WORM. Les administrateurs OS restent capables
de réécrire le journal. Cette amélioration n’est pas une validation humaine/juridique.

[Qualification et limites](RAPPORT_LOT15.md). Aucun corpus officiel acquis ou publié.


Lot 21 : la lecture native PDF est aussi soumise au contrat de succès obligatoire
(opération `lecture_pdf`), avec tests API sur PDF ReportLab NON OFFICIELS. Aucun
fragment PDF/document_id/page n’est ajouté à l’événement métier de succès.
