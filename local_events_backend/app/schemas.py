from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class EventListItem(BaseModel):
    id: uuid.UUID = Field(..., description="Event id (UUID).")
    title: str = Field(..., description="Event title.")
    description: Optional[str] = Field(None, description="Optional event description.")
    location_name: Optional[str] = Field(None, description="Optional location name.")
    starts_at: datetime = Field(..., description="Start datetime (ISO-8601).")
    ends_at: Optional[datetime] = Field(None, description="End datetime (ISO-8601).")
    category: Optional[str] = Field(None, description="Optional category string.")
    created_by: Optional[uuid.UUID] = Field(None, description="User id (UUID) that created the event.")

    model_config = {"from_attributes": True}


class EventDetail(EventListItem):
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp (ISO-8601).")


class EventCreateInput(BaseModel):
    title: str = Field(..., min_length=1, description="Event title.")
    description: Optional[str] = Field(None, description="Event description.")
    location_name: Optional[str] = Field(None, description="Location name.")
    starts_at: datetime = Field(..., description="Start datetime (ISO-8601).")
    ends_at: Optional[datetime] = Field(None, description="End datetime (ISO-8601).")
    category: Optional[str] = Field(None, description="Category string.")


class EventUpdateInput(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="Event title.")
    description: Optional[str] = Field(None, description="Event description.")
    location_name: Optional[str] = Field(None, description="Location name.")
    starts_at: Optional[datetime] = Field(None, description="Start datetime (ISO-8601).")
    ends_at: Optional[datetime] = Field(None, description="End datetime (ISO-8601).")
    category: Optional[str] = Field(None, description="Category string.")


class RsvpInput(BaseModel):
    status: Literal["going", "not_going"] = Field(..., description="RSVP status.")


class RsvpResponse(BaseModel):
    ok: bool = Field(..., description="Whether the operation succeeded.")
    status: str = Field(..., description="Stored RSVP status.")


class OkResponse(BaseModel):
    ok: bool = Field(..., description="Whether the operation succeeded.")


class CommentOut(BaseModel):
    id: uuid.UUID = Field(..., description="Comment id (UUID).")
    event_id: uuid.UUID = Field(..., description="Event id (UUID).")
    body: str = Field(..., description="Comment body.")
    created_by: Optional[uuid.UUID] = Field(None, description="User id (UUID) that authored the comment.")
    created_at: datetime = Field(..., description="Comment timestamp (ISO-8601).")

    model_config = {"from_attributes": True}


class CommentCreateInput(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000, description="Comment body text.")
