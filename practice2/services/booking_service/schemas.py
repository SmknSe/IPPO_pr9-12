from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_admin: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class BookingCreate(BaseModel):
    room_id: int = Field(gt=0)
    start_time: datetime
    end_time: datetime


class BookingParticipantOut(BaseModel):
    user_id: int
    email: str


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    user_id: int
    user_email: str
    start_time: datetime
    end_time: datetime
    participant_emails: list[str] = []
    participants: list[BookingParticipantOut] = []


class UserSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class ParticipantAdd(BaseModel):
    user_id: int = Field(gt=0)
