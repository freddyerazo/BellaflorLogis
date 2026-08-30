# Arranca BLIS en local.
#
# El entorno virtual vive FUERA de OneDrive (ver CLAUDE.md): OneDrive
# deshidrata los archivos y rompe tanto git como los paquetes instalados.
#
#   .\scripts\dev.ps1              # http://localhost:8000
#   .\scripts\dev.ps1 -Port 8010   # otro puerto

param(
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$venv = "C:\dev\venvs\blis"
$python = Join-Path $venv "Scripts\python.exe"
$backend = Resolve-Path (Join-Path $PSScriptRoot "..\backend")

if (-not (Test-Path $python)) {
    Write-Host "No existe el entorno virtual en $venv" -ForegroundColor Red
    Write-Host "Crearlo con:" -ForegroundColor Yellow
    Write-Host "  python -m venv $venv"
    Write-Host "  & '$python' -m pip install -r '$backend\requirements.txt'"
    exit 1
}

if (-not (Test-Path (Join-Path $backend ".env"))) {
    Write-Host "Falta backend\.env - la app no podra conectarse a la base." -ForegroundColor Red
    exit 1
}

Set-Location $backend

$uvicornArgs = @("-m", "uvicorn", "app.main:app", "--port", $Port)
if (-not $NoReload) { $uvicornArgs += "--reload" }

Write-Host "BLIS en http://localhost:$Port  (Ctrl+C para detener)" -ForegroundColor Green
& $python @uvicornArgs
