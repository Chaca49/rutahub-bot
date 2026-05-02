"""
Motor del bot: máquina de estados que procesa cada mensaje entrante
y devuelve la respuesta correspondiente según el estado actual del usuario.

Estados:
  NUEVO                → primer contacto, pedir tipo de usuario
  MENU                 → menú principal
  vc_listado           → viendo listado de cargas (todas)
  vc_filtro_origen     → el usuario eligió filtrar por su ubicación
  PV_ORIGEN            → flujo CU-03, paso origen
  PV_DESTINO           → paso destino
  PV_TIPO_CAMION       → paso tipo de camión (1/2/3)
  pv_tipo_camion_manual→ el usuario eligió "Otro", escribe libremente
  PV_FECHA_SALIDA      → paso fecha salida (formato dd/mm)
  PV_FECHA_VUELTA      → paso fecha vuelta (formato dd/mm o "-")
  PV_CONFIRMAR         → confirmación final
"""

import re
from sqlalchemy.orm import Session
from app.models.models import Usuario, Carga, Viaje, EstadoBot, TipoUsuario
from app.services.matching_service import buscar_cargas_compatibles, buscar_todas_las_cargas


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
    "¿Qué querés hacer?\n\n"
    "1️⃣ Ver cargas disponibles\n"
    "2️⃣ Publicar viaje"
)

MSG_OPCION_INVALIDA = "No entendí tu respuesta. Por favor elegí una opción válida."

MSG_FORMATO_FECHA = (
    "⚠️ Formato de fecha inválido.\n"
    "Usá el formato *dd/mm*, por ejemplo: *15/06*"
)


# ──────────────────────────────────────────────
# Validación de fechas
# ──────────────────────────────────────────────

def _es_fecha_valida(texto: str) -> bool:
    """Valida que el texto sea dd/mm con valores razonables."""
    patron = r"^\d{2}/\d{2}$"
    if not re.match(patron, texto.strip()):
        return False
    dia, mes = texto.strip().split("/")
    return 1 <= int(dia) <= 31 and 1 <= int(mes) <= 12


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

    if estado == EstadoBot.NUEVO:
        return _manejar_nuevo(usuario, texto, db)

    if estado == EstadoBot.MENU:
        return _manejar_menu(usuario, texto, db)

    if estado in (EstadoBot.VIENDO_CARGAS, "vc_listado", "vc_filtro_origen"):
        return _manejar_ver_cargas(usuario, texto, db)

    if estado in (
        EstadoBot.PV_ORIGEN,
        EstadoBot.PV_DESTINO,
        EstadoBot.PV_TIPO_CAMION,
        "pv_tipo_camion_manual",
        EstadoBot.PV_FECHA_SALIDA,
        EstadoBot.PV_FECHA_VUELTA,
        EstadoBot.PV_CONFIRMAR,
    ):
        return _manejar_publicar_viaje(usuario, texto, db)

    # Fallback: resetear al menú
    _set_estado(usuario, EstadoBot.MENU, db)
    return f"Volvemos al inicio 🔄\n\n{MSG_MENU}"


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
        # MEJORA 1: mostrar TODAS las cargas primero, sin filtros
        return _mostrar_todas_las_cargas(usuario, db)
    elif texto == "2":
        _set_estado(usuario, EstadoBot.PV_ORIGEN, db)
        return "¿De dónde salís? ✍️\nEjemplo: Neuquén, Rosario, Buenos Aires..."
    else:
        return f"{MSG_OPCION_INVALIDA}\n\n{MSG_MENU}"


