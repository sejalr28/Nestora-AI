"""
Import every model here. Alembic's autogenerate compares Base.metadata
against the live DB -- if a model isn't imported somewhere before that
comparison runs, it's invisible to Alembic and migrations silently miss it.
This file is that single required import point.
"""

from app.models.building import Building  # noqa: F401
from app.models.flat import Flat, FlatStatus  # noqa: F401
from app.models.resident import Resident, ResidentRole  # noqa: F401
from app.models.water_schedule import WaterSchedule, WaterSource  # noqa: F401
from app.models.vendor import Vendor  # noqa: F401
from app.models.service_request import ServiceRequest, RequestStatus  # noqa: F401
