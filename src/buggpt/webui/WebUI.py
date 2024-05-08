from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List
from flask import Flask, render_template
import json
import glob
import argparse

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
        pr_number = entry["pr_nb"]
        if pr_number == -1:
            pr_number = previous_pr_number
        pr_info = pr_number_to_info.get(pr_number,
                                        PRInfo(
                                            number=pr_number,
                                            url=f"https://github.com/pandas-dev/pandas/pull/{pr_number}"
                                        ))
        pr_info.entries.append(entry)
        pr_number_to_info[pr_number] = pr_info
        previous_pr_number = pr_number

    fill_details()


def fill_details():
    for pr_info in pr_number_to_info.values():
        for entry in pr_info.entries:
            if entry["message"].startswith("Starting to check PR"):
                pr_info.title = entry["title"]

            if entry["message"].startswith("Ignoring"):
                pr_info.status = "ignored"
                pr_info.summary = entry["message"]
                break

            if entry["message"] == "Test execution":
                pr_info.status = "tests executed"

            if entry["message"] == "Classification":
                if entry["is_relevant_change"] and entry["is_regression_bug"]:
                    pr_info.status = "regression bug"
                    entry["message"] = "Classification: Regression"
                else:
                    pr_info.status = "intended difference"
                    entry["message"] = "Classification: Intended"
                pr_info.summary = f"is_relevant_change={entry['is_relevant_change']}, is_regression_bug={entry['is_regression_bug']}, old_is_crash={entry['old_is_crash']}, new_is_crash={entry['new_is_crash']}"
                break


def summarize_status():
    summary = Counter()
    for pr_info in pr_number_to_info.values():
        summary["total"] += 1
        summary[pr_info.status] += 1
    return summary


status_colors = {
    "regression bug": "#FFCCCC",
    "intended difference": "#CCFFCC",
    "tests executed": "#D3D3D3",
}


def nl2br(value):
    if type(value) == str:
        return value.replace("\n", "<br>")
    else:
        return value


app.jinja_env.filters["nl2br"] = nl2br


@app.route('/')
def main_page():
    compute_pr_number_to_info()
    summary = summarize_status()
    return render_template("index.html", summary=summary, data=pr_number_to_info.values(), color_mapping=status_colors)


@app.route('/pr<int:number>')
def pr_page(number):
    compute_pr_number_to_info()
    pr_info = pr_number_to_info[number]

    return render_template('pr.html', pr_info=pr_info)


if __name__ == "__main__":
    args = parser.parse_args()
    app.run(debug=True)
