"""
Script d'optimisation du Design System UniOCR
Consolidation des couleurs: 76 → ~25 couleurs via tokens
"""
import re
from pathlib import Path
from collections import Counter

# Lire le CSS
css_path = Path('C:/workSpace/ocr-universal/web/styles.css')
css = css_path.read_text(encoding='utf-8')

print("="*70)
print("ANALYSE DES COULEURS - UNIOCR DESIGN SYSTEM")
print("="*70)

# Extraire toutes les couleurs hex
all_colors = re.findall(r'#[0-9a-fA-F]{6}', css)
color_counts = Counter(all_colors)

print(f"\nTotal de couleurs hex trouvées: {len(all_colors)}")
print(f"Couleurs uniques: {len(color_counts)}")

# Top 30 couleurs les plus utilisées
print("\n" + "="*70)
print("TOP 30 COULEURS LES PLUS UTILISÉES")
print("="*70)

for color, count in color_counts.most_common(30):
    percentage = (count / len(all_colors)) * 100
    print(f"{color}: {count:3d}x ({percentage:5.1f}%)")

# Tokens existants
print("\n" + "="*70)
print("TOKENS COULEUR EXISTANTS")
print("="*70)

existing_tokens = {
    '--obsidian': '#101A19',
    '--graphite': '#192624',
    '--mineral': '#2B3B38',
    '--ivory': '#F4F7F5',
    '--silver': '#A9B8B2',
    '--electric': '#83D3C3',
    '--cyan': '#E0A17D',  # Note: mal nommé, c'est du cuivre/orange
    '--ok': '#7BD1A1',
    '--warn': '#F0C36A',
    '--err': '#F08A7B',
}

for token, value in existing_tokens.items():
    if value in color_counts:
        count = color_counts[value]
        print(f"{token:15s} = {value}  →  {count:3d} usages directs trouvés")
    else:
        print(f"{token:15s} = {value}  →  0 usages directs (utilisé via var)")

# Identifier les couleurs à tokeniser
print("\n" + "="*70)
print("COULEURS À TOKENISER (>5 usages sans token)")
print("="*70)

tokenized_values = set(existing_tokens.values())
candidates = []

for color, count in color_counts.most_common(50):
    if count > 5 and color not in tokenized_values:
        candidates.append((color, count))

if candidates:
    print(f"\n{len(candidates)} couleurs candidates pour nouveaux tokens:\n")
    for color, count in candidates[:20]:  # Top 20
        print(f"{color}: {count:3d}x")
else:
    print("\n✓ Toutes les couleurs fréquentes ont déjà un token!")

# Analyser l'utilisation des tokens
print("\n" + "="*70)
print("UTILISATION DES TOKENS VS HEX DIRECT")
print("="*70)

# Compter les var(--xxx)
var_usage = len(re.findall(r'var\(--[a-z-]+\)', css))
hex_direct = len(all_colors)

print(f"var(--token): {var_usage:4d} usages")
print(f"#hex direct:  {hex_direct:4d} usages")
print(f"Ratio tokens: {(var_usage / (var_usage + hex_direct) * 100):.1f}%")

# Recommandations
print("\n" + "="*70)
print("RECOMMANDATIONS")
print("="*70)

print("\n1. Créer des tokens pour les couleurs fréquentes non tokenizées")
print("2. Remplacer tous les hex directs par var(--token)")
print("3. Réduire les couleurs one-off (<5 usages)")
print(f"4. Objectif: passer de {len(color_counts)} à ~25 couleurs max")

print("\n" + "="*70)
print("ANALYSE TERMINÉE")
print("="*70)
