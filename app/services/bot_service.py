"""
Motor del bot: máquina de estados que procesa cada mensaje entrante
y devuelve la respuesta correspondiente según el estado actual del usuario.

Estados:
  NUEVO            → primer contacto, pedir tipo de usuario
  MENU             → menú principal
  VIENDO_CARGAS    → flujo CU-02
  PV_ORIGEN        → flujo CU-03, paso origen
  PV_DESTINO       → paso destino
  PV_TIPO_CAMION   → paso tipo de camión
  PV_FECHA_SALIDA  → paso fecha salida
  PV_FECHA_VUELTA  → paso fecha vuelta
  PV_CONFIRMAR     → confirmación final
"""

from sqlalchemy.orm import Session
from app.models.models import Usuario, Carga, Viaje, EstadoBot, TipoUsuario
from app.services.matching_service import buscar_cargas_compatibles


# ──────────────────────────────────────────────
# Mensajes reutilizables
# ──────────────────────────────────────────────

MSG_BIENVENIDA = (
    "Hola 👋 Soy RutaHub.\n"
    "Te ayudo a encontrar cargas para tu camión.\n\n"
    "¿Sos transportista o empresa?\n"
    "1️⃣ Transportista\n"
    "2️⃣ Empresa"
)

MSG_EMPRESA = (
    "Gracias por tu interés 🙌\n"
    "Próximamente habilitaremos el acceso para empresas.\n"
    "Te avisamos cuando esté disponible."
)

MSG_MENU = (
    "Estas son las opciones disponibles:\n\n"
    "1️⃣ Ver cargas disponibles\n"
    "2️⃣ Publicar viaje"
)

MSG_OPCION_INVALIDA = "No entendí tu respuesta. Por favor elegí una opción válida."


# ──────────────────────────────────────────────
# Función principal
# ──────────────────────────────────────────────

def procesar_mensaje(telefono: str, texto: str, db: Session) -> str:
    texto = texto.strip()

    # Obtener o crear usuario
    usuario = db.query(Usuario).filter(Usuario.telefono == telefono).first()
    if not usuario:
        usuario = Usuario(telefono=telefono, estado_bot=EstadoBot.NUEVO)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    estado = usuario.estado_bot

    # ── NUEVO: primer contacto ──────────────────
    if estado == EstadoBot.NUEVO:
        return _manejar_nuevo(usuario, texto, db)

    # ── MENÚ PRINCIPAL ─────────────────────────
    if estado == EstadoBot.MENU:
        return _manejar_menu(usuario, texto, db)

    # ── VER CARGAS (CU-02) ─────────────────────
    if estado == EstadoBot.VIENDO_CARGAS:
        return _manejar_ver_cargas(usuario, texto, db)

    # ── PUBLICAR VIAJE (CU-03) ─────────────────
    if estado in (
        EstadoBot.PV_ORIGEN,
        EstadoBot.PV_DESTINO,
        EstadoBot.PV_TIPO_CAMION,
        EstadoBot.PV_FECHA_SALIDA,
        EstadoBot.PV_FECHA_VUELTA,
        EstadoBot.PV_CONFIRMAR,
    ):
        return _manejar_publicar_viaje(usuario, texto, db)

    # Fallback
    _set_estado(usuario, EstadoBot.MENU, db)
    return MSG_MENU


# ──────────────────────────────────────────────
# Handlers por estado
# ──────────────────────────────────────────────

def _manejar_nuevo(usuario: Usuario, texto: str, db: Session) -> str:
    if texto == "1":
        usuario.tipo = TipoUsuario.TRANSPORTISTA
        _set_estado(usuario, EstadoBot.MENU, db)
        return f"Perfecto, registrado como transportista ✅\n\n{MSG_MENU}"
    elif texto == "2":
        return MSG_EMPRESA
    else:
        return MSG_BIENVENIDA


def _manejar_menu(usuario: Usuario, texto: str, db: Session) -> str:
    if texto == "1":
        return _iniciar_ver_cargas(usuario, db)
    elif texto == "2":
        _set_estado(usuario, EstadoBot.PV_ORIGEN, db)
        return "¿De dónde salís? ✍️\nEjemplo: Neuquén, Rosario, Buenos Aires..."
    else:
        return f"{MSG_OPCION_INVALIDA}\n\n{MSG_MENU}"


def _iniciar_ver_cargas(usuario: Usuario, db: Session) -> str:
    # Si no tiene preferencias, las pedimos
    if not usuario.preferencia_origen:
        _set_estado(usuario, EstadoBot.VIENDO_CARGAS, db)
        return "Para mostrarte mejores cargas 🚛\n¿Desde dónde solés trabajar?\nEjemplo: Neuquén"
    # Ya tiene preferencias → mostrar cargas directamente
    return _mostrar_cargas(usuario, db)


