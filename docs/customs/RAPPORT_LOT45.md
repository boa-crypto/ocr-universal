# Lot 45 — recette transversale et bilan de réception technique

7 novembre 2026. Branche `arena/2cd4c91a-ocr-universal`.

Après le lot fonctionnel 44, exécution de la suite complète du dépôt, sans ignorer
les échecs, puis correction de sept attentes de tests obsolètes/non isolées :

- Cinq tests de catalogue/connecteurs supposaient encore deux adaptateurs et zéro
  adaptateur externe. Le catalogue livre depuis les lots antérieurs `customs_api`
  en plus de la démo et de l'export assisté. Attentes actualisées et contrôle
  renforcé : classe disponible ≠ instance configurée ou opérationnelle. Aucun
  accès administratif ou connexion réelle n'a été activé pour rendre les tests verts.
- Deux tests de chemins par défaut héritaient des variables d'environnement
  d'isolation. Ils effacent maintenant explicitement leur variable de surcharge
  pendant leur test ; les tests de surcharge restent conservés.
- Documentation du registre mise en cohérence ; aucune logique OCR modifiée,
  aucun échec OCR transformé en skip et aucun calcul non sourcé réactivé.

## Résultats effectivement obtenus

1. Première suite complète : **2 766 réussis, 25 échecs, 11 ignorés**, 203,49 s.
2. Tests ciblés config/connecteurs/douane après correction : **97 réussis**.
3. Deuxième suite complète : **2 773 réussis, 18 échecs, 11 ignorés**, **204,32 s**,
   1 avertissement Starlette/httpx. **La suite complète n'est pas verte.**
4. Recette douanière étendue du lot 44 : **1 741 réussis / 52 fichiers**, 43,01 s ;
   UI **152 scénarios**, quatre parcours HTTP/API, **66 exports JSON contrôlés**
   et quatre copies PDF Code. Pas qualification nationale ou navigateurs réels.

Les 18 échecs restants touchent disponibilité/routage/exécution des moteurs OCR,
leurs endpoints et les parcours scannés. Tesseract n'est pas installé et le module
Indra OCR n'est pas présent ; la recette ne simule pas leur disponibilité.
La liste exacte des tests en échec est dans [RECETTE_FINALE.json](RECETTE_FINALE.json).
Une réexécution dans un environnement OCR provisionné reste nécessaire ; aucune
affirmation que ces tests y seraient déjà réussis.

La suite complète régénère huit fixtures PDF/DOCX avec horodatages. Ces changements
incidents ont été annulés vers leur version Git antérieure ; aucun original de
production touché. Logs existants préservés hors commit, inventaire et empreintes
historiques revérifiés après les tests. Aperçu redémarré en v65, accès distant et
refus anonyme contrôlés. Pas de lot réel inscrit dans la quarantaine locale.

## Réception

[Bilan final des dix phases](BILAN_RECEPTION.md). Le lot 45 termine cette campagne
de vérification technique ; il **ne termine pas la mission réglementaire** et ne
renumérote pas les chantiers non livrés comme terminés.
