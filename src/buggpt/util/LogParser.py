from datetime import datetime
from enum import Enum
import json
import re
import argparse
from buggpt.util.Logs import Event


nb_test_generated_pattern = r"^Generated (\d+) tests"


class Classification(Enum):
    UNKNOWN = 0
    INTENDED_CHANGE = 1
    COINCIDENTAL_FIX = 2
    REGRESSION = 3


class ClassificationResult:
    def __init__(self, test_code: str, old_output: str, new_output: str):
        self.test_code = test_code
        self.old_output = old_output
        self.new_output = new_output
        self.classification: Classification = Classification.UNKNOWN


class PRResult:
    def __init__(self, number, entries):
        self.number = number
        self.entries = entries

        # initialize details
        self.title = None
        self.url = None
        self.ignored = False
        self.ignored_reason = None
        self.nb_generated_tests = 0
        self.nb_test_executions = 0
        self.nb_test_failures = 0
        self.nb_different_behavior = 0
        self.classification_results = []

        # fill details with proper values
        for entry in self.entries:
            if entry["message"].startswith("Starting to check PR"):
                self.title = entry["title"]
                self.url = entry["url"]

            if entry["message"].startswith("Ignoring"):
                self.ignored = True
                self.ignored_reason = entry["message"]

            nb_generated_tests_match = re.search(
                nb_test_generated_pattern, entry["message"])
            if nb_generated_tests_match:
                self.nb_generated_tests += int(
                    nb_generated_tests_match.group(1))

            if entry["message"] == "Test execution":
                self.nb_test_executions += 1
                if "Traceback (most recent call last)" in entry["output"]:
                    self.nb_test_failures += 1

            if entry["message"] == "Different outputs":
                self.nb_different_behavior += 1

        start_time = parse_time_stamp(entries[0]["timestamp"])
        end_time = parse_time_stamp(entries[-1]["timestamp"])
        self.time_taken = str(end_time - start_time)

        # extract classification details
        for entry_idx, entry in enumerate(self.entries):
            if entry["message"] == "Classification":
                classification_result = None
                # find test code, old output, new output by looking further up in the log
                for idx2 in range(entry_idx, -1, -1):
                    if self.entries[idx2]["message"] == "Different outputs (also after test reduction)":
                        classification_result = ClassificationResult(
                            self.entries[idx2]["test_code"], self.entries[idx2]["old_output"], self.entries[idx2]["new_output"])
                        break
                if classification_result is None:
                    raise Exception(
                        "Could not find test code, old output, new output for classification entry")

                # extract outcome of classification
                if entry["is_relevant_change"] in [True, False] and \
                        entry["is_deterministic"] in [True, False] and \
                        entry["is_public"] in [True, False] and \
                        entry["is_legal"] in [True, False] and \
                        entry["is_surprising"] in [True, False]:
                    if entry["is_relevant_change"] and \
                            entry["is_deterministic"] and \
                            entry["is_public"] and \
                            entry["is_legal"] and \
                            entry["is_surprising"]:
                        # find entry that selected the expected behavior further down in the log
                        for idx2 in range(entry_idx, len(self.entries)):
                            if self.entries[idx2]["message"] == "Selected expected behavior":
                                if self.entries[idx2]["expected_output"] == 1:
                                    classification_result.classification = Classification.REGRESSION
                                elif self.entries[idx2]["expected_output"] == 2:
                                    classification_result.classification = Classification.COINCIDENTAL_FIX
                                break
                    else:
                        classification_result.classification = Classification.INTENDED_CHANGE

                self.classification_results.append(classification_result)

    def status(self):
        if self.ignored:
            return "ignored"

        final_classification = Classification.UNKNOWN
        for cls in self.classification_results:
            if cls.classification.value > final_classification.value:
                final_classification = cls.classification

        if final_classification == Classification.UNKNOWN and self.nb_test_executions > 0:
            return "checked"
        else:
            return final_classification.name.lower()

    def summary(self):
        s = self.status()
        if s == "ignored":
            return self.ignored_reason
        elif s == "checked":
            return f"{self.nb_generated_tests} generated tests, {self.nb_test_executions} test executions, {self.nb_test_failures} failures ({100 * self.nb_test_failures / self.nb_test_executions:.1f}%)"
        elif s == "intended_change":
            return f"{self.nb_generated_tests} generated tests, {self.nb_test_executions} test executions, {self.nb_test_failures} failures ({100 * self.nb_test_failures / self.nb_test_executions:.1f}%), {len(self.classification_results)} differences"
        else:
            assert s in ["coincidental_fix", "regression"]
            nb_intended_changes = 0
            nb_coincidental_fixes = 0
            nb_regressions = 0
            for cls in self.classification_results:
                if cls.classification == Classification.INTENDED_CHANGE:
                    nb_intended_changes += 1
                elif cls.classification == Classification.COINCIDENTAL_FIX:
                    nb_coincidental_fixes += 1
                elif cls.classification == Classification.REGRESSION:
                    nb_regressions += 1

            return f"{self.nb_generated_tests} generated tests, {self.nb_test_executions} test executions, {self.nb_test_failures} failures ({100 * self.nb_test_failures / self.nb_test_executions:.1f}%), {len(self.classification_results)} differences ({nb_intended_changes} intended, {nb_coincidental_fixes} coincidental, {nb_regressions} regressions)"

    def __str__(self):
        return f"PR {self.number}: {self.status()} -- {self.summary()}"


def parse_log_files(log_files):
    pr_results = []
    meta_entries = []

    for log_file in log_files:
        with open(log_file, "r") as f:
            entries = json.load(f)

        current_pr_number = None
        current_entries = []
        for entry in entries:
            if entry["message"] == "Starting to check PR":
                current_pr_number = entry["pr_nb"]
                current_entries = [entry]
            elif entry["pr_nb"] == -1:
                entry["pr_nb"] = current_pr_number
                current_entries.append(entry)
            elif entry["pr_nb"] == 0:
                meta_entries.append(entry)
            elif entry["message"] == "Done with PR":
                current_entries.append(entry)
                pr_results.append(
                    PRResult(current_pr_number, current_entries))
                current_pr_number = None
                current_entries = []
            elif entry["pr_nb"] == current_pr_number:
                current_entries.append(entry)
            else:
                raise Exception(f"Unexpected state during parsing.\n{entry}")

    return pr_results, meta_entries


def parse_time_stamp(time_stamp):
    format_strs = ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]
    for format_str in format_strs:
        try:
            return datetime.strptime(time_stamp, format_str)
        except ValueError:
            pass
    raise ValueError(f"Could not parse time stamp: {time_stamp}")


def pr_results_as_dict(pr_results):
    pr_number_to_result = {}
    for pr_result in pr_results:
        if pr_result.number in pr_number_to_result:
            raise ValueError(
                f"PR number {pr_result.number} has multiple results.")
        pr_number_to_result[pr_result.number] = pr_result
    return pr_number_to_result


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
    pr_results, meta_results = parse_log_files(args.files)
    print(f"Found {len(pr_results)} PRs and {
          len(meta_results)} meta-results in log files.")
    print()
    for pr_result in pr_results:
        print(f"PR {pr_result.number}: {len(pr_result.entries)} entries, {
              len(pr_result.classification_results)} classification results")
        print(f"Status: {pr_result.status()}")
        print(f"Summary: {pr_result.summary()}")
        print()

    if args.extract_done_prs:
        done_pr_nbs = [r.number for r in pr_results]
        write_as_log(done_pr_nbs)
