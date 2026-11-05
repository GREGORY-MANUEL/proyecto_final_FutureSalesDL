@echo off
chcp 65001 > nul
setlocal EnableExtensions
set "ROOT=%~dp0"
set "SPEC_FILE=%ROOT%app.spec"
set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"
set "DIST_DIR=%ROOT%dist\GeneradorOC"
set "STAGING_ROOT=%ROOT%build\portable_staging"
set "STAGING_DIR=%STAGING_ROOT%\GeneradorOC"
set "PREVIOUS_DIR=%ROOT%build\portable_previous_%RANDOM%_%RANDOM%"
set "PIP_CMD=%PYTHON_EXE% -m pip"
set "PYINSTALLER_CMD=%PYTHON_EXE% -m PyInstaller"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"

pushd "%ROOT%"

title Generador OC — Construcción de App Portable
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   GENERADOR DE ORDENES DE COMPRA — BUILD PORTABLE   ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

REM ── Verificar que exista la especificación de PyInstaller ───────────────
if not exist "%SPEC_FILE%" (
    echo  [ERROR] No se encontro %SPEC_FILE%
    pause
    exit /b 1
)

REM ── Crear/usar entorno virtual ───────────────────────────────────────────
if not exist "%PYTHON_EXE%" (
    echo  [1/5] Creando entorno virtual .venv...
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if not exist "%PYTHON_EXE%" (
        echo  [ERROR] No se pudo crear el entorno virtual .venv
        pause
        exit /b 1
    )
) else (
    echo  [1/5] Usando entorno virtual existente...
)

echo        OK

echo.

REM ── Instalar/actualizar dependencias ─────────────────────────────────────
echo  [2/5] Verificando e instalando dependencias (puede tardar unos minutos)...
"%PYTHON_EXE%" -m pip install --upgrade pip wheel setuptools --quiet --disable-pip-version-check --no-input
if errorlevel 1 (
    echo  [ERROR] No se pudo preparar pip, wheel y setuptools.
    pause
    exit /b 1
)
"%PYTHON_EXE%" -m pip install -r requirements.txt --quiet --disable-pip-version-check --no-input
if errorlevel 1 (
    echo  [ERROR] No se pudieron instalar las dependencias de requirements.txt.
    pause
    exit /b 1
)
"%PYTHON_EXE%" -m pip install pyinstaller pywebview --upgrade --quiet --disable-pip-version-check --no-input
if errorlevel 1 (
    echo  [ERROR] No se pudieron instalar PyInstaller y pywebview.
    pause
    exit /b 1
)

REM ── Verificar dependencias críticas ─────────────────────────────────────
"%PYTHON_EXE%" -c "import streamlit, PyInstaller, torch, sklearn, webview, rapidfuzz, plotly, generar_historial; import core.prediccion_ventas" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Faltan dependencias criticas y no se pudieron instalar.
    echo  Asegurese de tener conexion a internet o instalar en el entorno:
    echo  streamlit, pyinstaller, torch, scikit-learn, webview, rapidfuzz, plotly
    echo  y los modulos locales generar_historial y core.prediccion_ventas
    pause
    exit /b 1
)
echo        OK (dependencias verificadas)
echo.

REM ── Preparar staging sin tocar el portable existente ──────────────────────
echo  [3/5] Preparando carpeta temporal de construccion...
if exist "%STAGING_ROOT%" rmdir /S /Q "%STAGING_ROOT%"
if exist "build\GeneradorOC" rmdir /S /Q "build\GeneradorOC"
mkdir "%STAGING_ROOT%"
if errorlevel 1 (
    echo  [ERROR] No se pudo crear la carpeta temporal de construccion.
    pause
    exit /b 1
)
echo        OK
echo.

REM ── Ejecutar PyInstaller ──────────────────────────────────────────────────
echo  [4/5] Construyendo ejecutable (puede tardar 3-8 minutos)...
echo        Por favor espera...
echo.
"%PYTHON_EXE%" -m PyInstaller app.spec --noconfirm --clean --workpath "build\GeneradorOC" --distpath "%STAGING_ROOT%"
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] PyInstaller finalizo con errores.
    pause
    exit /b 1
)
if not exist "%STAGING_DIR%\GeneradorOC.exe" (
    echo  [ERROR] PyInstaller termino, pero no genero GeneradorOC.exe.
    pause
    exit /b 1
)
if not exist "%STAGING_DIR%\_internal\app.py" (
    echo  [ERROR] El paquete no contiene _internal\app.py requerido por el launcher.
    pause
    exit /b 1
)

