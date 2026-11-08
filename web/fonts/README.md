# Polices locales

Ces fichiers WOFF2 sont extraits, octet pour octet, des URL data: déjà
présentes dans `web/styles.css` avant la refonte produit. Aucun téléchargement
de police ou changement de licence. La déclaration SIL Open Font License1.1
de la coque existante est conservée. Les fichiers de même SHA sont dédupliqués.

Objectif : servir les polices en same-origin, compatibles avec la CSP
`font-src` implicite `self`, sans autoriser data: ni fournisseur externe.

Les textes OFL sont également fournis, récupérés via l'API GitHub du dépôt
`google/fonts`, répertoires `ofl/inter`, `ofl/instrumentserif` et
`ofl/jetbrainsmono`. Les polices elles-mêmes ne sont pas réacquises.
