from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_user_id
from app.db import session_scope
from app.models import Comment, Event, Rsvp, User
from app.schemas import (
    CommentCreateInput,
    CommentOut,
    EventCreateInput,
    EventDetail,
    EventListItem,
    EventUpdateInput,
    OkResponse,
    RsvpInput,
    RsvpResponse,
)

router = APIRouter(prefix="", tags=["events"])


def _get_db() -> Session:
    with session_scope() as db:
        yield db


def _ensure_user_exists(db: Session, user_id: uuid.UUID) -> None:
    """Ensure the referenced user exists in DB.

    If a user id is used, auto-create a placeholder row if it doesn't exist.
    """
    existing = db.scalar(select(User).where(User.id == user_id))
    if existing is None:
        db.add(User(id=user_id, display_name=f"User {str(user_id)[:8]}"))
        db.flush()


@router.get(
    "/events",
    response_model=list[EventListItem],
    summary="List events",
    description="List events with optional query/category filtering and upcoming-only toggle.",
    operation_id="listEvents",
)
def list_events(
    q: Optional[str] = Query(default=None, description="Search in title/description."),
    category: Optional[str] = Query(default=None, description="Category filter (exact match)."),
    upcoming: Optional[bool] = Query(default=None, description="If true, only events starting from now onward."),
    db: Session = Depends(_get_db),
) -> list[EventListItem]:
    """List events for the feed, optionally filtered."""
    clauses = []
    if q:
        like = f"%{q.strip()}%"
        clauses.append(or_(Event.title.ilike(like), Event.description.ilike(like)))
    if category:
        clauses.append(Event.category == category)
    if upcoming:
        clauses.append(Event.starts_at >= datetime.now(tz=timezone.utc))

    stmt = select(Event).order_by(Event.starts_at.asc())
    if clauses:
        stmt = stmt.where(and_(*clauses))

    events = list(db.scalars(stmt).all())
    return [EventListItem.model_validate(e) for e in events]


@router.get(
    "/events/{event_id}",
    response_model=EventDetail,
    summary="Get event",
    description="Fetch a single event by id.",
    operation_id="getEvent",
)
def get_event(event_id: uuid.UUID, db: Session = Depends(_get_db)) -> EventDetail:
    """Get event details by id."""
    event = db.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return EventDetail.model_validate(event)


@router.post(
    "/events",
    response_model=EventDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create event",
    description="Create a new event. Requires X-User-Id header.",
    operation_id="createEvent",
)
def create_event(
    input_: EventCreateInput,
    user_id: uuid.UUID = Depends(require_user_id),
    db: Session = Depends(_get_db),
) -> EventDetail:
    """Create an event owned by the calling user."""
    _ensure_user_exists(db, user_id)

    event = Event(
        title=input_.title,
        description=input_.description,
        location_name=input_.location_name,
        starts_at=input_.starts_at,
        ends_at=input_.ends_at,
        category=input_.category,
        created_by=user_id,
    )
    db.add(event)
    db.flush()
    db.refresh(event)
    return EventDetail.model_validate(event)


@router.patch(
    "/events/{event_id}",
    response_model=EventDetail,
    summary="Update event",
    description="Patch update an existing event. Only the creator may update. Requires X-User-Id.",
    operation_id="updateEvent",
)
def update_event(
    event_id: uuid.UUID,
    input_: EventUpdateInput,
    user_id: uuid.UUID = Depends(require_user_id),
    db: Session = Depends(_get_db),
) -> EventDetail:
    """Update an event (owner-only)."""
    event = db.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event.created_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the event creator may edit this event")

    patch = input_.model_dump(exclude_unset=True)
    if not patch:
        return EventDetail.model_validate(event)

    patch["updated_at"] = func.now()

    db.execute(update(Event).where(Event.id == event_id).values(**patch))
    db.flush()

    event = db.scalar(select(Event).where(Event.id == event_id))
    assert event is not None
    return EventDetail.model_validate(event)


@router.delete(
    "/events/{event_id}",
    response_model=OkResponse,
    summary="Delete event",
    description="Delete an event. Only the creator may delete. Requires X-User-Id.",
    operation_id="deleteEvent",
)
def delete_event(
    event_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    db: Session = Depends(_get_db),
) -> OkResponse:
    """Delete an event (owner-only)."""
    event = db.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event.created_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the event creator may delete this event")

    db.execute(delete(Event).where(Event.id == event_id))
    return OkResponse(ok=True)


@router.post(
    "/events/{event_id}/rsvp",
    response_model=RsvpResponse,
    summary="RSVP to event",
    description="Set RSVP status for the current user on an event. Requires X-User-Id.",
    operation_id="rsvpEvent",
)
def rsvp_event(
    event_id: uuid.UUID,
    input_: RsvpInput,
    user_id: uuid.UUID = Depends(require_user_id),
    db: Session = Depends(_get_db),
) -> RsvpResponse:
    """Create or update RSVP status for the current user."""
    event = db.scalar(select(Event).where(Event.id == event_id))
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    _ensure_user_exists(db, user_id)

    existing = db.scalar(select(Rsvp).where(and_(Rsvp.event_id == event_id, Rsvp.user_id == user_id)))
    if existing is None:
        db.add(Rsvp(event_id=event_id, user_id=user_id, status=input_.status))
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            existing = db.scalar(select(Rsvp).where(and_(Rsvp.event_id == event_id, Rsvp.user_id == user_id)))

    db.execute(
        update(Rsvp)
        .where(and_(Rsvp.event_id == event_id, Rsvp.user_id == user_id))
        .values(status=input_.status, updated_at=func.now())
    )
    db.flush()

    return RsvpResponse(ok=True, status=input_.status)


@router.get(
    "/events/{event_id}/comments",
    response_model=list[CommentOut],
    summary="List comments",
    description="List comments for an event (oldest first).",
    operation_id="listComments",
)
def list_comments(event_id: uuid.UUID, db: Session = Depends(_get_db)) -> list[CommentOut]:
    """List comments for an event."""
    exists = db.scalar(select(Event.id).where(Event.id == event_id))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    comments = list(
        db.scalars(select(Comment).where(Comment.event_id == event_id).order_by(Comment.created_at.asc())).all()
    )
    return [CommentOut.model_validate(c) for c in comments]


@router.post(
    "/events/{event_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment",
    description="Add a comment to an event. Requires X-User-Id.",
    operation_id="addComment",
)
def add_comment(
    event_id: uuid.UUID,
    input_: CommentCreateInput,
    user_id: uuid.UUID = Depends(require_user_id),
    db: Session = Depends(_get_db),
) -> CommentOut:
    """Create a comment on an event by the calling user."""
    exists = db.scalar(select(Event.id).where(Event.id == event_id))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    _ensure_user_exists(db, user_id)

    comment = Comment(event_id=event_id, created_by=user_id, body=input_.body)
    db.add(comment)
    db.flush()
    db.refresh(comment)
    return CommentOut.model_validate(comment)
