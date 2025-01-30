import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import List

from buggpt.evaluation import EvalTaskManager
from buggpt.evaluation.EvalTaskManager import classification_pr_nb
from buggpt.execution.TestExecution import TestExecution
from buggpt.util.DocstringRetrieval import retrieve_relevant_docstrings
from buggpt.util.LogParser import DifferentiatingTest, parse_log_files
from buggpt.RegressionFinder import classify_regression, get_repo
from buggpt.util.Logs import ClassifierEvalEvent, get_logs_as_json, reset_logs, store_logs, append_event
from buggpt.util.PullRequest import PullRequest


@dataclass
class ClassificationGroundTruth:
    @dataclass
    class LabeledDifferentiatingTest:
        test: DifferentiatingTest
        label: str
        comment: str

        def to_json(self):
            return {
                'test': self.test.to_json(),
                'label': self.label,
                'comment': self.comment
            }

        def from_json(json):
            return ClassificationGroundTruth.LabeledDifferentiatingTest(
                test=DifferentiatingTest.from_json(json['test']),
                label=json['label'],
                comment=json['comment']
            )

    pr_number: int
    log_file: str
    differentiating_tests: List[LabeledDifferentiatingTest]

    def to_json(self):
        return {
            'pr_number': self.pr_number,
            'log_file': self.log_file,
            'differentiating_tests': [test.to_json() for test in self.differentiating_tests],
        }

    def from_json(json):
        return ClassificationGroundTruth(
            pr_number=json['pr_number'],
            log_file=json['log_file'],
            differentiating_tests=[ClassificationGroundTruth.LabeledDifferentiatingTest.from_json(
                test) for test in json['differentiating_tests']]
        )


def create_ground_truth_template(log_file):
    project_name = log_file.split("/")[-2]

    target_dir = f"data/ground_truth/{project_name}"
    os.makedirs(target_dir, exist_ok=True)

    print(f"\nTrying to create ground truth template from {log_file}")

    pr_results, _ = parse_log_files([log_file])
    pr_result = pr_results[0]

    assert pr_result.nb_different_behavior == len(
        pr_result.differentiating_tests)

    if pr_result.nb_different_behavior == 0:
        print("No differentiating test case found in log file")
        return

    labeled_diff_tests = []
    for diff_test in pr_result.differentiating_tests:
        labeled_diff_test = ClassificationGroundTruth.LabeledDifferentiatingTest(
            test=diff_test,
            label="TODO",
            comment=""
        )
        labeled_diff_tests.append(labeled_diff_test)

    ground_truth = ClassificationGroundTruth(
        pr_number=pr_result.number,
        log_file=log_file,
        differentiating_tests=labeled_diff_tests
    )
    target_file = f"{target_dir}/{pr_result.number}.json"

    if os.path.exists(target_file):
        print(f"Warning: Ground truth template already exists at "
              f"{target_file}. Remove it first if you want to create a new one.")
        return

    with open(target_file, "w") as f:
        json.dump(ground_truth.to_json(), f, indent=4)
    print(f"Ground truth template created at {target_file}")


def read_ground_truth(project_name):
    ground_truth_dir = f"data/ground_truth/{project_name}"
    ground_truths = []
    for file in os.listdir(ground_truth_dir):
        if file.endswith(".json"):
            ground_truth_file = f"{ground_truth_dir}/{file}"
            with open(ground_truth_file, "r") as fp:
                ground_truth = ClassificationGroundTruth.from_json(
                    json.load(fp))
            ground_truths.append(ground_truth)
    return ground_truths


def evaluate_against_ground_truth(cloned_repo_manager, project_name, pr, diff_test):
    changed_functions = pr.get_changed_function_names()
    old_execution = TestExecution(
        code=diff_test.test.test_code,
        output=diff_test.test.old_output)
    new_execution = TestExecution(
        code=diff_test.test.test_code,
        output=diff_test.test.new_output)

    # find docstrings
    cloned_repo_of_new_commit = cloned_repo_manager.get_cloned_repo(
        pr.post_commit)
    docstrings = retrieve_relevant_docstrings(
        cloned_repo_of_new_commit, new_execution.code)

    all_predicted_as_unintended = classify_regression(project_name, pr,
                                                      changed_functions,
                                                      docstrings,
                                                      old_execution, new_execution,
                                                      no_cache=False,
                                                      nb_samples=1)
    predictions = []
    for predicted_as_unintended in all_predicted_as_unintended:
        predictions.append(
            "unintended" if predicted_as_unintended else "intended")

    append_event(ClassifierEvalEvent(
        pr_nb=pr.number,
        message="Classification result",
        label=diff_test.label,
        predictions="#".join(predictions)
    ))


def evaluate():
    # read ground truth files
    target_project_file = Path(".target_project")
    with open(target_project_file, "r") as f:
        target_project = f.read().strip()
    ground_truths = read_ground_truth(target_project)

    # run classifier and compare against ground truth
    for ground_truth in ground_truths:
        # optimization to avoid pulling when we don't have any ground truth labels anyway
        skip_all = all([diff_test.label ==
                        "TODO" for diff_test in ground_truth.differentiating_tests])
        if skip_all:
            continue

        github_repo, cloned_repo_manager = get_repo(target_project)
        github_pr = github_repo.get_pull(ground_truth.pr_number)
        pr = PullRequest(github_pr, github_repo, cloned_repo_manager)

        for diff_test in ground_truth.differentiating_tests:
            if diff_test.label == "TODO":
                print(f"Skipping test because ground truth not yet annotated")
                continue
            else:
                evaluate_against_ground_truth(
                    cloned_repo_manager, target_project, pr, diff_test)

    # store results in DB
    store_logs()
    log = get_logs_as_json()
    EvalTaskManager.write_results(target_project, classification_pr_nb,
                                  log, table_name="classification_tasks")
    reset_logs()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--create_ground_truth_template', type=str,
                        help='Create a ground truth template from the given log file(s)',
                        nargs='+')
    parser.add_argument('--evaluate', action='store_true',
                        help="Fetch classification tasks from DB and perform them")
    args = parser.parse_args()

    if args.create_ground_truth_template:
        for log_file in args.create_ground_truth_template:
            create_ground_truth_template(log_file)
    elif args.evaluate:
        evaluate()
