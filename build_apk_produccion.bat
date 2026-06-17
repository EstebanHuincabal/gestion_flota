@echo off
setlocal enabledelayedexpansion
title Build APK - Produccion

echo.
echo  =====================================================
echo   BUILD APK DE PRODUCCION
echo   Servidor: http://157.180.85.17
echo  =====================================================
echo.

:: Posicionarse en la raiz del monorepo (donde esta este .bat)
cd /d "%~dp0"

:: ─────────────────────────────────────────
echo [1/4] Instalando dependencias npm...
:: ─────────────────────────────────────────
cd app_conductor
call npm install
if errorlevel 1 (
    echo.
    echo  ERROR: fallo npm install
    pause
    exit /b 1
)
cd ..

:: ─────────────────────────────────────────
echo.
echo [2/4] Compilando con Vite (modo produccion)...
:: ─────────────────────────────────────────

:: Reemplazar VITE_API_URL en .env con la URL de produccion y hacer backup
powershell -Command "Copy-Item .env .env.bak -Force; (Get-Content .env -Raw) -replace 'VITE_API_URL=[^\r\n]*', 'VITE_API_URL=http://157.180.85.17' | Set-Content .env -NoNewline"

cd app_conductor
call npm run build
set BUILD_ERR=%errorlevel%
cd ..

:: Restaurar .env original siempre, haya fallado o no
powershell -Command "if (Test-Path .env.bak) { Copy-Item .env.bak .env -Force; Remove-Item .env.bak -Force }"

if %BUILD_ERR% neq 0 (
    echo.
    echo  ERROR: fallo vite build
    pause
    exit /b 1
)

:: ─────────────────────────────────────────
echo.
echo [3/4] Sincronizando assets con Capacitor...
:: ─────────────────────────────────────────
cd app_conductor
call npx cap sync android
if errorlevel 1 (
    echo.
    echo  ERROR: fallo cap sync android
    pause
    exit /b 1
)

:: ─────────────────────────────────────────
echo.
echo [4/4] Construyendo APK debug...
:: ─────────────────────────────────────────
cd android
call gradlew.bat assembleDebug
if errorlevel 1 (
    echo.
    echo  ERROR: fallo gradle assembleDebug
    echo  Asegurate de tener ANDROID_HOME configurado y Java JDK instalado.
    pause
    exit /b 1
)

:: ─────────────────────────────────────────
echo.
echo  =====================================================
echo   APK generado exitosamente:
echo.
echo   app_conductor\android\app\build\outputs\apk\debug\
echo                        app-debug.apk
echo  =====================================================
echo.

:: Abrir la carpeta con el APK en el explorador
start "" "%~dp0app_conductor\android\app\build\outputs\apk\debug"

pause
