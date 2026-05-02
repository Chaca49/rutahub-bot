"""
Carga datos de prueba en la base de datos.
  python scripts/seed_data.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.models import Carga

cargas_ejemplo = [
    Carga(origen="Neuquén", destino="Buenos Aires", tipo_carga="General", peso_toneladas=18.0, fecha_retiro="02/06", contacto_nombre="Juan Pérez", contacto_telefono="+5491156781234"),
    Carga(origen="Neuquén", destino="Rosario", tipo_carga="Refrigerada", peso_toneladas=12.5, fecha_retiro="03/06", contacto_nombre="Logística Sur", contacto_telefono="+5491145671234"),
    Carga(origen="Mendoza", destino="Buenos Aires", tipo_carga="Parcial", peso_toneladas=5.0, fecha_retiro="01/06", contacto_nombre="Bodega Norte", contacto_telefono="+5492614321234"),
    Carga(origen="Córdoba", destino="Rosario", tipo_carga="General", peso_toneladas=20.0, fecha_retiro="mañana", contacto_nombre="Distribuidora Cel", contacto_telefono="+5493514561234"),
    Carga(origen="Buenos Aires", destino="Neuquén", tipo_carga="Materiales", peso_toneladas=15.0, fecha_retiro="05/06", contacto_nombre="Construcciones SA", contacto_telefono="+5491167891234"),
]

if __name__ == "__main__":
    db = SessionLocal()
    try:
        for carga in cargas_ejemplo:
            db.add(carga)
        db.commit()
        print(f"✅ {len(cargas_ejemplo)} cargas de ejemplo cargadas.")
    finally:
        db.close()
