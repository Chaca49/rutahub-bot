from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def enviar_mensaje(to: str, body: str):
    """
    Envía un mensaje de WhatsApp al número indicado.
    'to' debe estar en formato E.164: +5491112345678
    """
    to_whatsapp = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
    message = client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        body=body,
        to=to_whatsapp,
    )
    return message.sid
