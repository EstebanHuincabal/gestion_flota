$root     = $PSScriptRoot
$backend  = Join-Path $root "gestion_backend"
$frontend = Join-Path $root "gestion-frontend"

if (Get-Command wt -ErrorAction SilentlyContinue) {
    # Windows Terminal: abre dos pestanas
    wt --title "Django Backend" -d $backend pwsh -NoExit -Command "python manage.py runserver" `; new-tab --title "Vite Frontend" -d $frontend pwsh -NoExit -Command "npm run dev"
} else {
    # Fallback: dos ventanas PowerShell separadas
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backend'; python manage.py runserver"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontend'; npm run dev"
}
