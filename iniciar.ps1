$root           = $PSScriptRoot
$backend        = Join-Path $root "gestion_backend"
$frontend       = Join-Path $root "gestion-frontend"
$appConductor   = Join-Path $root "app_conductor"

$backendScript       = Join-Path $backend      "start.ps1"
$frontendScript      = Join-Path $frontend     "start.ps1"
$appConductorScript  = Join-Path $appConductor "start.ps1"

if (Get-Command wt -ErrorAction SilentlyContinue) {
    # Windows Terminal: abre tres pestañas
    wt --title "Django Backend"    -d "$backend"      pwsh -NoExit -File "$backendScript" `; `
       new-tab --title "Web Frontend"     -d "$frontend"     pwsh -NoExit -File "$frontendScript" `; `
       new-tab --title "App Conductores"  -d "$appConductor" pwsh -NoExit -File "$appConductorScript"
} else {
    # Fallback: tres ventanas PowerShell separadas
    Start-Process powershell -ArgumentList @("-NoExit", "-File", $backendScript)
    Start-Process powershell -ArgumentList @("-NoExit", "-File", $frontendScript)
    Start-Process powershell -ArgumentList @("-NoExit", "-File", $appConductorScript)
}
