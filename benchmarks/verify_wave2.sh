#!/usr/bin/env bash
# Vérification manuelle des endpoints de la vague 2 (hors suite de tests).
# Usage : ./benchmarks/verify_wave2.sh   (serveur démarré)
cd "$(dirname "$0")/.." || exit 1
BASE="${UNOCR_BASE:-http://127.0.0.1:8000}"

echo "=== 1. LOT ==="
curl -s -X POST "$BASE/api/batches" \
  -F "files=@tests/fixtures/text_pdf.pdf" \
  -F "files=@tests/fixtures/bl_port.pdf" \
  -F "profile=invoice" -F "quality_mode=fast" -F "export_formats=json,txt" \
  -o /tmp/batch.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/batch.json"))
print(f"  batch {d['batch_id']} -> {d['accepted']} acceptes, {len(d['rejected'])} refuses")
for j in d["jobs"]:
    print(f"    - {j['filename']:18s} {j['status']:9s} cached={j['cached']}")
print("  IDS=" + ",".join(j["job_id"] for j in d["jobs"]))
PY

sleep 10

echo ""
echo "=== 2. DEDUPLICATION (memes fichiers re-deposes) ==="
curl -s -X POST "$BASE/api/batches" \
  -F "files=@tests/fixtures/text_pdf.pdf" \
  -F "profile=invoice" -F "quality_mode=fast" -o /tmp/batch2.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/batch2.json"))
for j in d["jobs"]:
    print(f"    - {j['filename']:18s} {j['status']:9s} cached={j['cached']}")
PY

echo ""
echo "=== 3. EXPORT GROUPE ==="
for f in csv json txt xlsx; do
  curl -s -o "/tmp/lot.$f" -w "  $f : HTTP %{http_code} - %{size_download} octets\n" \
    "$BASE/api/batches/export/$f?ids=job_6fb3cf53b990,job_d5b61a94da0f"
done
head -2 /tmp/lot.csv | sed 's/^/    /'
python3 - <<'PY'
import json, openpyxl
wb = openpyxl.load_workbook("/tmp/lot.xlsx")
print(f"  xlsx : {len(wb.sheetnames)} feuilles -> {wb.sheetnames}")
d = json.load(open("/tmp/lot.json"))
print(f"  json : {len(d)} documents, {len(d[0]['fields'])} champs dans le premier")
PY

echo ""
echo "=== 4. AUDIT ==="
curl -s -o /tmp/audit.json "$BASE/api/audit?limit=5"
python3 - <<'PY'
import json
d = json.load(open("/tmp/audit.json"))
print(f"  {d['returned']} evenements, types : {d['events'][:6]}")
for e in d["entries"][:3]:
    print(f"    - {e['event']}")
PY

echo ""
echo "=== 5. EXPORT CIBLE ==="
JID=$(curl -s "$BASE/api/jobs?limit=1" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
CHAMP=$(curl -s "$BASE/api/jobs/$JID/result" | python3 -c 'import json,sys; print(list(json.load(sys.stdin)["fields"])[0])')
echo "  job=$JID champ=$CHAMP"
curl -s -o /tmp/sel.csv -w "  csv selectionne : HTTP %{http_code} - %{size_download} octets\n" \
  "$BASE/api/jobs/$JID/export/csv/selected?fields=$CHAMP"
head -2 /tmp/sel.csv | sed 's/^/    /'

echo ""
echo "=== 6. DOSSIER SURVEILLE ==="
mkdir -p /tmp/unocr_watch && cp tests/fixtures/text_pdf.pdf /tmp/unocr_watch/surveille.pdf
curl -s -X PUT "$BASE/api/watch" -H "Content-Type: application/json" \
  -d '{"enabled":true,"path":"/tmp/unocr_watch","profile":"invoice","quality_mode":"fast"}' \
  -o /tmp/watch.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/watch.json"))
print(f"  active={d['enabled']} dossier={d['path']}")
PY
echo "  balayage 1 (memorise la taille) :"
curl -s -X POST "$BASE/api/watch/scan" | sed 's/^/    /'
sleep 2
echo "  balayage 2 (taille stable) :"
curl -s -X POST "$BASE/api/watch/scan" | sed 's/^/    /'
sleep 12
curl -s -X PUT "$BASE/api/watch" -H "Content-Type: application/json" \
  -d '{"enabled":false}' -o /tmp/watch_off.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/watch_off.json"))
print(f"  desactive. traite={d['processed']} doublon={d['skipped_duplicates']} refuse={d['rejected']}")
PY
