from collections import Counter
from typing import Dict
from flask import Flask, render_template
import json
import glob
import argparse
from datetime import datetime, timedelta
from buggpt.util.LogParser import PRInfo, compute_pr_number_to_info

app = Flask("BugGPT Web UI")


parser = argparse.ArgumentParser(description="Web UI for BugGPT")
parser.add_argument("--files", help="Log file(s) to process",
                    type=str, required=False, nargs="+")
parser.add_argument("--all", help="Use all log files", action="store_true")


def get_log_files():
    # Use log file passed as argument
    args = parser.parse_args()
    if args.files:
        return args.files

    logs = glob.glob('logs_*.json')

    if args.all:
        return logs

    # Get the latest log file
    logs.sort()
    return [logs[-1]]


pr_number_to_info: Dict[int, PRInfo] = {}


def summarize_status():
    summary = Counter()
    for pr_info in pr_number_to_info.values():
        summary["total"] += 1
        summary[pr_info.status] += 1
    return summary


def parse_time_stamp(time_stamp):
    format_strs = ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]
    for format_str in format_strs:
        try:
            return datetime.strptime(time_stamp, format_str)
        except ValueError:
            pass
    raise ValueError(f"Could not parse time stamp: {time_stamp}")


def compute_perf_stats():
    entries = []
    for log_file in get_log_files():
        with open(log_file, "r") as f:
            entries.extend(json.load(f))

    total_time = parse_time_stamp(entries[-1]["timestamp"]) - \
        parse_time_stamp(entries[0]["timestamp"])

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
                previous_message_prefix, timedelta(0)) + (parse_time_stamp(current_timestamp) - parse_time_stamp(previous_timestamp))
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
    global pr_number_to_info
    pr_number_to_info = compute_pr_number_to_info(get_log_files())
    summary = summarize_status()
    perf_stats = compute_perf_stats()
    return render_template("index.html", summary=summary, data=pr_number_to_info.values(), perf_stats=perf_stats, color_mapping=status_colors)


@app.route('/pr<int:number>')
def pr_page(number):
    global pr_number_to_info
    pr_number_to_info = compute_pr_number_to_info(get_log_files())
    pr_info = pr_number_to_info[number]

    return render_template('pr.html', pr_info=pr_info)


if __name__ == "__main__":
    args = parser.parse_args()
    app.run(debug=True, port=4000)
