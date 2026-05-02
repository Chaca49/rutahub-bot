"""
Crea todas las tablas en la base de datos.
Ejecutar una sola vez al iniciar el proyecto:
  python scripts/create_tables.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine, Base
from app.models.models import Usuario, Carga, Viaje  # noqa: importar para registrar modelos

if __name__ == "__main__":
    print("Creando tablas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas correctamente.")
