"""
Script de refactorisation finale de index.html
Supprime les blocs de modules dupliqués et insère les balises script externes
"""
import re

# Lire le fichier original
with open('C:\\workSpace\\ocr-universal\\web\\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"Taille originale: {len(html):,} chars ({len(html)/1024:.1f} KB)")

# 1. Supprimer tous les blocs <style>
html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
print(f"Après suppression CSS: {len(html):,} chars ({len(html)/1024:.1f} KB)")

# 2. Ajouter le lien vers styles.css dans le <head>
html = re.sub(
    r'(<head[^>]*>\s*)',
    r'\1\n  <link rel="stylesheet" href="styles.css">\n',
    html,
    count=1
)

# 3. Définir les modules à remplacer
modules = [
    {
        'begin': r'/\* ═══ CNXHUB:BEGIN.*?',
        'end': r'\* ═══ CNXHUB:END ═══ \*/',
        'replacement': '    <script src="connectors.js" defer></script>'
    },
    {
        'begin': r'/\* ═══ DOSSIER:BEGIN.*?',
        'end': r'\* ═══ DOSSIER:END ═══ \*/',
        'replacement': '    <script src="dossier.js" defer></script>'
    },
    {
        'begin': r'/\* ═══ FORMULAIRE:BEGIN.*?',
        'end': r'\* ═══ FORMULAIRE:END ═══ \*/',
        'replacement': '    <script src="formulaire.js" defer></script>'
    },
    {
        'begin': r'/\* ═══ TRACABILITE:BEGIN.*?',
        'end': r'\* ═══ TRACABILITE:END ═══ \*/',
        'replacement': '    <script src="tracabilite.js" defer></script>'
    },
    {
        'begin': r'/\* ═══ TRANSMISSION:BEGIN.*?',
        'end': r'\* ═══ TRANSMISSION:END ═══ \*/',
        'replacement': '    <script src="transmission.js" defer></script>'
    }
]

# 4. Remplacer chaque bloc de module dupliqué par un script externe
total_removed = 0
for module in modules:
    pattern = f"{module['begin']}{module['end']}"
    matches = re.findall(pattern, html, flags=re.DOTALL)
    if matches:
        for match in matches:
            total_removed += len(match)
        html = re.sub(pattern, module['replacement'], html, flags=re.DOTALL)
        print(f"✓ Remplacé module: {module['replacement']}")
    else:
        print(f"⚠ Module non trouvé: {module['replacement']}")

print(f"\nJS dupliqué supprimé: {total_removed:,} chars ({total_removed/1024:.1f} KB)")

# 5. Sauvegarder le fichier refactorisé
output_path = 'C:\\workSpace\\ocr-universal\\web\\index_refactored.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

final_size = len(html)
original_size = 738129  # Taille connue de l'original

print(f"\n{'='*60}")
print(f"✅ REFACTORING TERMINÉ")
print(f"{'='*60}")
print(f"Taille finale: {final_size:,} chars ({final_size/1024:.1f} KB)")
print(f"Réduction: {((original_size - final_size) / original_size * 100):.1f}%")
print(f"Fichier créé: {output_path}")

# Vérification
print(f"\n{'='*60}")
print("VÉRIFICATION:")
print(f"{'='*60}")

checks = [
    ('CNXHUB:BEGIN', 'Module CNXHUB'),
    ('DOSSIER:BEGIN', 'Module DOSSIER'),
    ('FORMULAIRE:BEGIN', 'Module FORMULAIRE'),
    ('TRACABILITE:BEGIN', 'Module TRACABILITE'),
    ('TRANSMISSION:BEGIN', 'Module TRANSMISSION'),
    ('styles.css', 'Lien CSS externe'),
    ('connectors.js', 'Script connectors.js'),
    ('dossier.js', 'Script dossier.js'),
    ('formulaire.js', 'Script formulaire.js'),
    ('tracabilite.js', 'Script tracabilite.js'),
    ('transmission.js', 'Script transmission.js')
]

for pattern, name in checks:
    if pattern in html:
        if pattern.endswith(':BEGIN'):
            print(f"❌ {name} encore présent (duplication non supprimée)")
        else:
            print(f"✅ {name} chargé")
    else:
        if pattern.endswith(':BEGIN'):
            print(f"✅ {name} supprimé")
        else:
            print(f"⚠️  {name} non trouvé")
