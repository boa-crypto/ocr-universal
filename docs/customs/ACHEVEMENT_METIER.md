# Achèvement des fonctions métier — suivi explicite

Le lot94 recentre les travaux sur les fonctions métier. Il ne signifie pas que
l'ensemble de la mission est achevé. Aucun pourcentage déduit des tests/lots.

| Fonction | État vérifiable après94 | Reste pour clôturer |
|---|---|---|
| Fiche produit et questions | API persistante, champs déclarés et informations non renseignées | UI de saisie, justificatifs techniques et qualification opérateur |
| Pistes et comparaison documentaire | Moteur littéral FR/AR existant, snapshot attaché à chaque révision | Synonymes/ontologie métier sourcés, comparaison technique discriminante |
| Raisonnement de classement | Proposition humaine structurée, RGI/notes/exclusions déclarés et référence candidate exigée | Moteur RGI/notes, liens réellement prouvés, citations juridiques contrôlées ; pas IA livrée |
| Revue humaine | États brouillon/revue/complétion/proposition/rejet/réouverture, historique SQLite, CAS | UI, séparation des responsabilités, audit externe transactionnel/réconciliation outbox, sauvegarde et sécurité opérationnelle |
| Droit applicable à date | Versions/documentation déjà disponibles en quarantaine | Consolidation, conflits, abrogations et règles d'effet juridiquement qualifiés |
| Relations transversales | Relations déclarées et lectures documentaires existantes | Preuves entre articles/codes/notes/mesures/régimes/procédures |
| Publication/retrait | Toujours interdit dans ce périmètre | Registre de confiance, actes humains habilités et mécanisme contrôlé, sans transformer les données non validées en droit |
| API métier centrales | Revue et dossiers94 disponibles | Contrats de référentiel validé, connexion réelle autorisée, intégration transit/marchandises/facturation |
| Sources et fiscalité | Modèles/imports et contrôles locaux | Corpus officiel exhaustif FR/AR, tarif national10, mesures et droit à date validés |
| Réception | Recettes techniques isolées et natives | Déploiement maîtrisé, RBAC effectif, cas métier réels, navigateurs, charge et réception habilitée |

Certaines tâches sont du développement sans dépendance à de nouveaux originaux
(UI, outbox/réconciliation, contrats et moteurs sur fixtures). Leur livraison ne
prouvera pas la fidélité/applicabilité des sources ; ces vérifications externes
et humaines restent nécessaires avant exploitation fiscale.

**0 nouvel original officiel, 0 article/code officiellement validé, 0 publication
active** au titre de cette campagne. Les sources et scénarios de tests ne sont
pas des données de production. Aperçu backend76 conservé, pas déploiement implicite.
