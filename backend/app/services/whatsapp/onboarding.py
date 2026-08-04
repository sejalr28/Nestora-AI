"""
Onboarding flow for a new WhatsApp number.

Design choice: this is stateless -- no "onboarding in progress" session
table. Instead, a single required message format ("Name, Building N, Flat")
does the whole job in one round trip. That avoids needing to persist
conversation state between messages just to remember "we already asked
this number for their building" (which would need Redis or a DB table for
what's otherwise a one-shot exchange). The tradeoff is a stricter required
format -- a natural follow-up improvement once the agent is solid would be
letting the LLM itself parse free-form onboarding replies instead of this
regex, but a deterministic regex is easier to test and reason about for V1.
"""

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.flat import Flat, FlatStatus
from app.models.resident import Resident

ONBOARDING_PROMPT = (
    "Welcome to SocietyBoard! I don't have your flat on file yet.\n"
    "Reply with your name, building number, and flat number, like this:\n"
    "Sejal, Building 7, 302"
)

_ONBOARDING_PATTERN = re.compile(
    r"^\s*(?P<name>[^,]+),\s*building\s*(?P<building_number>\d+)\s*,\s*(?P<flat_number>\d+)\s*$",
    re.IGNORECASE,
)


@dataclass
class OnboardingInfo:
    name: str
    building_number: str
    flat_number: int


def parse_onboarding_message(text: str) -> OnboardingInfo | None:
    match = _ONBOARDING_PATTERN.match(text)
    if not match:
        return None
    return OnboardingInfo(
        name=match.group("name").strip(),
        building_number=match.group("building_number"),
        flat_number=int(match.group("flat_number")),
    )


def onboard_resident(db: Session, phone_number: str, info: OnboardingInfo) -> tuple[Resident | None, str]:
    """Creates the Resident (and the Flat, if it doesn't exist yet) and
    returns (resident_or_None, reply_text). Returns (None, ...) if the
    building doesn't exist -- buildings are fixed seed data, so an unknown
    building number means a typo, not something to auto-create."""
    building_name = f"Building {info.building_number}"
    building = db.query(Building).filter(Building.name.ilike(building_name)).first()
    if not building:
        return None, f"I couldn't find {building_name}. Please check the number and try again."

    flat = (
        db.query(Flat)
        .filter(Flat.building_id == building.id, Flat.flat_number == info.flat_number)
        .first()
    )
    if not flat:
        # Self-service: create the flat if the committee hasn't pre-seeded it,
        # with unknown status until someone sets it via the dashboard.
        flat = Flat(building_id=building.id, flat_number=info.flat_number, status=FlatStatus.unknown)
        db.add(flat)
        db.flush()

    resident = Resident(flat_id=flat.id, phone_number=phone_number, name=info.name)
    db.add(resident)
    db.commit()
    db.refresh(resident)

    reply = (
        f"Welcome {info.name}! You're linked to {building.name}, Flat {flat.flat_number}.\n"
        "Ask me about water timing, flat status, or just tell me if something needs fixing."
    )
    return resident, reply