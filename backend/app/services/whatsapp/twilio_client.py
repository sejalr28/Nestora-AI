"""
Outbound WhatsApp sending via Twilio's REST API.

Not used by the inbound webhook -- that replies synchronously via TwiML,
which doesn't need this. This exists for proactive sends, e.g. a future
admin-dashboard feature: "broadcast the new water timing to all residents."
"""

from twilio.rest import Client

from app.config import settings


def send_whatsapp_message(to_phone_number: str, body: str) -> str:
    """to_phone_number: plain number, e.g. '+919876543210' -- the 'whatsapp:'
    prefix is added here, not by the caller. Returns the Twilio message SID."""
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not configured in .env")

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    message = client.messages.create(
        from_=settings.twilio_whatsapp_number,
        to=f"whatsapp:{to_phone_number}",
        body=body,
    )
    return message.sid