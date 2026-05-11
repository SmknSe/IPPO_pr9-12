from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    capacity: int


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
