# Pistes documentaires dans la revue administrative — lot 60

## Usage explicite

Dans la revue douanière existante, choisir un lot Tarif, saisir au moins un
critère textuel puis utiliser **Explorer les pistes documentaires partielles**.
Les champs de critères/mode/préfixe/pagination sont communs avec la recherche
stricte, mais les boutons/routes restent **distincts**. Un résultat AND vide ne
lance aucune recherche partielle automatiquement. Préfixe seul refusé pour pistes.
Les outils sont désactivés pour Code et mesures autonomes.

Le panneau présente rang documentaire, nombres de critères complets et de paires
retrouvées, statut partiel ou conjonction littérale complète, termes non retrouvés
par critère. Il explique que les compteurs ne sont ni indépendants ni probabilités,
et ne déduit ni attribut manquant, ni absence de droit. Extraits FR/AR originaux
et positions Unicode réutilisent le rendu textuel borné existant (16 par ligne).
Libellés/termes hostiles restent du texte via textContent, pas HTML ni lien source.

Une fiche documentaire exacte peut être ouverte **par clic**, jamais sélectionnée
comme classement du produit. La page suivante restaure critères, préfixe, mode et
limite du rapport reçu, pas des champs éventuellement modifiés depuis. Le rang
continue avant pagination. Aucun candidat, taux, publication ou décision humaine
n'est produit automatiquement.

## Contrôles de restitution

Les actions spécifiques exigent drapeaux non validés, politique de tri connue,
filtres/types/bornes, termes normalisés, cohérence des critères complets/paires et
termes non retrouvés, rangs, codes uniques et ordre des lignes de la page. Les
extraits doivent correspondre au texte original et aux champs déclarés retrouvés.
Une réponse incohérente ne génère ni panneau spécifique, ni fiche, ni pagination
ou extrait de piste. Le JSON brut reste une restitution technique non validée ;
ce contrôle UI n'est ni signature, ni attestation de pertinence, ni validation de
la recherche côté serveur. Il ne démontre pas l'ordre des lignes hors de la page.

Changement de lot/compte/écran, requête plus récente et saisie invalide invalident
les anciennes suites de navigation. Une réponse tardive n'est pas affichée.
401/403/503 retirent les outils et anciens résultats via le mécanisme commun.
Les autres échecs d'une lecture effacent aussi l'ancien résultat et ses actions.

## Export et données

L'export existant **relit la même route autorisée/auditée** avant de créer le Blob
JSON. Un audit indisponible ne produit pas de fichier et efface les outils. Format
v1, limites de taille, marqueurs et horodatage client non certifié inchangés.
Chaque nouveau rapport UI de pistes a été contrôlé et rejoué contre son archive
explicitement fournie avec empreintes attendues de test ; pas preuve d'origine,
identité humaine ou audit serveur revérifiés par le rejeu.

Aucun résultat d'API n'est stocké dans le cache du service worker. Seule la version
de la coquille passe à `unocr-shell-v70-documentary-leads` pour renouveler le module.
Pas nouveau stockage documentaire navigateur persistant, endpoint, token de test,
réviseur, corpus ou publication de production créés.

## Recette et limites

26 scénarios JSDOM supplémentaires (212 au total) et quatre parcours UI/HTTP/API
réels enrichis : pagination de pistes, export relu, contrôle de structure et rejeu
intégral. Cela reste **JSDOM et TestClient sur fixtures NON OFFICIELLES**, pas
qualification d'un navigateur réel, accessibilité complète, charge nationale ou
classement métier. Le front n'a pas de moteur IA ou de raisonnement RGI.

L'aperçu a été redémarré pour charger les routes récentes. Smoke HTTP local avec
Host de type e2b : coquille/module/SW/OpenAPI 200, route pistes présente, accès
anonyme 403. Aucun contournement de RBAC ni lot fictif injecté dans la production.
