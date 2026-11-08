# Dossiers métier : interface, audit récupérable et sauvegarde

## Périmètre

Extension des dossiers de proposition tarifaire94 dans l'administration UniOCR
existante. Aucun classement automatique, validation juridique ou publication.
Les lots de quarantaine restent non validés. Le moteur de candidats est littéral
FR/AR : ce n'est pas une IA, une ontologie ou une expertise technique.

## Parcours opérateur

1. Ouvrir la revue douanière avec un compte nominatif autorisé et choisir un lot
   de type `tarif`. Le type vient du registre, pas du libellé du lot.
2. Saisir un identifiant simple et les cinq caractéristiques déclarées ; cliquer
   explicitement sur **Créer le brouillon**. Aucun enregistrement au chargement.
3. Charger/réconcilier un dossier existant par son identifiant. L'identifiant
   n'est pas un secret et ne remplace jamais l'autorisation serveur.
4. Examiner les questions, candidats, correspondances littérales, extraits et
   références déclarées, ainsi que l'historique. Une référence reçue n'est pas
   une preuve d'authenticité de l'original.
5. Motiver une transition. Pour une proposition humaine, choisir explicitement
   un candidat et déclarer raisonnement RGI et notes/exclusions. Le serveur
   contrôle la complétude et la référence ; il ne vérifie pas la justesse juridique.
6. Une proposition ou un rejet doit être rouvert avant modification du produit.
   Les transitions interdites restent refusées par le serveur.

Les données sont affichées comme texte, sans interprétation HTML, et ne sont pas
stockées par ce composant dans le navigateur. Le jeton existant est utilisé en
mémoire/session selon l'architecture existante. Les requêtes sont same-origin,
no-store ; le service worker ne met pas les API en cache. Changer de lot remet
le formulaire à zéro. Une réponse tardive après changement de contexte est
ignorée. Un changement de compte invalide le composant au prochain appel ; le
parent reste responsable de retirer la vue lors de la navigation/déconnexion.

Pas de liste/recherche globale des dossiers ni traduction IA dans cette extension95.
L’extension96 ajoute des pièces textuelles et la lecture des anciennes versions :
voir [son contrat](PIECES_TECHNIQUES_DOSSIERS.md). Les modules historiques de justificatifs ne sont pas
implicitement rattachés aux dossiers tarifaires.

## Conflit, panne et réconciliation

- 409 : aucune répétition automatique ; recharger avant nouvelle révision.
- 503 ou panne réseau : sauvegarde éventuellement déjà commise. Recharger le
  même identifiant après rétablissement, ne pas rejouer aveuglément l'écriture.
- 401/403 : suppression des champs et actions du composant.
- Les révisions utilisent exclusivement la version renvoyée par le serveur.
  Les doubles clics ne lancent pas une seconde requête simultanée.

## Outbox des versions

La table SQLite `sorties_audit` est alimentée dans la **même transaction** que
l'état et la version. Chaque événement contient un identifiant stable SHA256,
l'identité du dossier/lot/version/source, l'auteur initial, l'état et l'empreinte
du contenu. Les caractéristiques et motivations ne sont pas dupliquées dans
cette sortie ; elles restent dans l'historique de versions existant.

Après une écriture, et lors d'une lecture HTTP autorisée, le serveur livre les
sorties de ce dossier au journal obligatoire, puis acquitte dans SQLite. Le
verrou transactionnel sérialise deux livreurs. Pas de daemon, de retry automatique
réseau, ni de parcours global de dossiers sans nouvelle autorisation.

Les versions94 sont reprises paresseusement, après contrôle de leurs traces,
sans réécrire états/historique. Elles peuvent générer de nouveaux événements
pour des opérations déjà auditées dans le format historique. Les journaux
existants ne sont jamais effacés ni dédupliqués.

**Garantie : au moins une livraison récupérable, pas exactly-once.** Un arrêt
après append mais avant acquittement peut produire deux lignes avec le même
`evenement_id`. Le résumé HTTP historique reste distinct de ces événements :
une panne de son append peut encore donner503 après commit, même si toutes les
versions sont déjà livrées. Le GET suivant permet la relecture/réconciliation.
L'outbox ne rend pas le fichier et SQLite atomiques ensemble, ne garantit ni
WORM, ni signature, ni résistance à l'administrateur du disque. Son indicateur
de livraison n'est pas une preuve indépendante de présence actuelle du journal.

## Sauvegarde et reprise

La sauvegarde CLI avec option explicite de quarantaine utilise maintenant l'API
SQLite backup pour `data/customs-quarantine/dossiers_metier.sqlite3`, puis
`quick_check`. Elle conserve l'outbox (y compris les sorties en attente) et
n'archive pas ses fichiers WAL/SHM/journal qui pourraient rejouer un état ancien
sur l'instantané. Un journal orphelin est refusé. Le contrôle du manifeste et le
refus de fusionner une quarantaine cible existante restent inchangés.

Les lots, le registre, le journal externe et SQLite ne constituent pas un
instantané distribué unique. La reprise doit se faire sur une cible neuve,
avec vérification des épingles et habilitations avant réconciliation. Pas de
restauration ni de sauvegarde des données réelles effectuée par cette campagne.
Un registre situé hors de l'arborescence standard exige une procédure opérateur
adaptée ; l'extension ne prétend pas sauvegarder un chemin externe arbitraire.

## Recette reproductible

- `npm run ui:customs-assessments` : scénarios JSDOM simulés, non officiels.
- `python -m pytest tests/test_customs_assessments_ui.py -q` : même composant
  sur API réelle via pont HTTP isolé, création/révision/relecture.
- `python -m pytest tests/test_customs_assessment.py tests/test_customs_backup.py tests/test_backup.py -q` : métier, audit, concurrence et reprise SQLite.

JSDOM et fixtures HTTP ne remplacent pas une réception en navigateur réel,
l'accessibilité, les tests de charge, les cas métier habilités et le déploiement.
