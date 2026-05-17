$root           = $PSScriptRoot
$backend        = Join-Path $root "gestion_backend"
$frontend       = Join-Path $root "gestion-frontend"
$backendScript  = Join-Path $backend  "start.ps1"
$frontendScript = Join-Path $frontend "start.ps1"

if (Get-Command wt -ErrorAction SilentlyContinue) {
    # Windows Terminal: abre dos pestañas
    wt --title "Django Backend" -d "$backend" pwsh -NoExit -File "$backendScript" `; new-tab --title "Vite Frontend" -d "$frontend" pwsh -NoExit -File "$frontendScript"
} else {
    # Fallback: dos ventanas PowerShell separadas
    Start-Process powershell -ArgumentList @("-NoExit", "-File", $backendScript)
    Start-Process powershell -ArgumentList @("-NoExit", "-File", $frontendScript)
}
