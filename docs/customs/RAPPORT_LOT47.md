# Rapport lot 47 — localisations et extraits des critères tarifaires

7 novembre 2026, branche `arena/2cd4c91a-ocr-universal`.

## Livré

- Positions originales de **chaque terme de chaque critère dans chaque libellé
  correspondant**, sans compter les occurrences ou inventer une preuve PDF.
- Projection Unicode FR/AR partagée avec le Code, sans régression de son contrat ;
  ligatures/accents/marques/tatweel et caractères hors BMP pris en charge.
- Extraits originaux bornés à 16 par ligne et 384 points de code, troncature
  explicite et positions complètes même hors des 16 extraits. Préfixe seul inchangé.
- Interface intégrée : extrait textuel, critère/terme/champ, offsets Unicode et
  visibilité ; contrôle des bornes et du fragment contre le libellé reçu. Cache v67.
- Même API/CLI/audit/export que le lot 46 ; pas nouveau périmètre d'autorisation.

[Contrat détaillé et limites](EXTRAITS_TARIF_CRITERES.md).

## Tests exécutés

- **1 782 tests Python réussis**, sélection étendue de **54 fichiers**, **43,26 s**,
  un avertissement Starlette/httpx préexistant. Pas la suite OCR entière.
- **13 nouveaux cas Python** : projection multiterme FR/AR/emoji/ligatures/marques,
  premier match sans dénombrement, span dépassant le contexte, 160 localisations
  et 16 extraits maximum, préfixe seul, pagination sans extraire hors page, CLI,
  API réelle, audit, export structurel et absence de mutation des archives.
- **169 scénarios JSDOM réussis**, dont **11 nouveaux** : HTML inerte, Unicode hors
  BMP, rejet de champ/terme/bornes/fragment/unité/visibilité incohérents et
  disparition au changement de lot. Aucun navigateur réel simulé comme qualifié.
- Quatre parcours UI → HTTP → API réelle sur fixtures NON OFFICIELLES, avec
  positions et contexte affiché réellement vérifiés ; **70 exports JSON contrôlés
  hors ligne et 4 copies PDF Code**, sans changer les comptes du lot 46.
- Ruff, syntaxe des trois JS et diff-check : succès. SHA historiques inchangés :
  base `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
  référentiels `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

Aperçu redémarré sur 0.0.0.0:8000 : racine, module et SW v67 accessibles sous Host
distant ; requête anonyme multicritère refusée 403. Journaux historiques conservés
hors commit, aucun corpus réel inscrit ou réécrit.

## État global inchangé

**0 nouvel original officiel acquis, 0 article/code national officiellement validé,
0 publication active.** Positions documentaires ≠ attributs certifiés, classement
IA, authenticité ou preuve juridique. Pas de nouveaux taux/calculs/droit à date.
Dernière suite complète du dépôt : **lot 45**, 2 773 réussites, 18 échecs OCR et
11 ignorés, **non relancée intégralement ici**. Mission globale toujours partielle ;
les chantiers du bilan de réception restent ouverts.
