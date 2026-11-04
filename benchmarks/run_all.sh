#!/usr/bin/env bash
# Harnais de benchmark UniOCR — complète, reproductible, horodaté.
#
# Usage :
#   ./benchmarks/run_all.sh              # tests + toutes les suites
#   ./benchmarks/run_all.sh --no-tests   # benchmarks seuls (itération rapide)
#
# Produit dans benchmarks/results/ :
#   report_<horodatage>.md   rapport complet de cette exécution
#   latest.md                copie du dernier rapport
#   benchmark_<horodatage>.* sortie brute de la suite synthétique
#   field_latest.*           sortie de la suite terrain
#
# Le code de retour est non nul si au moins une étape échoue.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"
OUT="$ROOT/benchmarks/results"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="$OUT/report_${STAMP}.md"
RUN_TESTS=1
[ "${1:-}" = "--no-tests" ] && RUN_TESTS=0

mkdir -p "$OUT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
FAILED=0

{
  echo "# Rapport de benchmark UniOCR"
  echo
  echo "- Exécution : $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "- Machine : $(uname -srm) — $(nproc) cœurs"
  echo "- Python : $(python3 --version 2>&1)"
  echo "- Tesseract : $(tesseract --version 2>&1 | head -1)"
  echo
  echo "> Les chiffres de la suite **synthétique** sont mesurés sur des documents"
  echo "> générés programmatiquement. Ils ne valent **pas** promesse sur des"
  echo "> documents réels. La suite **terrain** ne produit un chiffre que si des"
  echo "> photos réelles annotées sont fournies dans \`benchmarks/field/\`"
  echo "> (voir \`benchmarks/corpus/README.md\`)."
} > "$REPORT"

run_step () {
  local title="$1"; shift
  echo "" >> "$REPORT"
  echo "## $title" >> "$REPORT"
  echo "" >> "$REPORT"
  echo '```' >> "$REPORT"
  if "$@" >> "$REPORT" 2>&1; then
    echo '```' >> "$REPORT"
    echo "" >> "$REPORT"
    echo "**Résultat : OK**" >> "$REPORT"
    echo "  [OK]   $title"
  else
    local code=$?
    echo '```' >> "$REPORT"
    echo "" >> "$REPORT"
    echo "**Résultat : ÉCHEC (code $code)**" >> "$REPORT"
    echo "  [FAIL] $title (code $code)"
    FAILED=1
  fi
}

if [ "$RUN_TESTS" = "1" ]; then
  run_step "Tests unitaires et d'intégration" \
    python3 -m pytest tests/ -q --no-header
else
  echo "" >> "$REPORT"
  echo "## Tests" >> "$REPORT"
  echo "" >> "$REPORT"
  echo "_Étape ignorée (--no-tests)._" >> "$REPORT"
  echo "  [SKIP] tests"
fi

# Contrôle statique de l'interface (pas de navigateur dans cet environnement)
if command -v node >/dev/null 2>&1; then
  run_step "Contrôle statique de l'interface (syntaxe, DOM simulé, identifiants)" \
    node tests/ui_stub_check.js
else
  echo "" >> "$REPORT"
  echo "## Contrôle statique de l'interface" >> "$REPORT"
  echo "" >> "$REPORT"
  echo "_Node.js absent — étape ignorée._" >> "$REPORT"
  echo "  [SKIP] contrôle UI (node absent)"
fi

run_step "Suite synthétique (documents générés)" \
  python3 benchmarks/run_benchmark.py

run_step "Suite terrain (photos réelles annotées)" \
  python3 benchmarks/run_field_benchmark.py --suite both

cp "$REPORT" "$OUT/latest.md"

{
  echo ""
  echo "---"
  echo ""
  echo "Rapport : $REPORT"
} >> "$REPORT"
cp "$REPORT" "$OUT/latest.md"

echo ""
echo "Rapport complet : $REPORT"
if [ "$FAILED" = "1" ]; then
  echo "AU MOINS UNE ÉTAPE A ÉCHOUÉ — voir le rapport."
  exit 1
fi
echo "Toutes les étapes sont passées."
exit 0
