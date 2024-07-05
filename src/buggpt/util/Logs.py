import json
import os
import fnmatch
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
    is_public: Optional[bool]
    is_legal: Optional[bool]
    is_surprising: Optional[bool]
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
last_file_stored_to: Optional[str] = None


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
    global last_file_stored_to
    timestamp = datetime.now().isoformat()
    event_dicts = [evt.dict() for evt in events]
    out_file = f"logs_{timestamp}.json"
    json.dump(event_dicts, open(out_file, "w"), indent=2)

    # remove previous log from this run
    if last_file_stored_to is not None:
        os.remove(last_file_stored_to)
    last_file_stored_to = out_file


def read_old_logs():
    events = []

    # find all logs*.json files in current directory
    current_dir = os.getcwd()
    all_files = os.listdir(current_dir)
    log_files = [f for f in all_files if fnmatch.fnmatch(f, "logs*.json")]

    # read them and append to events
    for log_file in log_files:
        with open(log_file) as f:
            events += json.load(f)

    return events


def keep_newest_logs_for_pr_numbers(events, pr_numbers):
    # gather completed runs for each PR
    pr_to_logs = {}
    current_pr = None
    current_pr_events = None
    for event in events:
        if event["message"] == "Starting to check PR":
            current_pr = event["pr_nb"]
            current_pr_events = [event]
            continue

        if current_pr is not None:
            current_pr_events.append(event)
            if event["message"] == "Done with PR":
                logs_for_pr = pr_to_logs.get(current_pr, [])
                logs_for_pr.append(current_pr_events)
                pr_to_logs[current_pr] = logs_for_pr
                current_pr = None

    # keep last run for each PR
    events_to_keep = []
    for pr in pr_numbers:
        logs_for_pr = pr_to_logs.get(pr, [])
        if not logs_for_pr:
            print(f"Warning: No logs found for PR {pr}")
            continue
        logs_for_pr.sort(
            key=lambda log: log[0]["timestamp"])
        most_recent_log = logs_for_pr[-1]
        for event in most_recent_log:
            events_to_keep.append(event)

    return events_to_keep


def start_logging():
    atexit.register(store_logs)
