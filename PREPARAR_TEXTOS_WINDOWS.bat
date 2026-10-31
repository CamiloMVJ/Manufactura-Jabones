@echo off
setlocal
cd /d "%~dp0"
echo Cierra primero el servidor con Ctrl+C.
echo La reparacion crea un respaldo y conserva los datos existentes.
pause
if not exist ".venv\Scripts\python.exe" (
  echo No se encontro el entorno del proyecto. Ejecuta desde la carpeta donde instalaste Espuma.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" reparar_textos.py
if errorlevel 1 (
  echo No se completo la reparacion. Revisa el mensaje anterior.
  pause
  exit /b 1
)
echo Vuelve a abrir INICIAR_WINDOWS.bat y actualiza el navegador con Ctrl+F5.
pause
