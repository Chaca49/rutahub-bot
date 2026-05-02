"""
Reset de usuario por número de teléfono.
Útil para testing — borra el usuario y toda su data temporal.

Uso:
  python scripts/reset_usuario.py +5491112345678
  python scripts/reset_usuario.py (sin argumento → lista todos los usuarios)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.models import Usuario, Viaje


def listar_usuarios(db):
    usuarios = db.query(Usuario).all()
    if not usuarios:
        print("No hay usuarios registrados.")
        return
    print(f"\n{'TELÉFONO':<20} {'TIPO':<15} {'ESTADO BOT'}")
    print("-" * 55)
    for u in usuarios:
        print(f"{u.telefono:<20} {str(u.tipo or 'sin tipo'):<15} {u.estado_bot}")


def reset_usuario(db, telefono: str):
    usuario = db.query(Usuario).filter(Usuario.telefono == telefono).first()

    if not usuario:
        print(f"❌ No se encontró el usuario con teléfono: {telefono}")
        return

    print(f"\nUsuario encontrado:")
    print(f"  Teléfono : {usuario.telefono}")
    print(f"  Tipo     : {usuario.tipo}")
    print(f"  Estado   : {usuario.estado_bot}")

    confirmar = input("\n¿Borrar este usuario? (s/n): ").strip().lower()
    if confirmar != "s":
        print("Operación cancelada.")
        return

    # Borrar viajes asociados primero
    viajes_borrados = db.query(Viaje).filter(Viaje.transportista_id == usuario.id).delete()
    db.delete(usuario)
    db.commit()

    print(f"✅ Usuario eliminado. ({viajes_borrados} viaje(s) también eliminados)")
    print("La próxima vez que escriba al bot, arrancará desde cero.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        if len(sys.argv) < 2:
            listar_usuarios(db)
            print("\nPara resetear: python scripts/reset_usuario.py +5491112345678")
        else:
            telefono = sys.argv[1].strip()
            reset_usuario(db, telefono)
    finally:
        db.close()
