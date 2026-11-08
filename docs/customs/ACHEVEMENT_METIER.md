# Achèvement des fonctions métier — suivi explicite

Le lot94 recentre les travaux sur les fonctions métier. Il ne signifie pas que
l'ensemble de la mission est achevé. Aucun pourcentage déduit des tests/lots.

| Fonction | État vérifiable après95 | Reste pour clôturer |
|---|---|---|
| Fiche produit et questions | API et UI explicite, champs déclarés et informations non renseignées | Justificatifs techniques rattachés au dossier et qualification opérateur |
| Pistes et comparaison documentaire | Moteur littéral FR/AR existant, snapshot attaché à chaque révision | Synonymes/ontologie métier sourcés, comparaison technique discriminante |
| Raisonnement de classement | Proposition humaine structurée, RGI/notes/exclusions déclarés et référence candidate exigée | Moteur RGI/notes, liens réellement prouvés, citations juridiques contrôlées ; pas IA livrée |
| Revue humaine | États et UI de revue/réouverture, historique SQLite/CAS, outbox de versions récupérable et sauvegarde SQLite | Séparation des responsabilités, sécurité/exploitation et réception de reprise réelle ; append externe au moins une fois, pas transaction distribuée |
| Droit applicable à date | Versions/documentation déjà disponibles en quarantaine | Consolidation, conflits, abrogations et règles d'effet juridiquement qualifiés |
| Relations transversales | Relations déclarées et lectures documentaires existantes | Preuves entre articles/codes/notes/mesures/régimes/procédures |
| Publication/retrait | Toujours interdit dans ce périmètre | Registre de confiance, actes humains habilités et mécanisme contrôlé, sans transformer les données non validées en droit |
| API métier centrales | Revue et dossiers94 disponibles | Contrats de référentiel validé, connexion réelle autorisée, intégration transit/marchandises/facturation |
| Sources et fiscalité | Modèles/imports et contrôles locaux | Corpus officiel exhaustif FR/AR, tarif national10, mesures et droit à date validés |
| Réception | Recettes techniques isolées et natives | Déploiement maîtrisé, RBAC effectif, cas métier réels, navigateurs, charge et réception habilitée |

Le lot95 livre ensemble l'UI, la réconciliation outbox des versions et la
sauvegarde SQLite du dossier, avec tests intégrés. Voir
[le contrat d'exploitation](INTERFACE_ET_AUDIT_DOSSIERS.md). Il ne clôt pas les
autres lignes : leur développement/qualification demeure explicitement ouvert.

## Dépendances et blocages de la mission complète

- **Corpus et fiscalité officiels** : aucun nouvel original reçu/validé. Les
  accès réseau de cet environnement n'autorisent pas les sites des autorités
  douanières et du journal officiel. Inventer un corpus depuis des fixtures
  n'est pas une solution. Fourniture d'originaux FR/AR, versions, provenance,
  droits de réutilisation et validation par responsables habilités nécessaires.
- **Ontologie, IA, RGI et droit à date** : fonctionnalités non achevées. Les
  fixtures et modèles ne définissent pas les synonymes admissibles, preuves,
  règles d'effet, exceptions et protocole de qualification. Il reste du
  développement possible sur contrats/fixtures ; cela ne doit pas être présenté
  comme une impossibilité purement technique ni comme une livraison réalisée.
  L'activation métier exige ces règles et une évaluation habilitée, absentes.
- **Responsabilités/publication** : aucune politique nominative à deux personnes,
  acte d'approbation ni autorisation de publication des sources non validées.
  Ne pas les remplacer par un bouton de publication sans gouvernance.
- **Intégration centrale et justificatifs techniques** : rattachement sécurisé
  des pièces et contrats d'intégration transit/marchandises/facturation encore
  non livrés pour ces dossiers. Les systèmes cibles, périmètres et comptes
  autorisés ne sont pas fournis ; les API de quarantaine ne les remplacent pas.
- **Exploitation** : pas de redémarrage de l'aperçu partagé/backend76 pendant
  ses traitements, ni de publication/déploiement ou restauration irréversible.
  RBAC effectif, sauvegarde/reprise réelle, navigateurs, charge et réception
  métier restent des conditions de mise en service.

Ce registre distingue les réalisations testées, le développement restant et les
prérequis externes. La campagne ne peut pas être déclarée achevée fiscalement
ou juridiquement à partir des seuls tests locaux.

**0 nouvel original officiel, 0 article/code officiellement validé, 0 publication
active** au titre de cette campagne. Les sources et scénarios de tests ne sont
pas des données de production. Aperçu backend76 conservé, pas déploiement implicite.
