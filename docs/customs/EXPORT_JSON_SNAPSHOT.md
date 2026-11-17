# Export JSON complet lié au résultat lu — lot 89

Route ciblée : `GET /api/jobs/{job_id}/export/json`.

## Défaut et changement

`_ensure_export` validait bien le résultat courant mais réutilisait ensuite
`exports/result.json` s'il existait. Une correction, annulation ou nouvelle
classification pouvait donc être visible au GET et absente du téléchargement.

Après les gardes et la vérification du job, la route JSON complète lit une fois
le résultat, applique `DocumentResult` et renvoie sa sérialisation JSON en mémoire.
Elle ne passe plus par `_ensure_export`, ne crée pas de dossier/fichier d'export,
ne lit/modifie pas le cache existant et ne réouvre pas un fichier partagé au
moment de servir la réponse. Contenu sémantique identique à l'exporteur JSON
(`model_dump(mode="json")`), mise en forme compacte non identique octet par octet.

Contrat HTTP : `application/json`, téléchargement `result.json`,
**`Cache-Control: no-store`**, sans ETag ni Last-Modified calculés depuis un fichier.
Des anciens en-têtes conditionnels ne font pas revenir une réponse304 obsolète.
Cela concerne les réponses émises par ce code, pas une purge des caches déjà
présents chez des clients/proxies ou une garantie qu'ils contacteront le serveur.

Le cliché est celui lu pour cette requête, **pas nécessairement le dernier état
à la fin du transfert** si une écriture intervient après lecture. Un entrelacement
testé modifie le store juste après lecture : la réponse conserve intégralement
le cliché précédent et n'effectue pas de seconde lecture.

## Recette

26 nouveaux cas : cinq caches existants valides/invalides/vides inchangés,
six changements confirmation/correction/statut/undo/classification manuelle/
automatique après cache initial, un export sans aucun chemin fichier,
un entrelacement de sauvegarde, cinq comptes autorisés, trois refus avant
résultat/cache, un job absent, un résultat indisponible malgré cache,
un résultat à statut invalide sans repli cache, un contrôle TXT inchangé,
un téléchargement avec anciens en-têtes conditionnels.

Stores/jobs/audits et HTTP réels temporaires ; caches artificiels explicités,
valeurs relues typées et empreintes conservées hors modifications intentionnelles.
Pas navigateur réel, OCR fournisseur ou charge représentative.
Contre-épreuve : seul ancien `export_job` réinjecté en mémoire ; fixtures/helper
inchangés, checkout/aperçu non remplacés.
[Rapport](RAPPORT_LOT89.md), [recette](RECETTE_LOT89.json).

## Limites

**Seulement JSON complet par cette route** : TXT/CSV/XML/XLSX/PDF, exports
sélectionnés, batch/archives, helper `_ensure_export` et exporteurs disque
inchangés. Le cache JSON ancien n'est pas réparé/supprimé ; d'autres chemins
qui le consomment peuvent rester obsolètes. Pas invalidation globale ou garantie
de fraîcheur pour tous les exports.

Pas borne nouvelle de taille, mémoire, CPU ou débit : modèle et JSON sont
matérialisés en mémoire à chaque requête. Pas qualification de charge ou streaming.
Validation modèle existante, pas nouvelle validation universelle des valeurs,
qualité ou fiscalité. Ordre gardes/formats/job conservé ; résultat indisponible409,
modèle invalide500 selon gestion d'erreurs existante, sans repli cache.
Pas refonte du détail des erreurs ou de la journalisation.

Snapshot de contenu, pas signature ni identité de révision ou transaction avec
la réponse. Autres écrivains/processus/ABA, audit best-effort et droits inchangés.
Aperçu backend76 maintenu : code77–89 poussé/testé mais non chargé avant
redémarrage maîtrisé pour préserver les traitements. RBAC non activé
implicitement ; mission réglementaire toujours partielle.
