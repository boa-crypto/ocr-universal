# UniOCR — installation sur Windows (PowerShell 5.1+ / PowerShell 7+)
#
#   .\scripts\install.ps1
#
# Installe les dépendances Python et vérifie l'environnement. Les binaires
# système (Tesseract, Poppler) ne sont PAS installés automatiquement : ils
# nécessitent des droits administrateur. Le script les détecte et affiche
# exactement quoi télécharger s'ils manquent.

[CmdletBinding()]
param(
    [switch]$SkipPip,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    !!   $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "    XX   $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "  UniOCR — installation Windows" -ForegroundColor White
Write-Host "  ================================" -ForegroundColor DarkGray

# ── 1. Python ────────────────────────────────────────────────────────────────
Write-Step "Vérification de Python"
try {
    $pyVersion = & $Python --version 2>&1
    Write-Ok $pyVersion
} catch {
    Write-Err "Python introuvable ('$Python'). Installez Python 3.11+ depuis python.org,"
    Write-Err "en cochant « Add Python to PATH »."
    exit 1
}

# ── 2. Dépendances Python ────────────────────────────────────────────────────
if (-not $SkipPip) {
    Write-Step "Installation des dépendances Python"
    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Write-Err "pip introuvable"; exit 1 }

    & $Python -m pip install -r (Join-Path $Root "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "installation depuis requirements.txt échouée, repli sur pyproject.toml"
        & $Python -m pip install (Join-Path $Root ".")
        if ($LASTEXITCODE -ne 0) { Write-Err "installation impossible"; exit 1 }
    }
    Write-Ok "dépendances Python installées"
} else {
    Write-Warn "installation pip ignorée (-SkipPip)"
}

# ── 3. Binaires système ──────────────────────────────────────────────────────
Write-Step "Vérification des binaires système"

$tesseract = Get-Command tesseract -ErrorAction SilentlyContinue
if ($tesseract) {
    Write-Ok "Tesseract : $(& tesseract --version 2>&1 | Select-Object -First 1)"
} else {
    Write-Warn "Tesseract absent — sans lui, aucun OCR raster n'est possible."
    Write-Host ""
    Write-Host "    Installez-le (une des options) :" -ForegroundColor White
    Write-Host "      • winget install UB-Mannheim.TesseractOCR" -ForegroundColor Gray
    Write-Host "      • chocolatey install tesseract" -ForegroundColor Gray
    Write-Host "      • https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    Après installation, ajoutez le dossier de Tesseract au PATH" -ForegroundColor Gray
    Write-Host "    et vérifiez les modèles de langue (fra, eng, ara, ...)." -ForegroundColor Gray
}

$pdftoppm = Get-Command pdftoppm -ErrorAction SilentlyContinue
if ($pdftoppm) {
    Write-Ok "Poppler : trouvé (pdftoppm)"
} else {
    Write-Warn "Poppler absent — requis pour les PDF."
    Write-Host "      • winget install oschwartz10612.Poppler" -ForegroundColor Gray
    Write-Host "      • https://github.com/oschwartz10612/poppler-windows/releases" -ForegroundColor Gray
}

# ── 4. Diagnostic ────────────────────────────────────────────────────────────
Write-Step "Diagnostic de l'environnement"
$env:PYTHONPATH = "$Root\src;$env:PYTHONPATH"
& $Python -m unocr.cli diagnose
$diag = $LASTEXITCODE

# ── 5. Bilan ─────────────────────────────────────────────────────────────────
Write-Host ""
if ($diag -eq 0 -and $tesseract) {
    Write-Host "  Installation terminée." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Démarrer le serveur :" -ForegroundColor White
    Write-Host "    .\scripts\run.ps1" -ForegroundColor Gray
    Write-Host "  Puis ouvrir http://localhost:8000" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "  Installation incomplète — voir les avertissements ci-dessus." -ForegroundColor Yellow
    Write-Host "  UniOCR fonctionnera une fois les binaires manquants installés." -ForegroundColor Yellow
    exit 1
}
