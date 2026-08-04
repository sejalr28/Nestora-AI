from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

from app.core.phone import normalize_phone
from app.database import get_db
from app.models.resident import Resident
from app.services.agent.agent import SocietyAgent
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMProvider
from app.services.whatsapp.onboarding import ONBOARDING_PROMPT, onboard_resident, parse_onboarding_message

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
):
    """
    Twilio POSTs form-encoded data here (From, Body, ...) on every incoming
    WhatsApp message. We reply synchronously with TwiML -- whatever text we
    put in the <Message> is what Twilio delivers back as the WhatsApp reply.
    No outbound REST call needed for this reply-to-inbound flow.

    Routing: unknown phone number -> onboarding; known resident -> agent.
    """
    form = await request.form()
    from_number = normalize_phone(str(form.get("From", "")))
    body = str(form.get("Body", "")).strip()

    resident = db.query(Resident).filter(Resident.phone_number == from_number).first()

    if resident is None:
        parsed = parse_onboarding_message(body)
        if parsed is None:
            reply_text = ONBOARDING_PROMPT
        else:
            _, reply_text = onboard_resident(db, from_number, parsed)
    else:
        agent = SocietyAgent(provider)
        reply_text = agent.run(db, resident, body)

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="application/xml")