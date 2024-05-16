import json
from datetime import datetime, timedelta
import atexit
from typing import List, Optional
from pydantic import BaseModel


class Event(BaseModel):
    timestamp: str = ""
    pr_nb: int
    message: str


class PREvent(Event):
    title: str
    url: str


class TestExecutionEvent(Event):
    code: str
    output: str


class ComparisonEvent(Event):
    test_code: str
    old_output: str
    new_output: str


class ClassificationEvent(Event):
    is_relevant_change: Optional[bool]
    is_deterministic: Optional[bool]
    is_regression_bug: Optional[bool]
    old_is_crash: bool
    new_is_crash: bool


class SelectBehaviorEvent(Event):
    expected_output: int


class LLMEvent(Event):
    content: str


class ErrorEvent(Event):
    details: str


events: List = []
last_time_stored = datetime.now()


def append_event(evt):
    global last_time_stored

    evt.timestamp = datetime.now().isoformat()
    events.append(evt)
    print(json.dumps(evt.dict(), indent=2))

    if datetime.now() - last_time_stored > timedelta(minutes=5):
        store_logs()
        last_time_stored = datetime.now()

def events_as_json():
    return json.dumps([evt.dict() for evt in events], indent=2)


def store_logs():
    timestamp = datetime.now().isoformat()
    event_dicts = [evt.dict() for evt in events]
    json.dump(event_dicts, open(f"logs_{timestamp}.json", "w"), indent=2)


atexit.register(store_logs)
