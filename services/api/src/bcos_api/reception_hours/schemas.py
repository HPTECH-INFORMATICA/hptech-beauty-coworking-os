"""HTTP schemas for BCOS reception hours."""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import JsonDict


class ReceptionHours(BaseModel):
    """Public representation of one reception-hours day."""

    day_of_week: int = Field(ge=0, le=6)
    opens_at: time | None = None
    closes_at: time | None = None
    is_closed: bool


def _reception_hours_input_schema(
    schema: JsonDict,
) -> None:
    """Publish the frozen ReceptionHoursInput component shape."""

    schema.clear()
    schema["allOf"] = [
        {"$ref": "#/components/schemas/ReceptionHours"},
    ]


class ReceptionHoursInput(ReceptionHours):
    """Payload item for replacing reception hours."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra=_reception_hours_input_schema,
    )
