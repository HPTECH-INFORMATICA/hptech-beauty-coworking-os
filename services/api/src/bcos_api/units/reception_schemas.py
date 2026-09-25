"""Reception-hours administration schemas."""

from datetime import time
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReceptionHour(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    opens_at: time | None = None
    closes_at: time | None = None
    is_closed: bool = False

    @model_validator(mode="after")
    def validate_window(self):
        if self.is_closed:
            if self.opens_at is not None or self.closes_at is not None:
                raise ValueError("Closed day must not define opening hours.")
        elif self.opens_at is None or self.closes_at is None or self.opens_at >= self.closes_at:
            raise ValueError("Open day requires opens_at earlier than closes_at.")
        return self


class ReceptionHoursUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: list[ReceptionHour] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def validate_days(self):
        if {item.day_of_week for item in self.hours} != set(range(7)):
            raise ValueError("Reception hours must contain each day from 0 through 6 exactly once.")
        return self
