from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Envelope(BaseModel, Generic[T]):
    data: T
    updated_at: datetime | None = None
    source: str | None = None
