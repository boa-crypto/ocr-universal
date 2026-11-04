# Quarantaine du 20261026-084032

Deplace depuis la racine du depot vers `sauvegardes/quarantaine-20261026-084032/`.
Aucun fichier n a ete supprime : l arborescence d origine est conservee.

## Restauration

```powershell
Copy-Item -Recurse -Force 'sauvegardes\quarantaine-20261026-084032\web\*'   'web\'
Copy-Item -Recurse -Force 'sauvegardes\quarantaine-20261026-084032\tools\*' 'tools\'
Copy-Item -Recurse -Force 'sauvegardes\quarantaine-20261026-084032\tests\*' 'tests\'
Copy-Item -Force 'sauvegardes\quarantaine-20261026-084032\audit_agency.py' '.'
```

## Contenu

| Fichier | Octets | SHA256 (16) | Raison |
|---|---:|---|---|
| `web\index_new.html` | 259924 | `4A350A4065DB8EEF` | Doublon octet-identique de index_refactored_final.html (SHA256 4A350A40...), non reference |
| `web\index_refactored_final.html` | 259924 | `4A350A4065DB8EEF` | Doublon octet-identique de index_new.html (SHA256 4A350A40...), non reference |
| `web\index_refactored.html` | 149167 | `DB0FDDDE1B2B6679` | Variante non chargee : 17 lignes de diff avec web\index.html actif |
| `web\index.html.backup` | 744834 | `D9E8B2818CE9865D` | Sauvegarde pre-refactor (744 Ko), remplacee par la quarantaine elle-meme |
| `tools\sync_web_module.py.obsolete` | 6828 | `396E9E4A0BF7718B` | Mecanisme de sync abandonne (architecture a modules externes) |
| `tools\refactor_html.py` | 3897 | `1AB8C316BD69892B` | Script one-shot, chemin code en dur C:\workSpace\..., deja applique |
| `tools\analyze_design_system.py` | 3001 | `653647C8A2FB5656` | Script one-shot, chemin code en dur C:/workSpace/..., non integre |
| `tools\_cfg_coherence.py` | 3246 | `875CB9D0BC3B03FF` | Patch one-shot, chemin code en dur /home/user/..., deja applique |
| `tools\_fix_debit.py` | 2798 | `1F3FB4DD7BE6682C` | Patch one-shot, chemin code en dur /home/user/..., deja applique |
| `tests\test_web_module_sync.py.obsolete` | 3308 | `28D86294215CA2EC` | Test du mecanisme de sync abandonne |
| `tests\_ui_bloc_0.js` | 87817 | `857471819DCE433B` | Artefact regenere par tests\ui_stub_check.js a chaque execution |
| `tests\_ui_bloc_1.js` | 283 | `80DE246D5E2966AC` | Artefact regenere par tests\ui_stub_check.js a chaque execution |
| `tests\_ui_bloc_2.js` | 6777 | `677A482EAA652D8A` | Artefact regenere par tests\ui_stub_check.js a chaque execution |
| `tests\_ui_bloc_3.js` | 40 | `635B3F7E6A26C342` | Artefact regenere par tests\ui_stub_check.js a chaque execution |
| `audit_agency.py` | 14440 | `C6C2CF7F34557A79` | Script Agency Swarm sans rapport avec l app ; dependance agency_swarm absente des requirements |

## Conserve volontairement
- `tests/_dossier_render_src.js` et `tests/_hub_render_src.js` : sources du harnais, utilisees par `tests/ui_stub_check.js` (l. 210).
- `tools/scenario_validation.py` : harnais de validation reel, sans chemin code en dur.
- `components/`, `styles/`, `brand/`, `ux-research/` : design system non branche a l UI, mais coherent (`styles/base/variables.css` importe `brand/*.css`). A arbitrer.

## References historiques restantes
- `ROADMAP.md` et `docs/audit/*.md` citent encore `tools/sync_web_module.py` et `web/index_refactored.html` : ce sont des journaux dates, laisses tels quels.
- `docs/audit/PHASE1_COMPLETED.md` (l. 209-210) decrit une restauration via `index.html.backup` : le fichier est desormais dans cette quarantaine.
- `tests/test_web_architecture_refactored.py` (l. 37-47) verifie justement que ces marqueurs ont disparu de `web/index.html` : ce test reste valide et passe.



