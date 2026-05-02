from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.bot_service import procesar_mensaje

router = APIRouter()


@router.post("/webhook/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Twilio envía un POST con Form data cuando llega un mensaje de WhatsApp.
    'From' es el número del usuario en formato whatsapp:+549XXXXXXXXXX
    'Body' es el texto del mensaje.
    """
    # Normalizar número: sacar prefijo "whatsapp:"
    telefono = From.replace("whatsapp:", "").strip()
    texto = Body.strip()

    respuesta = procesar_mensaje(telefono=telefono, texto=texto, db=db)

    # Twilio acepta TwiML o texto plano — usamos texto plano por simplicidad
    # Para respuesta TwiML descomentar el bloque de abajo
    # twiml = f"<?xml version='1.0' encoding='UTF-8'?><Response><Message>{respuesta}</Message></Response>"
    # return Response(content=twiml, media_type="application/xml")

    return respuesta


@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify():
    """
    Endpoint de verificación (algunos providers lo usan).
    """
    return {"status": "RutaHub webhook activo"}
