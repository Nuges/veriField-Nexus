from typing import Any, Callable, Coroutine, Dict, List

from app.core.events.base import BaseEvent

# Global registry maps event_type to a list of async callbacks
_subscriber_registry: Dict[
    str, List[Callable[[BaseEvent], Coroutine[Any, Any, None]]]
] = {}


def register_subscriber(event_type: str):
    """
    Decorator to register a callback function to handle an event type.

    Usage:
        @register_subscriber("activity.created")
        async def on_activity_created(event: BaseEvent):
            ...
    """

    def decorator(callback: Callable[[BaseEvent], Coroutine[Any, Any, None]]):
        if event_type not in _subscriber_registry:
            _subscriber_registry[event_type] = []
        _subscriber_registry[event_type].append(callback)
        return callback

    return decorator


def get_subscribers(
    event_type: str,
) -> List[Callable[[BaseEvent], Coroutine[Any, Any, None]]]:
    """Retrieve all registered async callbacks for an event type."""
    return _subscriber_registry.get(event_type, [])
