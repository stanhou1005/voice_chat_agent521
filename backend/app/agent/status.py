"""Thread-safe status callback registry for agent nodes."""

from typing import Callable, Awaitable

_callbacks: dict[str, Callable[[str, str], Awaitable[None]]] = {}


def set_callback(thread_id: str, cb: Callable[[str, str], Awaitable[None]]):
    _callbacks[thread_id] = cb


def clear_callback(thread_id: str):
    _callbacks.pop(thread_id, None)


async def emit(thread_id: str, phase: str, text: str):
    cb = _callbacks.get(thread_id)
    if cb:
        await cb(phase, text)
