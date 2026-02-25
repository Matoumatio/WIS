from typing import Callable, Dict, List, Any

class EventBus:
    """
    Simple messaging system that allows modules to communicate 
    without knowing about each other (Observer Pattern).
    """
    _subscribers: Dict[str, List[Callable]] = {}

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable):
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)
    
    @classmethod
    def emit(cls, event_type: str, data: Any = None):
        if event_type in cls._subscribers:
            for callback in cls._subscribers[event_type]:
                callback(data)

class AppEvents:
    LOG_EMITTED = "log_emitted"         #{message, level}
    STATS_UPDATED = "stats_updated"     #{sent, failed} 
    MONITORING_STARTED = "started"
    MONITORING_STOPPED = "stopped"