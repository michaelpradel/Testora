from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re
import argparse
from testora.util.Logs import Event
from testora.util.ClassificationResult import Classification, ClassificationResult

nb_test_generated_pattern = r"^Generated (\d+) tests"


@dataclass
class DifferentiatingTest:
    test_code: str
    old_output: str
    new_output: str

    def to_json(self):
        return {
            'test_code': self.test_code,
            'old_output': self.old_output,
            'new_output': self.new_output
        }

    def from_json(json):
        return DifferentiatingTest(
            test_code=json['test_code'],
            old_output=json['old_output'],
            new_output=json['new_output']
        )


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
        self.nb_diff_covered_tests = 0
        self.avg_old_diff_coverage = 0.0
        self.avg_new_diff_coverage = 0.0
        self.nb_different_behavior = 0
        self.differentiating_tests = []
        self.classification_results = []

        self.input_tokens = 0
        self.output_tokens = 0
        self.input_tokens_test_gen = 0
        self.output_tokens_test_gen = 0
        self.input_tokens_test_refinement = 0
        self.output_tokens_test_refinement = 0
        self.input_tokens_test_exec = 0
        self.output_tokens_test_exec = 0
        self.input_tokens_classification = 0
        self.output_tokens_classification = 0

        # fill details with proper values
        old_diff_coverages = []
        new_diff_coverages = []

        self.time_taken = parse_time_stamp(self.entries[-1]["timestamp"]) - \
            parse_time_stamp(self.entries[0]["timestamp"])
        phase = "test_gen"  # test_gen, test_refinement, test_exec, classification
        self.time_taken_test_gen = timedelta(0)
        self.time_taken_test_refinement = timedelta(0)
        self.time_taken_test_exec = timedelta(0)
        self.time_taken_classification = timedelta(0)
        last_used_time_stamp = parse_time_stamp(self.entries[0]["timestamp"])

        def update_time_taken(entry):
            nonlocal last_used_time_stamp, phase
            current_time_stamp = parse_time_stamp(entry["timestamp"])
            time_taken = current_time_stamp - last_used_time_stamp
            last_used_time_stamp = current_time_stamp
            if phase == "test_gen":
                self.time_taken_test_gen += time_taken
            elif phase == "test_refinement":
                self.time_taken_test_refinement += time_taken
            elif phase == "test_exec":
                self.time_taken_test_exec += time_taken
            elif phase == "classification":
                self.time_taken_classification += time_taken

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

            if entry["message"] == "Pre-classification":
                diff_test = DifferentiatingTest(
                    entry["test_code"],
                    entry["old_output"],
                    entry["new_output"])
                self.differentiating_tests.append(diff_test)

            if entry["message"] == "Different outputs":
                self.nb_different_behavior += 1

            if entry["message"] == "Diff coverage":
                old_coverage_results, new_coverage_results = entry["details"].split(
                    ", ")

                old_has_diff_coverage, old_diff_coverage = self._extract_coverage_details(
                    old_coverage_results)
                new_has_diff_coverage, new_diff_coverage = self._extract_coverage_details(
                    new_coverage_results)
                if old_has_diff_coverage or new_has_diff_coverage:
                    self.nb_diff_covered_tests += 1
                old_diff_coverages.append(old_diff_coverage)
                new_diff_coverages.append(new_diff_coverage)

            # keep track of phase we're in and update time taken for each phase
            if entry["message"].startswith("Querying"):
                if "has an undefined reference" in entry["content"] and "Fix it" in entry["content"]:
                    update_time_taken(entry)
                    phase = "test_refinement"
                    test_refinemement_start_time = parse_time_stamp(
                        entry["timestamp"])
            if entry["message"].startswith("Compiling"):
                update_time_taken(entry)
                phase = "test_exec"
                test_exec_start_time = parse_time_stamp(entry["timestamp"])
            if entry["message"] == "Pre-classification":
                update_time_taken(entry)
                phase = "classification"
                classification_start_time = parse_time_stamp(
                    entry["timestamp"])

            if entry["message"] == "Token usage":
                pattern = r"prompt=(\d+), completion=(\d+)"
                match = re.search(pattern, entry["content"])
                input_tokens = int(match.group(1))
                output_tokens = int(match.group(2))
                self.input_tokens += input_tokens
                self.output_tokens += output_tokens

                # update token usage based on phase
                if phase == "test_gen":
                    self.input_tokens_test_gen += input_tokens
                    self.output_tokens_test_gen += output_tokens
                elif phase == "test_refinement":
                    self.input_tokens_test_refinement += input_tokens
                    self.output_tokens_test_refinement += output_tokens
                elif phase == "test_exec":
                    self.input_tokens_test_exec += input_tokens
                    self.output_tokens_test_exec += output_tokens
                elif phase == "classification":
                    self.input_tokens_classification += input_tokens
                    self.output_tokens_classification += output_tokens

        update_time_taken(self.entries[-1])

        if len(old_diff_coverages) > 0:
            self.avg_old_diff_coverage = sum(
                old_diff_coverages) / len(old_diff_coverages)
        if len(new_diff_coverages) > 0:
            self.avg_new_diff_coverage = sum(
                new_diff_coverages) / len(new_diff_coverages)

        # extract classification details
        for entry_idx, entry in enumerate(self.entries):
            if entry["message"] == "Classification":
                classification_result = ClassificationResult(
                    test_code=entry["test_code"],
                    old_output=entry["old_output"],
                    new_output=entry["new_output"],
                    classification=Classification(entry["classification"]),
                    classification_explanation=entry["classification_explanation"]
                )

                # find entry that selected the expected behavior further down in the log
                if classification_result.classification == Classification.REGRESSION:
                    for idx2 in range(entry_idx, len(self.entries)):
                        if self.entries[idx2]["message"] == "Selected expected behavior":
                            if self.entries[idx2]["expected_output"] == 1:
                                classification_result.classification = Classification.REGRESSION
                            elif self.entries[idx2]["expected_output"] == 2:
                                classification_result.classification = Classification.COINCIDENTAL_FIX
                            break

                self.classification_results.append(classification_result)

    def _extract_coverage_details(self, s):
        has_diff_coverage = False
        diff_coverage = 0.0

        pattern = r"\((\d+)/(\d+)\)"
        match = re.search(pattern, s)
        has_diff_coverage = int(match.group(1)) > 0
        diff_coverage = (int(match.group(1)) / int(match.group(2))
                         ) if int(match.group(2)) > 0 else 0.0

        return has_diff_coverage, diff_coverage

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

            return (
                f"{self.nb_generated_tests} generated tests, "
                f"{self.nb_test_executions} test executions, "
                f"{self.nb_diff_covered_tests} tests covered diff "
                f"({100 * self.nb_diff_covered_tests / self.nb_generated_tests:.1f}%), "
                f"{self.nb_test_failures} failures "
                f"({100 * self.nb_test_failures / self.nb_test_executions:.1f}%), "
                f"{len(self.classification_results)} differences("
                f"{nb_intended_changes} intended, "
                f"{nb_coincidental_fixes} coincidental, "
                f"{nb_regressions} regressions)"
            )

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
    print(f"Found {len(pr_results)} PRs and "
          f"{len(meta_results)} meta-results in log files.")
    print()
    for pr_result in pr_results:
        print(f"PR {pr_result.number}: {len(pr_result.entries)} entries, "
              f"{len(pr_result.classification_results)} classification results")
        print(f"Status: {pr_result.status()}")
        print(f"Summary: {pr_result.summary()}")
        print()

    if args.extract_done_prs:
        done_pr_nbs = [r.number for r in pr_results]
        write_as_log(done_pr_nbs)
