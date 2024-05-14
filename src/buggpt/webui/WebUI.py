from collections import Counter
from dataclasses import dataclass, field
from flask import Flask, render_template
import json
import glob
import argparse
import re
from datetime import datetime, timedelta

app = Flask("BugGPT Web UI")


parser = argparse.ArgumentParser(description="Web UI for BugGPT")
parser.add_argument("--file", help="Log file to process",
                    type=str, required=False)
parser.add_argument("--all", help="Use all log files", action="store_true")


def get_log_files():
    # Use log file passed as argument
    args = parser.parse_args()
    if args.file:
        return [args.file]

    logs = glob.glob('logs_*.json')

    if args.all:
        return logs

    # Get the latest log file
    logs.sort()
    return [logs[-1]]


@dataclass
class PRInfo:
    number: int
    url: str
    title: str = "(title missing)"
    entries: list = field(default_factory=list)
    summary: str = "(summary missing)"
    status: str = "(unknown)"


pr_number_to_info = {}


def compute_pr_number_to_info():
    if len(pr_number_to_info) != 0:
        return

    entries = []
    for log_file in get_log_files():
        with open(log_file, "r") as f:
            entries.extend(json.load(f))

    previous_pr_number = 0
    for entry in entries:
        if entry["pr_nb"] == -1:
            entry["pr_nb"] = previous_pr_number
        pr_info = pr_number_to_info.get(entry["pr_nb"],
                                        PRInfo(
                                            number=entry["pr_nb"],
                                            url=f"https://github.com/pandas-dev/pandas/pull/{entry['pr_nb']}"
        ))
        pr_info.entries.append(entry)
        pr_number_to_info[entry["pr_nb"]] = pr_info
        previous_pr_number = entry["pr_nb"]

    fill_details()


def fill_details():
    nb_test_generated_pattern = r"^Generated (\d+) tests"

    for pr_info in pr_number_to_info.values():
        is_regression = False
        is_intended_difference = False
        is_unclear = False
        is_not_in_main = None
        nb_generated_tests = 0
        nb_test_executions = 0
        nb_observed_differences = 0
        selected_behavior = 0
        for entry in pr_info.entries:
            if entry["message"].startswith("Starting to check PR"):
                pr_info.title = entry["title"]

            if entry["message"].startswith("Ignoring"):
                pr_info.status = "ignored"
                pr_info.summary = entry["message"]
                break

            nb_generated_tests_match = re.search(
                nb_test_generated_pattern, entry["message"])
            if nb_generated_tests_match:
                nb_generated_tests += int(nb_generated_tests_match.group(1))

            if entry["message"] == "Test execution":
                nb_test_executions += 1

            if entry["message"] == "Classification":
                if entry["is_relevant_change"] and entry["is_deterministic"] and entry["is_regression_bug"]:
                    entry["message"] = "Classification: Regression"
                    is_regression = True
                elif entry["is_regression_bug"] == False:
                    entry["message"] = "Classification: Intended"
                    is_intended_difference = True
                else:
                    entry["message"] = "Classification: Unclear"
                    is_unclear = True
                nb_observed_differences += 1

            if entry["message"] == "Difference not present in main anymore":
                is_not_in_main = True

            if entry["message"] == "Selected expected behavior":
                selected_behavior = int(entry["expected_output"])

        if nb_test_executions > 0:
            pr_info.status = "tests executed"
            pr_info.summary = f"{nb_generated_tests} generated tests, {nb_test_executions} test executions"

        if is_regression:
            if selected_behavior == 1:
                pr_info.status = "regression bug"
                pr_info.summary += f", {nb_observed_differences} differences"
                if is_not_in_main:
                    pr_info.summary += ", not in main"
            elif selected_behavior == 2:
                pr_info.status = "coincidental fix"
                pr_info.summary += f", {nb_observed_differences} differences"
            else:
                pr_info.status = "unclear classification"
                pr_info.summary += f", {nb_observed_differences} differences"
        elif is_intended_difference:
            pr_info.status = "intended difference"
            pr_info.summary += f", {nb_observed_differences} differences"
        elif is_unclear:
            pr_info.status = "unclear classification"
            pr_info.summary += f", {nb_observed_differences} differences"


def summarize_status():
    summary = Counter()
    for pr_info in pr_number_to_info.values():
        summary["total"] += 1
        summary[pr_info.status] += 1
    return summary


def compute_perf_stats():
    format_str = "%Y-%m-%dT%H:%M:%S.%f"

    entries = []
    for log_file in get_log_files():
        with open(log_file, "r") as f:
            entries.extend(json.load(f))

    total_time = datetime.strptime(entries[-1]["timestamp"], format_str) - \
        datetime.strptime(entries[0]["timestamp"], format_str)

    message_prefix_to_timedelta = {}
    message_prefix_to_nb = Counter()
    previous_timestamp = None
    previous_message_prefix = None

    for entry in entries:
        if previous_timestamp is None:
            previous_timestamp = entry["timestamp"]
            previous_message_prefix = entry["message"].split(" ")[0]
        else:
            current_timestamp = entry["timestamp"]
            current_message_prefix = entry["message"].split(" ")[0]
            message_prefix_to_timedelta[previous_message_prefix] = message_prefix_to_timedelta.get(
                previous_message_prefix, timedelta(0)) + (datetime.strptime(current_timestamp, format_str) - datetime.strptime(previous_timestamp, format_str))
            message_prefix_to_nb[previous_message_prefix] += 1
            previous_timestamp = current_timestamp
            previous_message_prefix = current_message_prefix

    # sort by time and keep only top-k
    message_prefix_to_timedelta = dict(
        sorted(message_prefix_to_timedelta.items(), key=lambda item: item[1], reverse=True)[:6])

    result = [["All", len(entries), total_time, total_time / len(entries)]]
    for message_prefix, time in message_prefix_to_timedelta.items():
        if message_prefix in ["Done", "Starting"]:
            continue
        result.append([message_prefix, message_prefix_to_nb[message_prefix], time,
                       time / message_prefix_to_nb[message_prefix]])

    return result


status_colors = {
    "regression bug": "#FFCCCC",
    "coincidental fix": "#CBC3E3",
    "intended difference": "#CCFFCC",
    "unclear classification": "#FFFFE0",
    "tests executed": "#D3D3D3",
}


def nl2br(value):
    if type(value) == str:
        return value.replace("\n", "<br>")
    else:
        return value


app.jinja_env.filters["nl2br"] = nl2br


def escape_tags(value):
    if type(value) == str:
        return value.replace("<", "&lt;").replace(">", "&gt;")
    else:
        return value


app.jinja_env.filters["escape_tags"] = escape_tags


@app.route('/')
def main_page():
    compute_pr_number_to_info()
    summary = summarize_status()
    perf_stats = compute_perf_stats()
    return render_template("index.html", summary=summary, data=pr_number_to_info.values(), perf_stats=perf_stats, color_mapping=status_colors)


@app.route('/pr<int:number>')
def pr_page(number):
    compute_pr_number_to_info()
    pr_info = pr_number_to_info[number]

    return render_template('pr.html', pr_info=pr_info)


if __name__ == "__main__":
    args = parser.parse_args()
    app.run(debug=True)
