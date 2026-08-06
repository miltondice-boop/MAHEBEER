# Cómo encontrar y ejecutar MAHEBEER en Windows

## 1. Dónde poner la carpeta

Copia la carpeta completa del proyecto en una ubicación fácil de encontrar, por ejemplo:

```text
C:\MAHEBEER
```

Dentro de esa carpeta debes ver estos archivos:

```text
C:\MAHEBEER\ejecutar_mahebeer.bat
C:\MAHEBEER\README.md
C:\MAHEBEER\pyproject.toml
C:\MAHEBEER\mahebeer\app.py
```

## 2. Forma más fácil de ejecutar

Haz doble clic en:

```text
ejecutar_mahebeer.bat
```

Ese archivo hace automáticamente lo siguiente:

1. Entra a la carpeta donde está la app.
2. Verifica que exista Python.
3. Crea el entorno virtual `.venv` si no existe.
4. Instala las dependencias.
5. Lanza la aplicación con `python -m mahebeer.app`.

## 3. Si prefieres PowerShell

Abre PowerShell y ejecuta:

```powershell
cd C:\MAHEBEER
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m mahebeer.app
```

## 4. Dónde se guardan los datos

La base de datos y los reportes se guardan automáticamente en:

```text
C:\Users\TU_USUARIO\Documents\MAHEBEER
```

Archivos importantes generados por la app:

```text
mahebeer.sqlite3
backups\
exports\
```

## 5. Si no encuentras la carpeta

En Windows, abre el Explorador de archivos y busca:

```text
ejecutar_mahebeer.bat
```

Cuando aparezca el archivo, haz clic derecho y selecciona **Abrir ubicación del archivo**.
