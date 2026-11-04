# UniOCR — démarrage du serveur API + interface web (Windows)
#
#   .\scripts\run.ps1
#   .\scripts\run.ps1 -Port 8080
#
# Équivalent Windows de scripts/run_server.sh

[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$Host_ = "127.0.0.1",
    [string]$DataDir = "",
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if ($DataDir) {
    $env:UNOCR_DATA_DIR = $DataDir
    Write-Host "Données : $DataDir" -ForegroundColor DarkGray
}

$env:PYTHONPATH = "$Root\src;$env:PYTHONPATH"

$args = @("-m", "uvicorn", "unocr.api:app", "--host", $Host_, "--port", "$Port")
if ($Reload) { $args += "--reload" }

Write-Host ""
Write-Host "  UniOCR → http://localhost:$Port" -ForegroundColor White
Write-Host "  API (Swagger) → http://localhost:$Port/docs" -ForegroundColor DarkGray
Write-Host "  Ctrl+C pour arrêter." -ForegroundColor DarkGray
Write-Host ""

& python @args
exit $LASTEXITCODE
