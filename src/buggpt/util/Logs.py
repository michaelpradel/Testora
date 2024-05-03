import json
from datetime import datetime
import atexit
from pydantic import BaseModel


class Event(BaseModel):
    timestamp: str = datetime.now().isoformat()
    pr_nb: int
    message: str


class ComparisonEvent(Event):
    old_function_code: str
    old_output: str
    new_function_code: str
    new_output: str


class LLMEvent(Event):
    content: str


events = []


def append_event(evt):
    events.append(evt)
    print(json.dumps(evt.dict(), indent=2))


def store_logs():
    timestamp = datetime.now().isoformat()
    event_dicts = [evt.dict() for evt in events]
    json.dump(event_dicts, open(f"logs_{timestamp}.json", "w"), indent=2)


atexit.register(store_logs)
