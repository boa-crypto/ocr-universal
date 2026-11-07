# Lot 65 — diagnostics et transport Baidu bornés

7 novembre 2026. Durcissement testé **hors réseau**, pas qualification d'un compte
Baidu, d'une reconnaissance distante ou d'une connexion administrative autorisée.

## Risques corrigés

L'adaptateur construisait des URL par interpolation de clés/jeton, renvoyait les
objets d'erreur distants et le texte brut des exceptions. Une erreur de transport
pouvait donc devenir un résultat contenant une URL avec identifiants, puis être
tracée par le pipeline. Les redirections suivaient le comportement par défaut de
requests et les réponses JSON n'étaient pas bornées.

- Diagnostics de l'adaptateur limités à des messages locaux constants :
  authentification, préparation image, reconnaissance ou réponse invalide.
  Jamais de corps distant, `error_msg`, URL, clé, jeton ou exception interpolés
  dans ces messages. L'exception n'est même pas convertie en chaîne.
- Deux endpoints HTTPS constants, paramètres encodés par `requests`, TLS vérifié
  explicitement, **redirections refusées** et seul HTTP 200 accepté.
- Réponses lues en flux sous contexte, plafond **4 MiB décompressés** ; fermeture
  aussi sur statut refusé, JSON/UTF-8 invalide, débordement ou erreur de lecture.
- Objet JSON requis ; jeton ASCII imprimable non vide, longueur ≤ 8 192 ; liste
  `words_result` requise, ≤ 10 000 éléments, entrées texte vérifiées. Une réponse
  partiellement invalide n'est pas retournée comme un résultat partiel réussi.
- Une image RGBA est convertie en RGB avant encodage JPEG. Les résultats vides
  mais bien formés restent possibles, sans inventer des mots.

## Dépendance et disponibilité

```sh
python -m pip install -e '.[baidu]'
# Développement : inclut le transport pour les tests hors réseau.
python -m pip install -e '.[dev]'
```

`requests>=2.32.4` est un extra optionnel de production, également requis par les
tests de développement. Sans clés ou sans transport, l'adaptateur se déclare
indisponible et ne lance aucune requête. Un motif d'indisponibilité antérieur est
réinitialisé après configuration complète. Les deux paires de noms d'environnement
existantes restent supportées. Aucune clé n'est inscrite dans le code, la recette
ou les fichiers de configuration par ces tests.

Cette disponibilité reste **locale** : présence de paramètres et logiciel, pas
preuve de validité/autorisation des clés, solde du compte, disponibilité du
fournisseur ou aptitude d'un document à lui être transmis. Pas nouveau consentement
utilisateur ou mécanisme d'autorisation ajouté à la sélection des moteurs.

## Tests

**59 nouveaux cas**, plus le test existant d'enregistrement Baidu, lequel efface
explicitement ses variables d'environnement temporaires au lieu de présumer
qu'aucune clé n'est configurée sur le poste.

Les réponses et exceptions sont des doubles HTTP avec identifiants **factices**.
Cas : succès local simulé, encodage des caractères réservés, options TLS/timeout/
redirection, statuts 301/302/307/308/400/401/403/429/500 aux deux étapes, erreurs
réseau, JSON/UTF-8, structures invalides, limites de corps/jeton/mots, libération des
réponses, exception dont `__str__` ne doit jamais être exécuté, dépendance absente
et noms de variables historiques. Les messages et structures d'erreur rendus et
les logs capturés ne doivent contenir aucun des marqueurs sensibles factices.

```sh
.venv/bin/python -m pytest tests/test_baidu_transport.py tests/test_baidu_ocr.py -q
```

L'étape CI exécute ces 60 tests sans appel externe. Les autres étapes PDF,
rendu UI et sélection documentaire restent séparées. Les clés du poste ne sont
pas utilisées pour les essais ; aucun jeton réel demandé ou acquis.

## Risques résiduels — ne pas déclarer une confidentialité totale

Les paramètres OAuth **restent dans la query réellement envoyée**, y compris
`client_secret` et `access_token`. Le [SDK Python amont](https://github.com/Baidu-AIP/python-sdk/blob/master/aip/base.py)
emploie également des paramètres query ; notre lecture de cette source n'établit
pas la compatibilité d'un autre schéma d'authentification. Nous n'avons donc pas
inventé un déplacement vers un header non vérifié, ni qualifié un POST OAuth en
corps uniquement. Les paramètres structurés évitent l'interpolation incorrecte,
**pas** leur présence sur le réseau. Le choix dangereux `verify=False` visible
chez cet amont n'est pas repris : notre transport exige `verify=True`.

Le service peut recevoir une image contenant des données sensibles. HTTPS n'est
pas une garantie d'absence de journalisation chez le fournisseur, proxy approuvé,
outil d'observabilité, bibliothèque en mode DEBUG ou capture mémoire. Les tests
ne couvrent pas ces traces externes. Ils ne prouvent pas non plus que le texte
OCR retourné ne contiendra jamais un secret présent dans le document lui-même.
La politique de proxy/autorités de confiance de requests reste celle du poste.

Timeouts : connexion 5 s, lecture 10 s pour OAuth et 15 s pour OCR. Ce sont des
**délais d'inactivité**, pas un délai mural global ni une sandbox réseau. Le
plafond 4 MiB borne les octets assemblés, pas toute la mémoire des structures JSON.
Les limites de l'image d'entrée restent celles du pipeline ; pas nouveau quota
ou mécanisme de facturation, retry, cache de jeton ou test de charge ajouté.

Aucun appel réel à `aip.baidubce.com`, hors des hôtes autorisés ici. Pas contournement
réseau ; compatibilité réelle et reconnaissance fournisseur non qualifiées.
Le score conventionnel préexistant 0,95 des mots Baidu n'est pas modifié par ce
lot et ne devient pas une probabilité calibrée ou une précision mesurée.
Aucun effet sur l'absence d'Indra ni sur la validation réglementaire du corpus.
