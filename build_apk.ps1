# build_apk.ps1 - Compila la app de conductores y genera el APK de debug
#
# Pasos:
#   1. Detecta tu IP local y actualiza .env
#   2. npm run build
#   3. npx cap sync android
#   4. gradlew assembleDebug
#   5. Copia el APK a la raiz del proyecto y abre la carpeta

$ErrorActionPreference = 'Stop'

$root       = $PSScriptRoot
$appDir     = Join-Path $root "app_conductor"
$androidDir = Join-Path $appDir "android"
$envFile    = Join-Path $root ".env"          # Vite lee el .env de la raiz del monorepo
$apkSrc     = Join-Path $androidDir "app\build\outputs\apk\debug\app-debug.apk"
$apkDest    = Join-Path $root "app-conductor-debug.apk"

function Write-Step { param($msg) Write-Host "" ; Write-Host ">> $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "   OK  $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "   !   $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "" ; Write-Host "ERROR: $msg" -ForegroundColor Red ; exit 1 }

Write-Host ""
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "   BUILD APK - App Conductores            " -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta

# 1. Detectar IP local
Write-Step "Detectando IP local..."

$ip = $null
$candidatos = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*"
    } |
    Sort-Object {
        if     ($_.InterfaceAlias -match "Wi-Fi|WiFi|Inalambric") { 0 }
        elseif ($_.InterfaceAlias -match "Ethernet|Local")        { 1 }
        else                                                        { 2 }
    }

if ($candidatos) { $ip = $candidatos[0].IPAddress }

if (-not $ip) {
    Write-Warn "No se detecto IP automaticamente."
    $ip = Read-Host "   Ingresa tu IP local (ej: 192.168.1.100)"
}

Write-Ok "IP: $ip"
Write-Ok "Backend URL: http://${ip}:8000"

# 2. Actualizar solo la linea VITE_API_URL en el .env raiz (sin tocar el resto)
Write-Step "Actualizando .env..."

$envContent = Get-Content -Path $envFile -Raw
$nuevaLinea = "VITE_API_URL=http://${ip}:8000"

if ($envContent -match "(?m)^VITE_API_URL=.*$") {
    # Reemplaza la linea existente
    $envContent = $envContent -replace "(?m)^VITE_API_URL=.*$", $nuevaLinea
} else {
    # Si no existe la linea, la agrega al final
    $envContent = $envContent.TrimEnd() + "`r`n$nuevaLinea`r`n"
}

Set-Content -Path $envFile -Value $envContent -Encoding UTF8 -NoNewline
Write-Ok ".env actualizado -> $nuevaLinea"

# 3. npm run build
Write-Step "Compilando frontend Vue..."
Set-Location $appDir

npm run build
if ($LASTEXITCODE -ne 0) { Write-Fail "npm run build fallo." }
Write-Ok "Frontend compilado."

# 4. cap sync android
Write-Step "Sincronizando con Android..."

npx cap sync android
if ($LASTEXITCODE -ne 0) { Write-Fail "cap sync fallo." }
Write-Ok "Sincronizacion completada."

# 5. Gradle assembleDebug
Write-Step "Generando APK con Gradle..."
Set-Location $androidDir

.\gradlew.bat assembleDebug
if ($LASTEXITCODE -ne 0) { Write-Fail "Gradle fallo. Revisa los mensajes de arriba." }
Write-Ok "APK generado."

# 6. Copiar APK a la raiz
Write-Step "Copiando APK..."

if (Test-Path $apkSrc) {
    Copy-Item -Path $apkSrc -Destination $apkDest -Force
    Write-Ok "APK listo en: $apkDest"
    Start-Process explorer.exe -ArgumentList "/select,`"$apkDest`""
} else {
    Write-Warn "No se encontro el APK en: $apkSrc"
    Write-Warn "Buscalo manualmente en: $androidDir\app\build\outputs\apk\debug\"
}

# Fin
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "   APK listo para instalar!               " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Pasos para instalar en el telefono:" -ForegroundColor White
Write-Host "  1. Pasa 'app-conductor-debug.apk' al telefono" -ForegroundColor Gray
Write-Host "     (cable USB, WhatsApp, Drive, etc.)" -ForegroundColor Gray
Write-Host "  2. Abre el archivo en el telefono y toca Instalar" -ForegroundColor Gray
Write-Host "  3. Si pide permiso para apps desconocidas, acepta" -ForegroundColor Gray
Write-Host ""
Write-Host "Inicia el backend con:" -ForegroundColor White
Write-Host "  python manage.py runserver 0.0.0.0:8000" -ForegroundColor Gray
Write-Host ""