REM ── Copiar archivos adicionales de runtime ───────────────────────────────
echo  [5/5] Copiando archivos necesarios para la ejecucion...
if exist "core" xcopy "core" "%STAGING_DIR%\core" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia
if exist "ui" xcopy "ui" "%STAGING_DIR%\ui" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia
if exist "assets" xcopy "assets" "%STAGING_DIR%\assets" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia
if exist "archivos" xcopy "archivos" "%STAGING_DIR%\archivos" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia
if exist "backups" xcopy "backups" "%STAGING_DIR%\backups" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia
if exist "orden de compra" xcopy "orden de compra" "%STAGING_DIR%\orden de compra" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia
if exist "streamlit" xcopy "streamlit" "%STAGING_DIR%\streamlit" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia

for /d /r "%STAGING_DIR%" %%D in (__pycache__) do if exist "%%D" rmdir /S /Q "%%D"

for %%F in (app.py launcher.py login.py registro.py mantenimiento.py) do (
    if not exist "%%F" goto :error_copia
    copy /Y "%%F" "%STAGING_DIR%\%%F" > nul
    if errorlevel 1 goto :error_copia
)

if not exist "%STAGING_DIR%\core\ia_engine.py" goto :error_copia
if not exist "%STAGING_DIR%\ui\styles.py" goto :error_copia
if not exist "%STAGING_DIR%\assets\icono_personal.png" goto :error_copia
if not exist "%STAGING_DIR%\streamlit\config.toml" goto :error_copia

REM ── Conservar datos mutables del portable anterior ────────────────────────
if exist "%DIST_DIR%\gctech.db" (
    copy /Y "%DIST_DIR%\gctech.db" "%STAGING_DIR%\gctech.db" > nul
    if errorlevel 1 goto :error_copia
) else if exist "gctech.db" (
    copy /Y "gctech.db" "%STAGING_DIR%\gctech.db" > nul
    if errorlevel 1 goto :error_copia
)
if exist "%DIST_DIR%\backups" xcopy "%DIST_DIR%\backups" "%STAGING_DIR%\backups" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia
if exist "%DIST_DIR%\orden de compra" xcopy "%DIST_DIR%\orden de compra" "%STAGING_DIR%\orden de compra" /E /I /Y /Q > nul
if errorlevel 2 goto :error_copia
if exist "%DIST_DIR%\core\perfiles_custom.json" (
    copy /Y "%DIST_DIR%\core\perfiles_custom.json" "%STAGING_DIR%\core\perfiles_custom.json" > nul
    if errorlevel 1 goto :error_copia
)
if exist "%DIST_DIR%\archivos\data2\datasets_entrenamiento" (
    xcopy "%DIST_DIR%\archivos\data2\datasets_entrenamiento" "%STAGING_DIR%\archivos\data2\datasets_entrenamiento" /E /I /Y /Q > nul
    if errorlevel 2 goto :error_copia
)

REM ── Publicar solo despues de validar el nuevo paquete ─────────────────────
taskkill /f /im "GeneradorOC.exe" 2>nul
if not exist "%ROOT%dist" (
    mkdir "%ROOT%dist"
    if errorlevel 1 goto :error_publicacion
)
if exist "%DIST_DIR%" (
    move "%DIST_DIR%" "%PREVIOUS_DIR%" > nul
    if errorlevel 1 goto :error_publicacion
)
move "%STAGING_DIR%" "%DIST_DIR%" > nul
if errorlevel 1 (
    if exist "%PREVIOUS_DIR%" move "%PREVIOUS_DIR%" "%DIST_DIR%" > nul
    goto :error_publicacion
)
if exist "%PREVIOUS_DIR%" rmdir /S /Q "%PREVIOUS_DIR%"

REM ── Verificar resultado ───────────────────────────────────────────────────
echo.
if exist "%DIST_DIR%\GeneradorOC.exe" (
    echo  ╔══════════════════════════════════════════════════════╗
    echo  ║              ¡BUILD EXITOSO!                         ║
    echo  ║                                                      ║
    echo  ║  Ejecutable: dist\GeneradorOC\GeneradorOC.exe        ║
    echo  ║                                                      ║
    echo  ║  Para distribuir: copia toda la carpeta              ║
    echo  ║  dist\GeneradorOC\ a donde quieras.                  ║
    echo  ╚══════════════════════════════════════════════════════╝
    echo.
    echo  Abriendo carpeta con el resultado...
    explorer "%DIST_DIR%"
) else (
    echo  ╔══════════════════════════════════════════════════════╗
    echo  ║  ERROR: No se genero el ejecutable.                  ║
    echo  ║  Revisa los mensajes de error arriba.                ║
    echo  ╚══════════════════════════════════════════════════════╝
)

echo.
pause

popd
endlocal
exit /b 0

:error_copia
echo  [ERROR] No se pudieron copiar o validar todos los archivos del paquete.
echo  El portable existente no fue reemplazado.
pause
exit /b 1

:error_publicacion
echo  [ERROR] No se pudo publicar el nuevo paquete portable.
echo  Se intento restaurar la carpeta portable anterior.
pause
exit /b 1