def _mostrar_todas_las_cargas(usuario: Usuario, db: Session) -> str:
    """Muestra todas las cargas activas sin filtro de ubicación."""
    cargas = buscar_todas_las_cargas(db)
    _set_estado(usuario, "vc_listado", db)

    if not cargas:
        _set_estado(usuario, EstadoBot.MENU, db)
        return (
            "No hay cargas disponibles en este momento 😕\n"
            "Volvé a intentar más tarde.\n\n"
            f"{MSG_MENU}"
        )

    lineas = ["🚛 *Cargas disponibles:*\n"]
    for i, c in enumerate(cargas[:5], start=1):
        lineas.append(f"{i}️⃣ {c.origen} → {c.destino}\n   {c.tipo_carga or 'Carga general'} | 📅 {c.fecha_retiro}")

    lineas.append("\nEscribí el número para ver el detalle")
    lineas.append("F - Filtrar por mi ubicación")
    lineas.append("0 - Volver al menú")
    return "\n".join(lineas)


def _manejar_ver_cargas(usuario: Usuario, texto: str, db: Session) -> str:
    estado = usuario.estado_bot
    texto_lower = texto.lower().strip()

    # ── Esperando origen para filtrar ──
    if estado == "vc_filtro_origen":
        usuario.preferencia_origen = texto.title()
        db.commit()
        return _mostrar_cargas_filtradas(usuario, db)

    # ── Listado visible: procesar navegación ──
    if texto_lower in ("0", "menu", "menú"):
        _set_estado(usuario, EstadoBot.MENU, db)
        return MSG_MENU

    if texto_lower == "f":
        _set_estado(usuario, "vc_filtro_origen", db)
        return "📍 ¿Desde qué ciudad querés filtrar?\nEjemplo: Neuquén, Córdoba..."

    # Selección de carga por número
    if usuario.preferencia_origen:
        cargas = buscar_cargas_compatibles(usuario.preferencia_origen, None, db)
    else:
        cargas = buscar_todas_las_cargas(db)

    try:
        idx = int(texto) - 1
        if 0 <= idx < len(cargas):
            carga = cargas[idx]
            _set_estado(usuario, EstadoBot.MENU, db)
            return (
                f"📦 *Detalle de carga*\n\n"
                f"🔹 Origen: {carga.origen}\n"
                f"🔹 Destino: {carga.destino}\n"
                f"🔹 Tipo: {carga.tipo_carga or 'No especificado'}\n"
                f"🔹 Peso: {carga.peso_toneladas or '?'} tn\n"
                f"🔹 Fecha: {carga.fecha_retiro}\n"
                f"📞 Contacto: {carga.contacto_telefono or 'No disponible'}\n\n"
                f"1️⃣ Ver más cargas\n"
                f"2️⃣ Volver al menú"
            )
        else:
            raise ValueError
    except (ValueError, TypeError):
        pass

    # MEJORA 2: si no entiende, volver a mostrar el listado limpio (no bucle)
    return _mostrar_todas_las_cargas(usuario, db)


