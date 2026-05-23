"""
Manage asyncio.Event cancellation flags per session.
"""

import asyncio

_cancel_events: dict[str, asyncio.Event] = {}


def create_cancel_event(session_id: str) -> asyncio.Event:
    event = asyncio.Event()
    _cancel_events[session_id] = event
    return event


def get_cancel_event(session_id: str) -> asyncio.Event | None:
    return _cancel_events.get(session_id)


def set_cancel_event(session_id: str):
    event = _cancel_events.get(session_id)
    if event:
        event.set()


def clear_cancel_event(session_id: str):
    """Reset the cancel flag so subsequent turns can proceed."""
    event = _cancel_events.get(session_id)
    if event:
        event.clear()


def remove_cancel_event(session_id: str):
    _cancel_events.pop(session_id, None)
