from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base


class EstadoBot(str, enum.Enum):
    NUEVO = "nuevo"
    MENU = "menu"
    VIENDO_CARGAS = "viendo_cargas"
    PUBLICANDO_VIAJE = "publicando_viaje"
    # Sub-estados para publicar viaje
    PV_ORIGEN = "pv_origen"
    PV_DESTINO = "pv_destino"
    PV_TIPO_CAMION = "pv_tipo_camion"
    PV_FECHA_SALIDA = "pv_fecha_salida"
    PV_FECHA_VUELTA = "pv_fecha_vuelta"
    PV_CONFIRMAR = "pv_confirmar"


class TipoUsuario(str, enum.Enum):
    TRANSPORTISTA = "transportista"
    EMPRESA = "empresa"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    telefono = Column(String, unique=True, index=True, nullable=False)
    tipo = Column(Enum(TipoUsuario), nullable=True)
    nombre = Column(String, nullable=True)
    estado_bot = Column(String, default=EstadoBot.NUEVO)

    # Preferencias de búsqueda
    preferencia_origen = Column(String, nullable=True)
    preferencia_destino = Column(String, nullable=True)

    # Datos temporales durante flujo de publicación de viaje
    temp_origen = Column(String, nullable=True)
    temp_destino = Column(String, nullable=True)
    temp_tipo_camion = Column(String, nullable=True)
    temp_fecha_salida = Column(String, nullable=True)
    temp_fecha_vuelta = Column(String, nullable=True)

    creado_en = Column(DateTime, default=datetime.utcnow)
    viajes = relationship("Viaje", back_populates="transportista")


class Carga(Base):
    __tablename__ = "cargas"

    id = Column(Integer, primary_key=True, index=True)
    origen = Column(String, nullable=False)
    destino = Column(String, nullable=False)
    tipo_carga = Column(String, nullable=True)       # general, refrigerada, parcial, etc.
    peso_toneladas = Column(Float, nullable=True)
    fecha_retiro = Column(String, nullable=False)    # formato dd/mm o texto libre
    contacto_nombre = Column(String, nullable=True)
    contacto_telefono = Column(String, nullable=True)
    activa = Column(Boolean, default=True)
    creada_en = Column(DateTime, default=datetime.utcnow)


class Viaje(Base):
    __tablename__ = "viajes"

    id = Column(Integer, primary_key=True, index=True)
    transportista_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    origen = Column(String, nullable=False)
    destino = Column(String, nullable=False)
    tipo_camion = Column(String, nullable=True)
    fecha_salida = Column(String, nullable=False)
    fecha_vuelta = Column(String, nullable=True)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    transportista = relationship("Usuario", back_populates="viajes")