def _manejar_ver_cargas(usuario: Usuario, texto: str, db: Session) -> str:
    # Capturar preferencias si faltan
    if not usuario.preferencia_origen:
        usuario.preferencia_origen = texto.title()
        db.commit()
        return "¿Hacia qué zonas te interesa viajar?\nEjemplo: Rosario, Buenos Aires..."

    if not usuario.preferencia_destino:
        usuario.preferencia_destino = texto.title()
        db.commit()
        return _mostrar_cargas(usuario, db)

    # Ya tiene preferencias — navegar listado
    if texto == "0":
        usuario.preferencia_origen = None
        usuario.preferencia_destino = None
        db.commit()
        return "¿Desde dónde solés trabajar?\nEjemplo: Neuquén"

    # Selección de carga por número
    cargas = buscar_cargas_compatibles(usuario.preferencia_origen, usuario.preferencia_destino, db)
    try:
        idx = int(texto) - 1
        if 0 <= idx < len(cargas):
            carga = cargas[idx]
            _set_estado(usuario, EstadoBot.MENU, db)
            return (
                f"📦 *Detalle de carga*\n\n"
                f"Origen: {carga.origen}\n"
                f"Destino: {carga.destino}\n"
                f"Tipo: {carga.tipo_carga or 'No especificado'}\n"
                f"Peso: {carga.peso_toneladas or '?'} tn\n"
                f"Fecha: {carga.fecha_retiro}\n"
                f"📞 Contacto: {carga.contacto_telefono or 'No disponible'}\n\n"
                f"1️⃣ Ver más cargas\n"
                f"2️⃣ Volver al menú"
            )
    except (ValueError, IndexError):
        pass

    return f"{MSG_OPCION_INVALIDA}\n\n{_mostrar_cargas(usuario, db)}"


def _mostrar_cargas(usuario: Usuario, db: Session) -> str:
    cargas = buscar_cargas_compatibles(usuario.preferencia_origen, usuario.preferencia_destino, db)
    _set_estado(usuario, EstadoBot.VIENDO_CARGAS, db)

    if not cargas:
        return (
            "No hay cargas disponibles en este momento 😕\n"
            "Te avisaremos cuando aparezcan en tu zona.\n\n"
            f"{MSG_MENU}"
        )

    lineas = ["🚛 *Cargas disponibles cerca de vos:*\n"]
    for i, c in enumerate(cargas[:5], start=1):
        lineas.append(f"{i}️⃣ {c.origen} → {c.destino}\n{c.tipo_carga or 'Carga general'} | {c.fecha_retiro}")

    lineas.append("\nEscribí el número para ver detalles")
    lineas.append("0️⃣ Cambiar ubicación")
    return "\n".join(lineas)


def _manejar_publicar_viaje(usuario: Usuario, texto: str, db: Session) -> str:
    estado = usuario.estado_bot

    if estado == EstadoBot.PV_ORIGEN:
        usuario.temp_origen = texto.title()
        _set_estado(usuario, EstadoBot.PV_DESTINO, db)
        return "¿Hacia dónde vas? ✍️\nEjemplo: Buenos Aires, Córdoba..."

    if estado == EstadoBot.PV_DESTINO:
        usuario.temp_destino = texto.title()
        _set_estado(usuario, EstadoBot.PV_TIPO_CAMION, db)
        return (
            "¿Qué tipo de camión tenés?\n\n"
            "1️⃣ Semi\n"
            "2️⃣ Chasis\n"
            "3️⃣ Otro"
        )

    if estado == EstadoBot.PV_TIPO_CAMION:
        tipos = {"1": "Semi", "2": "Chasis", "3": "Otro"}
        if texto not in tipos:
            return f"{MSG_OPCION_INVALIDA}\n\n1️⃣ Semi\n2️⃣ Chasis\n3️⃣ Otro"
        usuario.temp_tipo_camion = tipos[texto]
        _set_estado(usuario, EstadoBot.PV_FECHA_SALIDA, db)
        return "¿Cuándo salís? 📅\nEjemplo: mañana, 15/06, hoy"

    if estado == EstadoBot.PV_FECHA_SALIDA:
        usuario.temp_fecha_salida = texto
        _set_estado(usuario, EstadoBot.PV_FECHA_VUELTA, db)
        return "¿Tenés fecha estimada de vuelta? (opcional)\nEscribí la fecha o *no sé*"

    if estado == EstadoBot.PV_FECHA_VUELTA:
        usuario.temp_fecha_vuelta = texto if texto.lower() != "no sé" else None
        db.commit()
        _set_estado(usuario, EstadoBot.PV_CONFIRMAR, db)
        return (
            f"🚛 *Resumen de tu viaje:*\n\n"
            f"{usuario.temp_origen} → {usuario.temp_destino}\n"
            f"Camión: {usuario.temp_tipo_camion}\n"
            f"Fecha de salida: {usuario.temp_fecha_salida}\n"
            f"Fecha de vuelta: {usuario.temp_fecha_vuelta or 'No especificada'}\n\n"
            f"1️⃣ Confirmar\n"
            f"2️⃣ Cancelar"
        )

    if estado == EstadoBot.PV_CONFIRMAR:
        if texto == "1":
            viaje = Viaje(
                transportista_id=usuario.id,
                origen=usuario.temp_origen,
                destino=usuario.temp_destino,
                tipo_camion=usuario.temp_tipo_camion,
                fecha_salida=usuario.temp_fecha_salida,
                fecha_vuelta=usuario.temp_fecha_vuelta,
            )
            db.add(viaje)
            # Limpiar datos temporales
            usuario.temp_origen = None
            usuario.temp_destino = None
            usuario.temp_tipo_camion = None
            usuario.temp_fecha_salida = None
            usuario.temp_fecha_vuelta = None
            _set_estado(usuario, EstadoBot.MENU, db)
            return (
                "✅ Tu viaje fue publicado con éxito\n"
                "Te avisamos cuando aparezcan cargas compatibles 🚛\n\n"
                f"{MSG_MENU}"
            )
        elif texto == "2":
            _set_estado(usuario, EstadoBot.MENU, db)
            return f"Publicación cancelada.\n\n{MSG_MENU}"
        else:
            return f"{MSG_OPCION_INVALIDA}\n\n1️⃣ Confirmar\n2️⃣ Cancelar"

    return MSG_MENU


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _set_estado(usuario: Usuario, estado: str, db: Session):
    usuario.estado_bot = estado
    db.commit()