def _mostrar_cargas_filtradas(usuario: Usuario, db: Session) -> str:
    """Muestra cargas filtradas por origen del usuario."""
    cargas = buscar_cargas_compatibles(usuario.preferencia_origen, None, db)
    _set_estado(usuario, "vc_listado", db)

    if not cargas:
        nombre_origen = usuario.preferencia_origen
        usuario.preferencia_origen = None
        db.commit()
        _set_estado(usuario, EstadoBot.MENU, db)
        return (
            f"No encontré cargas desde *{nombre_origen}* 😕\n"
            "Podés ver todas las cargas disponibles desde el menú.\n\n"
            f"{MSG_MENU}"
        )

    lineas = [f"🚛 *Cargas desde {usuario.preferencia_origen}:*\n"]
    for i, c in enumerate(cargas[:5], start=1):
        lineas.append(f"{i}️⃣ {c.origen} → {c.destino}\n   {c.tipo_carga or 'Carga general'} | 📅 {c.fecha_retiro}")

    lineas.append("\nEscribí el número para ver el detalle")
    lineas.append("0 - Volver al menú")
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
            "3️⃣ Otro (escribir manualmente)"
        )

    if estado == EstadoBot.PV_TIPO_CAMION:
        if texto == "1":
            usuario.temp_tipo_camion = "Semi"
            _set_estado(usuario, EstadoBot.PV_FECHA_SALIDA, db)
            return _msg_pedir_fecha_salida()
        elif texto == "2":
            usuario.temp_tipo_camion = "Chasis"
            _set_estado(usuario, EstadoBot.PV_FECHA_SALIDA, db)
            return _msg_pedir_fecha_salida()
        elif texto == "3":
            # MEJORA 3: pedir que escriba manualmente el tipo
            _set_estado(usuario, "pv_tipo_camion_manual", db)
            return "✍️ Escribí el tipo de camión que tenés:\nEjemplo: Batea, Volcador, Furgón, Cisterna..."
        else:
            return (
                f"{MSG_OPCION_INVALIDA}\n\n"
                "¿Qué tipo de camión tenés?\n\n"
                "1️⃣ Semi\n"
                "2️⃣ Chasis\n"
                "3️⃣ Otro (escribir manualmente)"
            )

    # MEJORA 3: capturar tipo manual
    if estado == "pv_tipo_camion_manual":
        if len(texto.strip()) < 2:
            return "Por favor describí el tipo de camión (mínimo 2 caracteres)."
        usuario.temp_tipo_camion = texto.strip().title()
        _set_estado(usuario, EstadoBot.PV_FECHA_SALIDA, db)
        return _msg_pedir_fecha_salida()

    # MEJORA 4: validar formato de fecha de salida
    if estado == EstadoBot.PV_FECHA_SALIDA:
        if not _es_fecha_valida(texto):
            return MSG_FORMATO_FECHA + "\n\n" + _msg_pedir_fecha_salida()
        usuario.temp_fecha_salida = texto.strip()
        _set_estado(usuario, EstadoBot.PV_FECHA_VUELTA, db)
        return (
            "¿Tenés fecha estimada de vuelta? 📅\n"
            "Formato: *dd/mm* — Ejemplo: *20/06*\n"
            "Si no sabés, escribí *-*"
        )

    # MEJORA 4: validar formato de fecha de vuelta
    if estado == EstadoBot.PV_FECHA_VUELTA:
        if texto.strip() == "-":
            usuario.temp_fecha_vuelta = None
        elif _es_fecha_valida(texto):
            usuario.temp_fecha_vuelta = texto.strip()
        else:
            return (
                MSG_FORMATO_FECHA + "\n"
                "O escribí *-* si no sabés la fecha de vuelta."
            )
        db.commit()
        _set_estado(usuario, EstadoBot.PV_CONFIRMAR, db)
        return (
            f"🚛 *Resumen de tu viaje:*\n\n"
            f"📍 {usuario.temp_origen} → {usuario.temp_destino}\n"
            f"🚚 Camión: {usuario.temp_tipo_camion}\n"
            f"📅 Salida: {usuario.temp_fecha_salida}\n"
            f"📅 Vuelta: {usuario.temp_fecha_vuelta or 'No especificada'}\n\n"
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
            _limpiar_temp(usuario, db)
            _set_estado(usuario, EstadoBot.MENU, db)
            return (
                "✅ Tu viaje fue publicado con éxito\n"
                "Te avisamos cuando aparezcan cargas compatibles 🚛\n\n"
                f"{MSG_MENU}"
            )
        elif texto == "2":
            _limpiar_temp(usuario, db)
            _set_estado(usuario, EstadoBot.MENU, db)
            return f"Publicación cancelada.\n\n{MSG_MENU}"
        else:
            return f"{MSG_OPCION_INVALIDA}\n\n1️⃣ Confirmar\n2️⃣ Cancelar"

    return MSG_MENU


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _msg_pedir_fecha_salida() -> str:
    return (
        "¿Cuándo salís? 📅\n"
        "Formato: *dd/mm* — Ejemplo: *15/06*"
    )


def _limpiar_temp(usuario: Usuario, db: Session):
    usuario.temp_origen = None
    usuario.temp_destino = None
    usuario.temp_tipo_camion = None
    usuario.temp_fecha_salida = None
    usuario.temp_fecha_vuelta = None
    db.commit()


def _set_estado(usuario: Usuario, estado: str, db: Session):
    usuario.estado_bot = estado
    db.commit()
