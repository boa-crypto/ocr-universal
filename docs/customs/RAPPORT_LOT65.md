# Rapport lot 65 — confidentialité des erreurs du transport Baidu

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

L'adaptateur Baidu ne renvoie plus de réponses d'erreur distantes ou d'exceptions
brutes susceptibles d'inclure clés, jeton ou URL. Les redirections sont refusées,
les réponses sont bornées et fermées, TLS reste vérifié. Aucun appel réel Baidu,
aucune clé réelle demandée ou installée par cette recette.

[Contrat et risques résiduels](CONFIDENTIALITE_TRANSPORT_BAIDU.md),
[recette machine](RECETTE_LOT65.json).

## Réalisations et tests

- Messages locaux contrôlés, sans interpolation des erreurs du fournisseur ou
  conversion des exceptions sensibles en chaînes. Encodage des paramètres confié
  à requests, pas interpolation d'identifiants dans les URL.
- Endpoints HTTPS fixes, `verify=True`, `allow_redirects=False`, HTTP 200 requis.
  Réponses en flux, plafond 4 MiB décompressés, fermeture sur erreurs et refus.
  Objets JSON, jetons et listes de mots contrôlés ; pas succès partiel pour une
  structure invalide. Image RGBA convertie en RGB avant JPEG.
- Extra **`baidu`** : requests ≥ 2.32.4, également déclaré en dépendance de tests
  `dev`. Sans transport ou clés, disponibilité refusée ; aucun appel pour le
  vérifier. Une disponibilité locale ne prouve pas l'accès réel au fournisseur.
- **59 nouveaux tests**, sélection **60 réussis, 0 échec, 0 ignoré, 0,52 s**.
  Doubles HTTP et secrets factices exclusivement : statuts/redirections, erreurs
  réseau/JSON/UTF-8, encodage, limites, libération des réponses, variables héritées
  et exception dont `__str__` ne doit jamais être évalué. Pas reconnaissance
  distante simulée présentée comme réelle.
- Sélection documentaire inchangée : **2 160 réussis, 0 échec, 0 ignoré,
  1 avertissement, 55,11 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM** réussis.
  Quatre ponts et 74 exports existants, pas nouveau scénario métier attribué.
- **Complète : 3 313 réussis, 2 échecs, 1 ignoré, 1 avertissement, 342,37 s**,
  soit **3 316 tests**, code **1**. Compteurs JUnit cohérents avec les cas réels,
  sélection complète non verte. Les deux échecs sont exactement ceux du lot 64,
  liés à Indra absent ; seul ignoré : `test_indra_engine_recognize`.

## CI et environnement

Code **`c66551e2`**, run
**[42399498261](https://github.com/boa-crypto/ocr-universal/actions/runs/42399498261)**
terminé **success**, révision et étapes confirmées via `gh` : 60 tests Baidu hors
réseau, 24 ingestion/PDF, 8 UI, puis sélection documentaire. Le premier run
[42399333425](https://github.com/boa-crypto/ocr-universal/actions/runs/42399333425)
était également réussi. Ubuntu 24.04 / Python 3.11 / Node 24, installation
explicite `.[dev,baidu]`. **Pas suite OCR complète en CI**, pas JUnit distant
 téléchargé ; chiffres détaillés ci-dessus mesurés localement.

Localement requests **2.34.2** et urllib3 **2.8.0** installés depuis PyPI public.
Pas réinstallation editable ou modification des métadonnées egg-info historiques.
Aperçu redémarré avec le correctif sur `0.0.0.0:8000`. Tesseract local et OpenCV
headless restent ceux des lots précédents. Artefacts :
`/home/user/recettes-unocr/lot65`.

## Confidentialité partielle, pas garantie globale

**Les paramètres OAuth sensibles restent dans la query effectivement envoyée**,
y compris secret et jeton. Le SDK amont utilise cette convention ; un autre
schéma n'a pas été inventé sans qualification fournisseur. L'encodage structuré
n'enlève donc pas les secrets des requêtes. Les logs externes, proxy approuvé,
traces DEBUG de bibliothèques, fournisseur et mémoire ne sont pas couverts par
nos tests de diagnostics applicatifs. Les images et le texte OCR peuvent eux-mêmes
contenir des données sensibles. Pas nouveau consentement ou contrôle métier
 d'autorisation ajouté à la sélection du moteur.

Les timeouts sont d'inactivité, pas une limite murale globale ; 4 MiB borne les
octets assemblés, pas toute la mémoire du JSON. Pas sandbox réseau, test de
charge, retry ou cache de jeton. Le score conventionnel préexistant 0,95 n'est
ni modifié ni qualifié comme probabilité calibrée. **Connectivité, compatibilité
et reconnaissance réelles Baidu non vérifiées** : hôte hors allowlist, pas de
contournement. Indra reste absent, sans moteur de remplacement ou assertion
assouplie pour masquer les échecs.

## Données partagées préservées

**26/27 empreintes historiques conformes**, même écart qu'au dernier relevé du
lot 64 : `data/referentiels.json` observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`, référence
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Le référentiel, quatre dossiers historiques déjà modifiés, les journaux et données
exploratoires restent hors commit et non restaurés. Pas certificat d'intégrité
globale du magasin, ni effacement d'une saisie pour rendre le bilan conforme.

**Mission réglementaire toujours partielle : 0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.**
