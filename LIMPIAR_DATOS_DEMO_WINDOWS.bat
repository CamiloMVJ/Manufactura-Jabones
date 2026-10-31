@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No se encontro el entorno. Ejecuta este archivo dentro del proyecto instalado.
  pause
  exit /b 1
)
echo Pura Cocos - Limpieza de datos DEMO antiguos
echo El servidor debe estar detenido. Se creara un respaldo antes de borrar.
".venv\Scripts\python.exe" limpiar_datos_demo.py %*
if errorlevel 1 (
  echo La limpieza no se completo. Revisa el mensaje anterior.
  pause
  exit /b 1
)
echo Proceso terminado. Revisa el resumen de registros eliminados y conservados.
pause
