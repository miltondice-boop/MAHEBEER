from pathlib import Path
import os

APP_NAME = "MAHEBEER - Recetas y Costos"
DATA_DIR = Path(os.getenv("MAHEBEER_DATA_DIR", Path.home() / "Documents" / "MAHEBEER"))
DB_PATH = DATA_DIR / "mahebeer.sqlite3"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"
MEASURES = ("Gramos", "Mililitros", "Unidades")
