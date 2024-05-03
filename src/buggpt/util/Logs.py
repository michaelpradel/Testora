import json
from datetime import datetime, timedelta
import atexit
from pydantic import BaseModel


class Event(BaseModel):
    timestamp: str = datetime.now().isoformat()
    pr_nb: int
    message: str


class PREvent(Event):
    title: str
    url: str


class TestExecutionEvent(Event):
    code: str
    output: str


class ComparisonEvent(Event):
    old_function_code: str
    old_output: str
    new_function_code: str
    new_output: str


class LLMEvent(Event):
    content: str


events = []
last_time_stored = datetime.now()


def append_event(evt):
    global last_time_stored

    events.append(evt)
    print(json.dumps(evt.dict(), indent=2))

    if datetime.now() - last_time_stored > timedelta(minutes=5):
        store_logs()
        last_time_stored = datetime.now()


def store_logs():
    timestamp = datetime.now().isoformat()
    event_dicts = [evt.dict() for evt in events]
    json.dump(event_dicts, open(f"logs_{timestamp}.json", "w"), indent=2)


atexit.register(store_logs)
