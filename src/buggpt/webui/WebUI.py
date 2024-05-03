from dataclasses import dataclass, field
from typing import Dict, List
from flask import Flask, render_template
import json
import glob

app = Flask("BugGPT Web UI")


def latest_log_file():
    # Get the latest log file
    logs = glob.glob('logs_*.json')
    logs.sort()
    return logs[-1]


@dataclass
class PRInfo:
    number: int
    url: str
    title: str = "(title missing)"
    entries: list = field(default_factory=list)
    status: str = "(unknown)"


pr_number_to_info = {}


def compute_pr_number_to_info():
    if len(pr_number_to_info) != 0:
        return

    with open(latest_log_file(), "r") as f:
        entries = json.load(f)

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

    determine_status()


def determine_status():
    for pr_info in pr_number_to_info.values():
        if any("unintended" in entry["message"] for entry in pr_info.entries):
            pr_info.status = "unintended"
        elif any("intended" in entry["message"] for entry in pr_info.entries):
            pr_info.status = "intended"
        else:
            pr_info.status = "unknown"


status_colors = {
    "intended": "#CCFFCC",
    "unintended": "#FFCCCC",
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

    # Pass the data to the template
    return render_template("index.html", data=pr_number_to_info.values(), color_mapping=status_colors)


@app.route('/pr<int:number>')
def pr_page(number):
    compute_pr_number_to_info()
    pr_info = pr_number_to_info[number]

    return render_template('pr.html', pr_info=pr_info)


if __name__ == "__main__":
    app.run(debug=True)
