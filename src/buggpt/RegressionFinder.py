import glob
import json
import re
from github import Github, Auth
from git import Repo
from buggpt.execution.DockerExecutor import DockerExecutor
from buggpt.execution.TestExecution import TestExecution
from buggpt.llms.LLMCache import LLMCache
from buggpt.prompts.RegressionClassificationPrompt import RegressionClassificationPrompt
from buggpt.prompts.RegressionTestGeneratorPrompt import RegressionTestGeneratorPrompt
from buggpt.util.PullRequest import PullRequest
from buggpt.execution import PythonProjects
import buggpt.llms.OpenAIGPT as uncached_llm
from buggpt.util.Logs import ClassificationEvent, PREvent, TestExecutionEvent, append_event, Event, ComparisonEvent, LLMEvent
llm = LLMCache(uncached_llm)


def clean_output(output):
    # pandas-specific cleaning (to remove build output)
    result = []
    for line in output.split("\n"):
        if line == "+ /usr/local/bin/ninja":
            continue
        # check if line starts with "[1/1]", "[2/4]", etc.
        if len(line) >= 6 and line.startswith("[") and \
                line[1].isdigit() and \
                line[2] == "/" and \
                line[3].isdigit() and \
                line[4] == "]" and \
                line[5] == " ":
            continue
        result.append(line)
    return "\n".join(result)


def execute_tests_on_commit(pr_number, test_executions, commit):
    docker_executor = DockerExecutor("pandas-dev")

    cloned_repo.git.checkout(commit)
    # to trigger pandas re-compilation
    docker_executor.execute_python_code("import pandas")

    for test_execution in test_executions:
        output = docker_executor.execute_python_code(test_execution.code)
        test_execution.output = clean_output(output)
        append_event(TestExecutionEvent(pr_nb=pr_number,
                                        message="Test execution",
                                        code=test_execution.code,
                                        output=output))


def is_crash(output):
    return "Traceback (most recent call last)" in output


def check_pr(pr):
    # ignore if too few or too many files changed
    if len(pr.non_test_modified_python_files) == 0:
        append_event(Event(
            pr_nb=pr.github_pr.number, message="Ignoring because no non-test Python files were modified"))
        return
    if len(pr.non_test_modified_python_files) > 3:
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because too many non-test Python files were modified"))
        return

    # ignore if PR has more than one parent
    if len(pr.parents) != 1:
        append_event(
            Event(pr_nb=pr.number, message=f"Ignoring because PR has != 1 parent"))
        return

    # ignore if only comment changes
    if not pr.has_non_comment_change():
        append_event(
            Event(pr_nb=pr.number, message="Ignoring because only comments changed"))
        return

    # extract diff and names of changed functions
    diff = pr.get_diff()
    changed_functions = pr.get_changed_function_names()

    if len(diff.split("\n")) > 200:
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because diff too long"))
        return

    # generate tests via LLM
    prompt = RegressionTestGeneratorPrompt(
        github_repo.name, changed_functions, diff)
    raw_answer = llm.query(prompt)
    append_event(LLMEvent(pr_nb=pr.number,
                 message="Raw answer", content=raw_answer))
    generated_tests = prompt.parse_answer(raw_answer)
    for idx, test in enumerate(generated_tests):
        append_event(LLMEvent(pr_nb=pr.number,
                     message=f"Generated test {idx+1}", content=test))

    # make sure the tests import pandas
    updated_tests = []
    for test in generated_tests:
        if "import pandas" not in test:
            updated_tests.append("import pandas as pd\n" + test)
        else:
            updated_tests.append(test)

    # execute tests
    old_executions = [TestExecution(t) for t in generated_tests]
    new_executions = [TestExecution(t) for t in generated_tests]

    execute_tests_on_commit(pr.number, old_executions, pr.pre_commit)
    execute_tests_on_commit(pr.number, new_executions, pr.post_commit)

    for (old_execution, new_execution) in zip(old_executions, new_executions):
        difference_found = old_execution.output != new_execution.output
        append_event(ComparisonEvent(pr_nb=pr.number,
                                     message=f"{'Different' if difference_found else 'Same'} outputs",
                                     test_code=old_execution.code, old_output=old_execution.output,
                                     new_output=new_execution.output))

        # if difference found, classify regression
        if difference_found:
            assert old_execution.code == new_execution.code
            prompt = RegressionClassificationPrompt(
                github_repo.name, pr, changed_functions, old_execution.code, old_execution.output, new_execution.output)
            raw_answer = llm.query(prompt)
            append_event(LLMEvent(pr_nb=pr.number,
                                  message="Raw answer", content=raw_answer))
            is_relevant_change, is_regression_bug = prompt.parse_answer(
                raw_answer)
            append_event(ClassificationEvent(pr_nb=pr.number,
                                             message="Classification",
                                             is_relevant_change=is_relevant_change,
                                             is_regression_bug=is_regression_bug,
                                             old_is_crash=is_crash(
                                                 old_execution.output),
                                             new_is_crash=is_crash(new_execution.output)))


def get_recent_prs(github_repo, nb=50):
    all_prs = github_repo.get_pulls(state="closed")
    merged_prs = []
    for github_pr in all_prs:
        if github_pr.is_merged():
            merged_prs.append(github_pr)
        if len(merged_prs) >= nb:
            break
    return merged_prs


def find_prs_checked_in_past():
    done_prs = set()

    logs = glob.glob('logs_*.json')
    for log in logs:
        with open(log, "r") as f:
            entries = json.load(f)
        for entry in entries:
            done_prs.add(entry["pr_nb"])

    return done_prs


# setup for testing on pandas
cloned_repo = Repo("./data/repos/pandas")
cloned_repo.git.checkout("main")
cloned_repo.git.pull()
token = open(".github_token", "r").read().strip()
github = Github(auth=Auth.Token(token))
project = PythonProjects.pandas_project
github_repo = github.get_repo(project.project_id)

# testing with motivating example
# pr = github_repo.get_pull(55108)
# check_pr(pr, github_repo, cloned_repo)

# run on recent PRs, excluding those we've already checked
# done_pr_numbers = find_prs_checked_in_past()
github_prs = get_recent_prs(github_repo, nb=20)
prs = [PullRequest(github_pr, github_repo, cloned_repo) for github_pr in github_prs]
for pr in prs:
    # if pr.number in done_pr_numbers:
    #     print(f"Skipping PR {pr.number} because already analyzed")
    #     continue

    append_event(PREvent(pr_nb=pr.number,
                         message="Starting to check PR",
                         title=pr.github_pr.title, url=pr.github_pr.html_url))
    check_pr(pr)
    append_event(PREvent(pr_nb=pr.number,
                         message="Done with PR",
                         title=pr.github_pr.title, url=pr.github_pr.html_url))

# testing on specific PRs
# interesting_pr_numbers = [58479, 58390, 58369, 58322, 58148]
# interesting_pr_numbers = [55108, 56841]  # known regression bugs
# prs = [github_repo.get_pull(pr_nb) for pr_nb in interesting_pr_numbers]
# for pr in prs:
#     append_event(PREvent(pr_nb=pr.number,
#                          message="Starting to check PR",
#                          title=pr.github_pr.title, url=pr.github_pr.html_url))
#     check_pr(pr, github_repo, cloned_repo)
#     append_event(PREvent(pr_nb=pr.number,
#                          message="Done with PR",
#                          title=pr.github_pr.title, url=pr.github_pr.html_url))

