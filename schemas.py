from pydantic import BaseModel, Field
from typing import List


class MeasurementCreate(BaseModel):
    load_id: int = Field(..., ge=1, le=3)

    voltage_v: float = Field(..., ge=0)

    current_a: float = Field(..., ge=0)

    power_w: float = Field(..., ge=0)

    power_factor: float | None = Field(
        default=None,
        ge=0,
        le=1.2
    )

    relay_state: bool


class BatchMeasurementCreate(BaseModel):
    timestamp: str

    measurements: List[MeasurementCreate]


class RelayControlCreate(BaseModel):
    state: bool