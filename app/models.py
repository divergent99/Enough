from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Moment = Literal["panic", "overthinking", "grief", "stuck", "checkin"]

class ReflectionRequest(BaseModel):
    moment: Moment
    text: str = Field(min_length=1, max_length=5000)
    energy: int = Field(default=2, ge=1, le=5)
    preference: Literal["listen", "untangle", "next_step"] = "untangle"
    agent: Literal["sentinel", "duelist", "strategist", "healer", "wanderer"] | None = None

class ReflectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acknowledgement: str
    feeling: str
    controllable: list[str]
    can_wait: list[str]
    next_step: str
    mode: str
    safety: Literal["support", "urgent"]

class CheckIn(BaseModel):
    mood: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    note: str = Field(default="", max_length=1000)

class AccountCreate(BaseModel):
    email: str = Field(min_length=5,max_length=254,pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    name: str = Field(min_length=1,max_length=60)
    password: str = Field(min_length=10,max_length=128)

class AccountLogin(BaseModel):
    email: str = Field(min_length=5,max_length=254)
    password: str = Field(min_length=1,max_length=128)

class PushSubscription(BaseModel):
    endpoint: str = Field(min_length=10,max_length=2048)
    expirationTime: int | None = None
    keys: dict[str,str]

class NotificationPreferences(BaseModel):
    enabled: bool = False
    theme: Literal["gentle","philosophy","grief","poetry"] = "gentle"
    frequency: Literal["daily","weekly","request"] = "daily"
    time_local: str = Field(default="09:00",pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(default="UTC",min_length=1,max_length=80)
    delivery: Literal["in-app","push","email","both"] = "in-app"
