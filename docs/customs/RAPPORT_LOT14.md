# Avancement — lot 14 : navigation assistée de la revue documentaire

**2026-11-06 — raccourcis de lecture seulement, aucune relation juridique inférée.**

## Audit et livraison

Inspection préalable de la coque de revue, des identifiants/plages retournés par
recherche/historique/arbre/lecture, et des tests JSDOM/HTTP existants. Les handlers
fiche/arbre/article ont été réutilisés et nommés, sans nouvelle API ou logique
métier dans le navigateur. Les données de quarantaine ne sont pas dupliquées.

- Résultat Code → lecture de l’ID de version exact, texte intégral déclaré.
- Historique → lecture des versions et du contexte de relations sans doublon d’ID,
  y compris une disposition modificative dont le numéro diffère de celui de la cible.
- Résultat tarifaire ou feuille de l’arbre → fiche documentaire du code10 reçu.
- Arbre → enfants directs du parent reçu au niveau suivant cohérent, puis fiche.
- Page suivante des enfants et fragment suivant d’article : reprise des paramètres
  du rapport, avec décalage serveur validé. Pas de calcul d’offset Unicode via la
  longueur UTF-16 de JavaScript.
- Zone d’actions texte, styles du design system, garde de génération/requête/lot
  et contrôle de session. Anciens boutons détachés inertes après remplacement.
  Effacement des actions avec le résultat ; jamais d’URL de source suivie.
- Coque service worker v46 ; pas de nouvelle persistance métier ni cache API.

[Guide et limites](NAVIGATION_ASSISTEE.md). Les formulaires et rapports JSON
restent accessibles : ce n’est pas encore un arbre graphique complet à fil d’Ariane.
Les boutons ne certifient ni les relations, ni les sources ou l’applicabilité.

## Qualification

**754 tests Python réussis, 1 avertissement Starlette/httpx**, data/logs isolés :
**même sélection que le lot 13**, dont le test d’intégration UI/API est étendu.
Aucun nouveau cas Python n’est revendiqué pour une modification d’interface ;
la commande complète demeure celle du [rapport lot 13](RAPPORT_LOT13.md).
Pas de suite complète du dépôt annoncée.

**36 scénarios JSDOM réussis**, soit 28 précédents + 8 nouveaux :

1. lien de recherche Code vers ID exact contenant caractères spéciaux, sans URL externe ;
2. liens d’historique et contexte sans doublons ;
3. lien tarifaire vers fiche avec zéros initiaux ;
4. descente par enfant déclaré et page suivante ;
5. fragment suivant avec identité/champ/plage du rapport et points de code Unicode ;
6. effacement et inertie d’un ancien bouton après changement de lot ;
7. décalage invalide ou niveau suivant incohérent sans bouton de navigation ;
8. changement de jeton refusé avant nouvel appel réseau.

```sh
npm run ui:customs-review
# Avec UNOCR_DATA_DIR et UNOCR_LOG_DIR temporaires avant l’import de l’API :
python -m pytest tests/test_customs_review_ui.py -q
```

Le parcours JSDOM → HTTP → véritable middleware/API, sur magasin temporaire,
est étendu : recherche → version ; historique → disposition modificative ;
lecture → fragment suivant ; sections → chapitres → positions → SH6 → codes10 →
fiche. Les comptes/lots sont des fixtures NON OFFICIELLES temporaires, sans réponse
métier simulée dans ce parcours. Les instantanés du corpus de test sont inchangés.
Aucun compte, registre ou lot de production créé pour afficher une démonstration.

Ruff, syntaxe JavaScript et `git diff --check` passent. Prévisualisation existante
contrôlée : coque/module/service worker 200 avec hôte de prévisualisation, revue
anonyme 403. Fichiers statiques servis directement, aucun redémarrage backend
nécessaire. Empreintes historiques inchangées :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Corpus et mission restante

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, originaux/modifications exhaustifs, tarif
national courant et sources fiscales restent à acquérir et vérifier humainement.
Ni consolidation à date, validation humaine signée, publication, classification IA
ou calcul ajouté. Les deux calculs legacy non sourcés restent bloqués.

La sécurité autoritaire reste celle du serveur ; aucune protection contre poste
compromis ou retrait d’informations déjà lues/copiées. Qualification JSDOM/backend
isolé, pas homologation visuelle/accessibilité complète ou benchmark national.
Aucun usage réglementaire réel n’est autorisé par cette amélioration ergonomique.
