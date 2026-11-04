#!/usr/bin/env bash
# Vérification live des endpoints de la vague 3 (hors suite de tests).
# Usage : ./benchmarks/verify_wave3.sh   (serveur démarré)
#
# Contrôle chaque élément livré en vague 3 : B5 profils, A2 calibration,
# E2 typage de zones, C3 i18n/PWA, D3 jeton. Aucun chiffre n'est inventé :
# tout est lu dans les réponses réelles du serveur.
cd "$(dirname "$0")/.." || exit 1
BASE="${UNOCR_BASE:-http://127.0.0.1:8000}"
FAIL=0
ok()   { echo "  [OK]   $1"; }
ko()   { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
# en-tête d'authentification si un jeton est défini dans l'environnement
AUTH=()
if [ -n "$UNOCR_TOKEN" ]; then AUTH=(-H "Authorization: Bearer $UNOCR_TOKEN"); fi
getc() { curl -s "${AUTH[@]}" -o /dev/null -w '%{http_code}' "$1"; }
posts() { curl -s "${AUTH[@]}" -X POST "$1" -H "Content-Type: application/json" -d "$2"; }
gets() { curl -s "${AUTH[@]}" "$1"; }

echo "=== 1. ÉTAT DES SERVICES (A2 calibration, D3 jeton) ==="
for u in /api/health /api/auth/status /api/calibration; do
  c=$(getc "$BASE$u")
  [ "$c" = "200" ] && ok "$u → 200" || ko "$u → $c"
done
echo "  calibration : $(gets "$BASE/api/calibration")"

echo ""
echo "=== 2. PWA (C4) ==="
for u in /manifest.webmanifest /sw.js /icon.svg; do
  c=$(getc "$BASE$u")
  [ "$c" = "200" ] && ok "$u → 200" || ko "$u → $c"
done
python3 - <<'PY'
import json, urllib.request
base = "http://127.0.0.1:8000"
try:
    m = json.load(urllib.request.urlopen(base + "/manifest.webmanifest"))
    print(f"  [OK]   manifeste : {m['name']} — démarrage {m['start_url']}, "
          f"{len(m['icons'])} icône(s)")
    sw = urllib.request.urlopen(base + "/sw.js").read().decode()
    assert "caches" in sw and "/api/" in sw
    print("  [OK]   service worker : coquille en cache, /api/ exclu")
except Exception as e:
    print("  [FAIL]", e)
PY
grep -q 'rel="manifest"' web/index.html && ok "index.html référence le manifeste" \
  || ko "index.html ne référence pas le manifeste"
grep -q 'serviceWorker.register' web/index.html && ok "index.html enregistre le service worker" \
  || ko "service worker non enregistré côté UI"

echo ""
echo "=== 3. PROFILS (B5) ==="
c=$(getc "$BASE/api/profiles")
[ "$c" = "200" ] && ok "GET /api/profiles → 200" || ko "GET /api/profiles → $c"
python3 - <<'PY'
import json, urllib.request
base = "http://127.0.0.1:8000"
d = json.load(urllib.request.urlopen(base + "/api/profiles/catalog"))
print(f"  [OK]   catalogue : {len(d['validators'])} validateurs, "
      f"{len(d['aux_validators'])} auxiliaires, "
      f"{len(d['normalizations'])} normalisations")
profiles = json.load(urllib.request.urlopen(base + "/api/profiles"))
noms = [p["name"] for p in profiles]
print(f"  [OK]   {len(noms)} profils chargés : {', '.join(noms[:6])}…")
PY

# écriture d'un profil utilisateur (jamais dans profiles/)
cat > /tmp/profil_vague3.json <<'JSON'
{"label": "Vague 3 — test", "fields": [
  {"key": "ref_test", "label": "Référence",
   "patterns": ["(?:REF|Réf)\\s*[:#]\\s*([A-Z0-9-]{4,})"]}]}
JSON
c=$(curl -s "${AUTH[@]}" -o /dev/null -w '%{http_code}' -X PUT \
     "$BASE/api/profiles/vague3_test" -H "Content-Type: application/json" \
     --data @/tmp/profil_vague3.json)
[ "$c" = "200" ] && ok "PUT /api/profiles/vague3_test → 200 (écrit dans data/profiles/)" \
  || ko "PUT /api/profiles/vague3_test → $c"
[ -f data/profiles/vague3_test.json ] && ok "fichier créé dans data/profiles/" \
  || ko "fichier absent de data/profiles/"
[ -f profiles/vague3_test.json ] && ko "ÉCRITURE DANS profiles/ (profils livrés) !" \
  || ok "profiles/ (livrés) non modifié"
rm -f /tmp/profil_vague3.json

echo ""
echo "=== 4. ESSAI À BLANC D'UN PROFIL (B5) ==="
posts "$BASE/api/profiles/test" \
  '{"profile": "vague3_test", "text": "Facture REF : AB-123-CD du 12/03/2019"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"  essai : {d['detected']}/{d['total']} champs détectés -> {d['fields']}\")"

echo ""
echo "=== 5. CALIBRATION (A2) — réajustement réel ==="
posts "$BASE/api/calibration/fit" '{"force": false}' > /tmp/calib.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/calib.json"))
print(f"  suite={d['suite']} — {d['n_samples']} paires étiquetées, "
      f"{d['n_positive']} correctes")
print(f"  méthode={d['method']} — active={d['active']}")
print(f"  note : {d['note']}")
if d["suite"] == "synthétique" and d["active"]:
    print("  [FAIL] une calibration synthétique ne doit PAS être active sans force")
else:
    print("  [OK]   garde-fou respecté (synthétique ⇒ inactif)")
PY
rm -f /tmp/calib.json

echo ""
echo "=== 6. TYPAGE DE ZONES (E2) ==="
python3 - <<'PY'
import sys
sys.path.insert(0, "src")
from pathlib import Path
from unocr.zone_typing import classify_zones
for f in ("tests/fixtures/photo_carte_grise.png", "tests/fixtures/table_pdf.pdf"):
    z = classify_zones(Path(f))
    kinds = {}
    for item in z:
        kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1
    print(f"  {Path(f).name:26s} {len(z):3d} zones {kinds if kinds else ''}")
    boxes = [i for i in z if i["kind"] == "checkbox"]
    if boxes:
        assert all("à confirmer" in i.get("note", "") for i in boxes)
        print(f"  [OK]   {len(boxes)} case(s) candidate(s) — "
              "heuristique géométrique, à confirmer")
    if any(i["kind"] in ("signature", "handwritten") for i in z):
        print("  [FAIL] capacité retirée de nouveau présente")
    else:
        print("  [OK]   aucune signature/manuscrit affirmée (capacité retirée)")
PY

echo ""
echo "=== 7. DIRECTION RTL (C3) ==="
python3 - <<'PY'
import sys
sys.path.insert(0, "src")
from pathlib import Path
from unocr.models import JobOptions
from unocr.pipeline import Pipeline
from unocr.direction import detect_direction
p = Path("tests/fixtures/photo_arabe.png")
if not p.is_file():
    print("  [FAIL] fixture arabe absente")
else:
    r = Pipeline().process_file(p, JobOptions(languages=["ara"], quality_mode="fast"))
    print(f"  document arabe -> direction={r.direction} "
          f"(page: {[pg.direction for pg in r.pages]})")
    print("  [OK]" if r.direction == "rtl" else "  [FAIL] RTL non détecté")
PY
grep -q 'data-i18n=' web/index.html && ok "$(grep -c 'data-i18n=' web/index.html) éléments traduisibles (data-i18n)" \
  || ko "aucun élément data-i18n"
for l in fr en ar; do
  grep -q "data-lang=\"$l\"" web/index.html && ok "bouton de langue '$l' présent" \
    || ko "bouton de langue '$l' absent"
done
node tests/ui_stub_check.js >/dev/null 2>&1 && ok "contrôle statique de l'UI" \
  || ko "contrôle statique de l'UI en échec"

echo ""
echo "=== 8. JETON (D3) — nécessite un redémarrage avec UNIOCR_TOKEN ==="
if [ -n "$UNOCR_TOKEN" ]; then
  c=$(code "$BASE/api/jobs")
  [ "$c" = "401" ] && ok "sans jeton : /api/jobs → 401" || ko "sans jeton : $c"
  c=$(code "$BASE/api/jobs" -H "Authorization: Bearer $UNOCR_TOKEN")
  [ "$c" = "200" ] && ok "avec jeton : /api/jobs → 200" || ko "avec jeton : $c"
else
  echo "  (ignoré — relancer avec UNIOCR_TOKEN=xxx ./benchmarks/verify_wave3.sh)"
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "Tous les contrôles de la vague 3 passent."
else
  echo "$FAIL contrôle(s) en échec."
fi
exit $FAIL
