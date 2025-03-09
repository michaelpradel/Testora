from collections import Counter
from typing import Dict, List
from flask import Flask, render_template
import argparse
from datetime import timedelta
from testora.util.LogParser import PRResult, parse_log_files, parse_time_stamp, pr_results_as_dict

app = Flask("Testora Web UI")


parser = argparse.ArgumentParser(description="Web UI for Testora")
parser.add_argument("--files", help="Log file(s) to process",
                    type=str, required=False, nargs="+")

pr_results: List[PRResult] = []
pr_number_to_result: Dict[int, PRResult] = {}


def summarize_status():
    summary = Counter()
    for pr_result in pr_results:
        summary["total"] += 1
        summary[pr_result.status()] += 1

    # add percentages
    for key in summary:
        if key != "total":
            percentage = (int(summary[key]) / summary['total']) * 100
            summary[key] = f"{summary[key]} ({percentage:.1f}%)"

    return summary


def compute_perf_stats(entries):
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
    "unknown": "#FFFFE0",
    "checked": "#D3D3D3",
    "intended_change": "#CCFFCC",
    "coincidental_fix": "#CBC3E3",
    "regression": "#FFCCCC",
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
    global pr_results, pr_number_to_result
    pr_results, _ = parse_log_files(args.files)
    summary = summarize_status()
    pr_number_to_result = pr_results_as_dict(pr_results)
    return render_template("index.html", summary=summary, data=pr_results, color_mapping=status_colors)


@app.route('/pr<int:number>')
def pr_page(number):
    pr_result = pr_number_to_result[int(number)]
    perf_stats = compute_perf_stats(pr_result.entries)
    return render_template('pr.html', pr_result=pr_result, perf_stats=perf_stats)


if __name__ == "__main__":
    args = parser.parse_args()
    app.run(debug=True, port=4000)
