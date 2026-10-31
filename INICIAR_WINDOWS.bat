@echo off
setlocal
cd /d "%~dp0"
echo ESPUMA JABONERIA - Preparacion e inicio
echo.
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Instala Python 3.10 o posterior y habilita "Add Python to PATH".
    pause
    exit /b 1
  )
  set "ERP_PYTHON=python"
) else (
  set "ERP_PYTHON=py -3"
)
%ERP_PYTHON% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo Se necesita Python 3.10 o posterior. La adaptacion se verifico con Python 3.12 en Linux.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  %ERP_PYTHON% -m venv .venv
  if errorlevel 1 (
    echo No se pudo crear el entorno virtual.
    pause
    exit /b 1
  )
)
if not exist ".venv\.espuma-ready" (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo No se pudieron instalar las dependencias. Revisa Internet y vuelve a ejecutar este archivo.
    pause
    exit /b 1
  )
  echo ok>".venv\.espuma-ready"
)
if not exist ".env" copy /y ".env.example" ".env" >nul
".venv\Scripts\python.exe" preparar.py
if errorlevel 1 (
  echo Revisa el mensaje de preparacion antes de continuar.
  pause
  exit /b 1
)
echo.
echo Abre http://127.0.0.1:8000 en tu navegador.
echo Manten esta ventana abierta. Para detener el servidor, presiona Ctrl+C.
echo.
".venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
pause

