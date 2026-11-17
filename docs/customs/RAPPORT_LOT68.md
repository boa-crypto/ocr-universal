# Rapport lot 68 — provenance visible dans le panneau moteurs

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

La provenance enregistrée au lot 67 est maintenant visible dans l'interface
existante. Chaque run apparaît séparément, y compris avec un seul moteur ; les
variantes ne sont plus additionnées dans une moyenne comparative par moteur.

[Contrat et limites](AFFICHAGE_PROVENANCE_SCORES.md),
[recette machine](RECETTE_LOT68.json).

## Réalisation

- Module dédié chargé avant le rendu des résultats ; page, run, état, moyenne
  enregistrée arrondie en pourcentage, nombre d'éléments et durée disponibles.
- Baidu : compteurs déclaré/absent/invalide après contrôles locaux de cohérence,
  rappel non calibré et portée par run, pas par mot. Pas jauge verte comparative.
- Ancien résultat ou provenance incohérente : **« Provenance indisponible »**,
  sans compteur déduit. Un ancien 95 % n'est pas requalifié en score fournisseur.
- Pas de données invalides ou erreur brute fournisseur réaffichées dans ce panneau ;
  noms échappés, valeurs numériques vérifiées, pas de regroupement par clé moteur
  permettant un traitement spécial de `__proto__`.
- Nouveau rendu remplaçant l'ancien, absence de module explicitement signalée.
  Service worker **v71**, module inclus dans la coquille ; non-cache API inchangé.
- Pas écriture, requête métier, migration, recalcul de qualité ou validation ajouté.
  Les jauges des autres écrans et les scores historiques ne sont pas corrigés
  rétroactivement. Recharger la page charge les nouveaux scripts de l'aperçu.

## Vérifications

- **2 nouveaux tests Python**, dont un rendu HTTP/JSDOM avec **47 nouveaux
  scénarios**. Les trois modules complets sont téléchargés depuis le serveur
  applicatif, sans extraction de fonctions ou copie de logique de production.
  Le rendu complet et son repli module absent sont exécutés. Données de provenance
  synthétiques injectées ; pas de réponse Baidu réelle. Les PDF natifs du harnais
  restent synthétiques et ne qualifient pas le fournisseur distant.
- Sélection UI/Baidu/provenance : **143 réussis**, zéro échec/ignoré,
  1 avertissement, **44,02 s**, JUnit 44,021 s : 133 Baidu/provenance existants,
  8 contrôles UI existants et 2 nouveaux contrôles Python. Les 47 scénarios JS
  sont imbriqués dans un de ces tests, pas 47 tests Python supplémentaires.
- Contre-épreuve isolant l'ancien renderer du lot 67 : HTML/module nouveaux et
  `app-extras.js` exact du lot 67 servis sur un serveur temporaire. **45 scénarios
  préalables réussissent, puis l'intégration échoue comme attendu**, code 1 : le
  moteur unique reste masqué par « Comparaison indisponible ». Témoin hybride
  ciblé, pas exécution de toute l'ancienne application ni 47 échecs revendiqués.
  Aucun fichier source du checkout n'est remplacé pour ce témoin.
- Documentaire historique : **2 160 réussis**, zéro échec/ignoré, 1 avertissement,
  **58,81 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM documentaires** réussis.
  Quatre ponts et 74 exports existants, aucun nouveau parcours métier attribué.
- **Complète : 3 388 réussis, 2 échecs, 1 ignoré, 1 avertissement, 362,00 s**,
  soit **3 391 cas**, JUnit 361,923 s, code **1**. Compteurs cohérents avec les
  vrais cas. Échecs `test_indra_engine_availability` et
  `test_selection_prefers_native_when_present`, ignoré `test_indra_engine_recognize`,
  identiques au lot 67. **La suite complète n'est pas verte.**

Code **`aaeebd4015fed63faa84f1e706cb91651dcc390e`** poussé ;
[CI 42402144812](https://github.com/boa-crypto/ocr-universal/actions/runs/42402144812)
terminée **success**, révision et étapes confirmées via `gh` : sélection Baidu/
provenance, 24 ingestion/PDF, **10 UI** dont les deux nouveaux, puis documentaire.
Pas suite OCR complète en CI ni JUnit distant téléchargé. Résultats chiffrés locaux
conservés dans `/home/user/recettes-unocr/lot68` hors dépôt.

## Limites et réception

JSDOM et requêtes HTTP locales, pas qualification de navigateur réel, accessibilité,
rendu visuel, charge ou cycle offline du service worker. Cohérence client, pas
signature ou preuve d'authenticité du fournisseur. Compteurs par run et numéros
ordinaux, pas statut individuel par mot ni nom de variante. Scores non calibrés,
pas comparabilité scientifique des moteurs ou précision FR/AR mesurée.

Endpoint Baidu, géométrie approximative et risques OAuth query inchangés. Aucun
appel Baidu réel ni moteur Indra substitué. **26/27 empreintes historiques
conformes**, même écart référentiels qu'aux lots 64–67 : observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`, attendu
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Référentiels, quatre dossiers partagés modifiés, autres données exploratoires et
journaux préservés hors commit, sans restauration ou attribution certaine.

**0 nouvel original officiel, 0 article/code officiellement validé, 0 publication
active. Mission globale partielle, non recevable pour production fiscale.**
