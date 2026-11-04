# Agents importés depuis le catalogue « agency »

## Origine

| Élément | Valeur |
|---|---|
| Source | `.dsh/skills/<slug>/SKILL.md` (catalogue présent dans le dépôt) |
| Catalogues équivalents sur disque | `.claude/agents/` (283 fichiers), `.github/agents/` (283), `.dsh/skills/` (282) |
| Sélection | 18 agents sur 282 |
| Cible | `.opencode/agents/<catégorie>/<nom>.md` → identifiant OpenCode `<catégorie>/<nom>` |
| Import | 2026-10-26 |

## Transformation appliquée

Le frontmatter d'origine (`name`, `description`) a été remplacé par un frontmatter OpenCode V2 :

```yaml
---
description: <description d'origine, verbatim>
mode: subagent
---
```

Le corps du fichier est conservé **verbatim** : seule la mise en forme du
frontmatter change. Aucun persona n'a été réécrit, donc certains décrivent
d'autres stacks que ce projet (Laravel/Livewire, WordPress, Laravel Nova…).
Ils restent utiles pour leur méthode, pas pour leur écosystème : à adapter au
cas par cas si le comportement par défaut ne convient pas.

Aucun `model:` n'est fixé : ces agents héritent du modèle de la session
appelante, ce qui évite d'imposer un fournisseur ou une clé API.

## Sélection

| Identifiant | Pourquoi |
|---|---|
| `engineering/software-architect` | Décisions d'architecture, cohérence des modules |
| `engineering/backend-architect` | FastAPI, `api.py` (3 453 lignes), routes |
| `engineering/api-platform-engineer` | 124 routes HTTP, contrat d'API |
| `engineering/code-reviewer` | Revue de code |
| `engineering/minimal-change-engineer` | Corrections chirurgicales, sans réécriture |
| `engineering/pdf-engine-architect` | Cœur du produit : PDF natifs/scannés/hybrides |
| `engineering/universal-document-compiler` | Ingestion/compilation multi-formats |
| `engineering/frontend-developer` | UI vanilla sans build, `web/` |
| `engineering/i18n-engineer` | Dette B1 documentée dans `docs/AUDIT.md` |
| `engineering/technical-writer` | Documentation et rapports d'audit |
| `engineering/devops-automator` | Docker, CI `.github/workflows/ci.yml` |
| `security/appsec-engineer` | Upload de fichiers, `security.py` |
| `security/secrets-credential-engineer` | `data/keys/master.key`, conneteurs secrets |
| `testing/test-automation-engineer` | 799 tests, 55 fichiers |
| `testing/api-tester` | Couverture des routes |
| `testing/performance-benchmarker` | `benchmarks/` |
| `testing/reality-checker` | Vérifier les affirmations plutôt que les croire |
| `product/manager` | Priorisation, `ROADMAP.md` |

## Ajouter d'autres agents

```powershell
$slug = 'engineering-database-optimizer'   # nom du dossier dans .dsh/skills
$p = ".dsh\skills\$slug\SKILL.md"
```

Reprendre le frontmatter `description`, ajouter `mode: subagent`, conserver le
corps. Ou relancer un script de conversion équivalent à celui utilisé le
2026-10-26 (non conservé dans le dépôt).

## Vérifier la découverte

Les agents sont découverts automatiquement depuis `.opencode/agents/` (pas de
redémarrage nécessaire). En session, ils apparaissent dans le catalogue des
sous-agents sous les identifiants `engineering/*`, `security/*`, `testing/*`,
`product/*`.

Attention : `README.md` ou tout autre `.md` placé dans `.opencode/agents/`
serait interprété comme un agent. Ce fichier est donc volontairement en dehors.
