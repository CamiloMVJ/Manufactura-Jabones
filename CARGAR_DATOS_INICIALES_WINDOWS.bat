@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta INICIAR_WINDOWS.bat para preparar el entorno.
  pause
  exit /b 1
)
echo Pura Cocos - Carga inicial ampliada
echo Cierra el servidor antes de continuar.
echo Contactos ficticios y cantidades propuestas: revisa data\negocio_inicial.json.
".venv\Scripts\python.exe" cargar_datos_iniciales.py %*
if errorlevel 1 (
  echo La carga no se completo. Revisa el mensaje anterior.
  pause
  exit /b 1
)
echo Carga terminada. Inicia el sistema y actualiza el navegador.
pause
