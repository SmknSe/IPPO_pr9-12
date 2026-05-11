from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    capacity: int


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    capacity: int = Field(gt=0)


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    capacity: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "RoomUpdate":
        if self.name is None and self.capacity is None:
            raise ValueError("at least one of name, capacity is required")
        return self


class BookingCreate(BaseModel):
    room_id: int = Field(gt=0)
    user_email: str
    start_time: datetime
    end_time: datetime


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    user_email: str
    start_time: datetime
    end_time: datetime
