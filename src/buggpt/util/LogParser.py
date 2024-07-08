from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Dict
import re
import argparse
from buggpt.util.Logs import Event


@dataclass
class PRInfo:
    number: int
    url: str
    title: str = "(title missing)"
    entries: list = field(default_factory=list)
    nb_test_executions: int = 0
    summary: str = "(summary missing)"
    status: str = "(unknown)"
    time_taken: str = ""


def parse_time_stamp(time_stamp):
    format_strs = ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]
    for format_str in format_strs:
        try:
            return datetime.strptime(time_stamp, format_str)
        except ValueError:
            pass
    raise ValueError(f"Could not parse time stamp: {time_stamp}")


def compute_pr_number_to_info(log_files: list[str]):
    pr_number_to_info: Dict[int, PRInfo] = {}

    if len(pr_number_to_info) != 0:
        return

    entries = []
    for log_file in log_files:
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

    fill_details(pr_number_to_info)

    return pr_number_to_info


def fill_details(pr_number_to_info: Dict[int, PRInfo]):
    nb_test_generated_pattern = r"^Generated (\d+) tests"

    for pr_info in pr_number_to_info.values():
        is_regression = False
        is_intended_difference = False
        is_unclear = False
        is_not_in_main = None
        nb_generated_tests = 0
        nb_test_executions = 0
        nb_test_failures = 0
        nb_observed_differences = 0
        selected_behavior = 0
        for entry in pr_info.entries:
            if entry["message"].startswith("Starting to check PR"):
                pr_info.title = entry["title"]
                pr_info.url = entry["url"]

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
                if "Traceback (most recent call last)" in entry["output"]:
                    nb_test_failures += 1

            if entry["message"] == "Classification":
                if entry["is_relevant_change"] and entry["is_deterministic"] and entry["is_public"] and entry["is_legal"] and entry["is_surprising"]:
                    entry["message"] = "Classification: Regression"
                    is_regression = True
                elif entry["is_relevant_change"] in [True, False] and \
                        entry["is_deterministic"] in [True, False] and \
                        entry["is_public"] in [True, False] and \
                        entry["is_legal"] in [True, False] and \
                        entry["is_surprising"] in [True, False]:
                    entry["message"] = "Classification: Intended"
                    is_intended_difference = True
                else:
                    entry["message"] = "Classification: Unclear"
                    is_unclear = True
                nb_observed_differences += 1

            if entry["message"] == "Difference not present in main anymore":
                is_not_in_main = True

            if entry["message"] == "Selected expected behavior":
                # prioritize "1", i.e., old version is expected, so we see it as a regression bug
                if selected_behavior != 1:
                    selected_behavior = int(entry["expected_output"])

        if nb_test_executions > 0:
            pr_info.status = "tests executed"
            failure_percentage = 100 * nb_test_failures / nb_test_executions
            pr_info.summary = f"{nb_generated_tests} generated tests, {nb_test_executions} test executions, {nb_test_failures} failures ({failure_percentage:.1f}%)"

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

        pr_info.nb_test_executions = nb_test_executions

        start_time = parse_time_stamp(pr_info.entries[0]["timestamp"])
        end_time = parse_time_stamp(pr_info.entries[-1]["timestamp"])
        pr_info.time_taken = str(end_time - start_time)


def extract_done_prs(pr_number_to_info: Dict[int, PRInfo]):
    done_pr_nbs = []
    for pr_info in pr_number_to_info.values():
        if pr_info.nb_test_executions > 0:
            done_pr_nbs.append(pr_info.number)
    return done_pr_nbs


def write_as_log(pr_nbs: list[int]):
    event_log = []
    for pr_nb in pr_nbs:
        event_log.append(Event(pr_nb=pr_nb, message="Done with PR"))

    with open("done_prs.json", "w") as f:
        json.dump([evt.dict() for evt in event_log], f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", help="Log file(s) to process",
                        type=str, required=True, nargs="+")
    parser.add_argument("--extract_done_prs", action="store_true",
                        help="Create a log-like file with all PRs that have been fully analyzed")

    args = parser.parse_args()
    pr_number_to_info = compute_pr_number_to_info(args.files)
    if args.extract_done_prs:
        done_pr_nbs = extract_done_prs(pr_number_to_info)
        write_as_log(done_pr_nbs)
