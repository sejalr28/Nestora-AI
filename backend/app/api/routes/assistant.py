from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.agent.factory import RESIDENT_ROLE, get_agent
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMMessage, LLMProvider

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    # "role" is the current field name. "agent_role" is kept as an accepted
    # alias so the dashboard's existing AIAssistantPage (built before this
    # field was renamed) keeps working unchanged -- if both are omitted,
    # the default is "resident", so a bare {"message": "..."} request from
    # any older client also continues to work exactly as before.
    role: str | None = None
    agent_role: str | None = None

    @property
    def effective_role(self) -> str:
        return self.role or self.agent_role or RESIDENT_ROLE


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
):
    """
    JSON chat endpoint for the admin dashboard's AI Assistant page. Routes
    to the correct role-scoped agent via the agent factory (Phase 11) --
    "resident" (default, same tools/prompt WhatsApp always has) or
    "committee" (broader, society-wide read/aggregate tools). Only the
    transport differs from WhatsApp (JSON in/out here vs. Twilio
    form/TwiML there). No resident context is attached (this is an admin,
    not a specific flat), so ResidentAgent tools that require an
    identified resident (e.g. logging a complaint) will report that
    limitation rather than act on someone's behalf.
    """
    agent = get_agent(payload.effective_role, provider)
    history = [LLMMessage(role=m.role, content=m.content) for m in payload.history]
    reply = agent.run(db, resident=None, user_message=payload.message, history=history)
    return ChatResponse(reply=reply)