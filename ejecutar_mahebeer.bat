@echo off
setlocal
cd /d "%~dp0"
echo Iniciando MAHEBEER - Recetas y Costos...
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo ERROR: No se encontro Python en este PC.
  echo Instala Python 3.11 o superior desde https://www.python.org/downloads/
  echo Marca la opcion "Add python.exe to PATH" durante la instalacion.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual local...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
echo Instalando/actualizando dependencias...
python -m pip install --upgrade pip
python -m pip install -e .
echo.
echo Abriendo MAHEBEER...
python -m mahebeer.app
pause
