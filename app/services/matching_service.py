"""
Servicio de matching: busca cargas compatibles con el origen/destino del transportista.
Por ahora usa búsqueda por texto (ILIKE). En fases futuras se puede mejorar con
geocodificación y radio de distancia.
"""

from sqlalchemy.orm import Session
from app.models.models import Carga


def buscar_cargas_compatibles(origen: str, destino: str, db: Session) -> list[Carga]:
    """
    Busca cargas activas que coincidan aproximadamente con origen y destino.
    La búsqueda es case-insensitive y por substring.
    """
    query = db.query(Carga).filter(Carga.activa == True)

    if origen:
        query = query.filter(Carga.origen.ilike(f"%{origen}%"))
    if destino:
        query = query.filter(Carga.destino.ilike(f"%{destino}%"))

    return query.order_by(Carga.creada_en.desc()).limit(10).all()


def notificar_transportistas_por_carga(carga: Carga, db: Session) -> list[str]:
    """
    CU-04: dado una carga nueva, encuentra transportistas con viajes compatibles.
    Devuelve lista de teléfonos a notificar.
    """
    from app.models.models import Viaje, Usuario

    viajes_compatibles = (
        db.query(Viaje)
        .filter(
            Viaje.activo == True,
            Viaje.origen.ilike(f"%{carga.origen}%"),
            Viaje.destino.ilike(f"%{carga.destino}%"),
        )
        .all()
    )

    telefonos = []
    for viaje in viajes_compatibles:
        usuario = db.query(Usuario).filter(Usuario.id == viaje.transportista_id).first()
        if usuario:
            telefonos.append(usuario.telefono)

    return telefonos
