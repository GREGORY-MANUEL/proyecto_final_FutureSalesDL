@echo off
setlocal
cd /d "%~dp0"

echo ======================================================
echo Generador de Ordenes de Compra - Iniciando...
echo ======================================================

:: Verificar si el entorno virtual existe
if exist ".venv" goto :activate
echo [ERROR] No se encontro el entorno virtual (.venv).
echo Intentando crear el entorno virtual...
python -m venv .venv
if errorlevel 1 goto :error_venv
goto :activate

:error_venv
echo [ERROR CRITICO] No se pudo crear el entorno virtual. Asegurese de tener Python instalado.
pause
exit /b 1

:activate
call ".venv\Scripts\activate"

:: Verificar si streamlit esta instalado
".venv\Scripts\python.exe" -c "import streamlit" 2>NUL
if not errorlevel 1 goto :start_app

echo [INFO] Instalando librerias necesarias (esto puede tardar unos minutos)...
".venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 goto :error_libs

:start_app
:: Ejecutar streamlit en modo silencioso
echo [INFO] Iniciando el servidor de la aplicacion...
start /b "" ".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --browser.gatherUsageStats false --server.port 8501

:: Esperar a que el servidor inicie
echo [INFO] Esperando a que la pagina este lista...
timeout /t 7 /nobreak > NUL

:: Abrir el navegador
echo [INFO] Abriendo navegador en http://localhost:8501
start http://localhost:8501

echo [OK] Aplicacion iniciada correctamente.
timeout /t 3 > NUL
exit

:error_libs
echo [ERROR] Fallo la instalacion de librerias. Verifique su conexion a internet.
pause
exit /b 1
