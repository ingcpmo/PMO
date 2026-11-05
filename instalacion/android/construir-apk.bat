@echo off
REM Construye la app Android "QSG Campo" (APK) apuntando a su servidor de QSG PMO.
REM   construir-apk.bat http://192.168.1.50:8080
REM Requisitos: Node 22+, JDK 21 y Android SDK (Android Studio los instala).
REM Si no quiere instalar nada, use la opcion en la nube (GitHub Actions) del README.
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set SERVIDOR=%~1
if "%SERVIDOR%"=="" set /p SERVIDOR=Direccion de QSG PMO (ej. http://192.168.1.50:8080): 

where node >nul 2>nul || (echo Falta Node.js 22 o superior: https://nodejs.org & pause & exit /b 1)
if "%ANDROID_HOME%"=="" if exist "%LOCALAPPDATA%\Android\Sdk" set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
if "%ANDROID_HOME%"=="" (echo Falta el Android SDK. Instale Android Studio y abralo una vez. & pause & exit /b 1)
if "%JAVA_HOME%"=="" if exist "%ProgramFiles%\Android\Android Studio\jbr" set JAVA_HOME=%ProgramFiles%\Android\Android Studio\jbr

call npm install --no-audit --no-fund || goto error
node preparar.mjs "%SERVIDOR%" || goto error
if not exist android call npx cap add android || goto error
call npx cap sync android || goto error
node preparar.mjs --android || goto error
pushd android
call gradlew.bat --no-daemon assembleDebug || (popd & goto error)
popd
if not exist salida mkdir salida
copy /y android\app\build\outputs\apk\debug\app-debug.apk salida\QSG-Campo.apk >nul
echo.
echo Listo: %CD%\salida\QSG-Campo.apk
echo Copielo al celular (cable, Drive o WhatsApp) y abralo para instalar.
pause
exit /b 0

:error
echo.
echo Algo fallo. Copie lo que aparece arriba y envielo para revisarlo.
pause
exit /b 1
