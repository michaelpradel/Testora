import glob
import json
from typing import List
from github import Github, Auth
from buggpt.execution.DockerExecutor import DockerExecutor
from buggpt.execution.ProgramMerger import merge_programs, separate_outputs
from buggpt.execution.TestExecution import TestExecution
from buggpt.llms.LLMCache import LLMCache
from buggpt.prompts.UndefinedRefsFixingPrompt import UndefinedRefsFixingPrompt
from buggpt.prompts.PRRegressionBugRanking import PRRegressionBugRanking
from buggpt.prompts.RegressionClassificationPromptV1 import RegressionClassificationPromptV1
from buggpt.prompts.RegressionClassificationPromptV2 import RegressionClassificationPromptV2
from buggpt.prompts.RegressionClassificationPromptV3 import RegressionClassificationPromptV3
from buggpt.prompts.RegressionClassificationPromptV4 import RegressionClassificationPromptV4
from buggpt.prompts.RegressionClassificationPromptV5 import RegressionClassificationPromptV5
from buggpt.prompts.RegressionTestGeneratorPrompt import RegressionTestGeneratorPrompt
from buggpt.prompts.SelectExpectedBehaviorPrompt import SelectExpectedBehaviorPrompt
from buggpt.util.ClonedRepoManager import ClonedRepoManager
from buggpt.util.DocstringRetrieval import retrieve_relevant_docstrings
from buggpt.util.Exceptions import BugGPTException
from buggpt.util.PullRequest import PullRequest
from buggpt.llms.OpenAIGPT import OpenAIGPT
from buggpt.util.Logs import CoverageEvent, PreClassificationEvent, start_logging, ClassificationEvent, ErrorEvent, PREvent, SelectBehaviorEvent, TestExecutionEvent, append_event, Event, ComparisonEvent, LLMEvent, get_logs_as_json, store_logs, reset_logs
from buggpt.util.PythonCodeUtil import has_private_accesses_or_fails_to_parse
from buggpt.util.UndefinedRefsFinder import get_undefined_references
from buggpt.evaluation import EvalTaskManager
from buggpt import Config
from buggpt.execution.CoverageAnalyzer import summarize_coverage

llm = LLMCache(OpenAIGPT())

if Config.classification_prompt_version == 1:
    RegressionClassificationPrompt = RegressionClassificationPromptV1
elif Config.classification_prompt_version == 2:
    RegressionClassificationPrompt = RegressionClassificationPromptV2
elif Config.classification_prompt_version == 3:
    RegressionClassificationPrompt = RegressionClassificationPromptV3
elif Config.classification_prompt_version == 4:
    RegressionClassificationPrompt = RegressionClassificationPromptV4
elif Config.classification_prompt_version == 5:
    RegressionClassificationPrompt = RegressionClassificationPromptV5


def clean_output(output):
    # remove warnings caused by coverage measurements
    cleaned_lines = []
    for line in output.split("\n"):
        if "CoverageWarning" in line:
            continue
        cleaned_lines.append(line)
    cleaned_output = "\n".join(cleaned_lines)
    
    # pandas-specific cleaning (to remove build output)
    result = []
    for line in cleaned_output.split("\n"):
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


def merge_tests_and_execute(test_executions, docker_executor) -> List[str]:
    """
    Try to merge all tests into a single program (for efficiency, to avoid repeated imports and Python engine startup).
    If this fails (e.g., due to segfault of Python), execute smaller subsets of tests at once.
    In the extreme case, will try to execute each test separately.
    """

    if len(test_executions) > 20:
        # split into chunks of at most 20 test executions
        chunks = [test_executions[i:i + 20]
                  for i in range(0, len(test_executions), 20)]
        all_outputs = []
        for chunk in chunks:
            all_outputs.extend(merge_tests_and_execute(chunk, docker_executor))
        return all_outputs

    merged_code = merge_programs([test.code for test in test_executions])
    append_event(ErrorEvent(
        pr_nb=-1, message="Merged code", details=merged_code))
    # TODO: in case we ever revive this code, use the coverage report provided here
    merged_outputs, coverage_report = docker_executor.execute_python_code(
        merged_code)
    append_event(ErrorEvent(
        pr_nb=-1, message="Merged output", details=merged_outputs))
    merged_outputs = clean_output(merged_outputs)
    outputs = separate_outputs(merged_outputs)
    if len(outputs) == len(test_executions):
        return outputs
    elif len(test_executions) == 1:
        # we can't split it any further but don't see the expected output format
        # (e.g., reaching this when code parses but raises a SyntaxError)
        return [merged_outputs]
    else:
        mid = len(test_executions) // 2
        test_executions_part1, test_executions_part2 = \
            test_executions[:mid], test_executions[mid:]
        outputs_part1 = merge_tests_and_execute(
            test_executions_part1, docker_executor)
        outputs_part2 = merge_tests_and_execute(
            test_executions_part2, docker_executor)
        return outputs_part1 + outputs_part2


def execute_test(test_execution, docker_executor):
    output, coverage_report = docker_executor.execute_python_code(
        test_execution.code)
    output = clean_output(output)
    test_execution.output = output
    test_execution.coverage_report = coverage_report


def execute_tests_on_commit(cloned_repo_manager, pr, test_executions, commit):
    cloned_repo = cloned_repo_manager.get_cloned_repo(
        commit)
    container_name = cloned_repo.container_name
    docker_executor = DockerExecutor(container_name,
                                     project_name=cloned_repo_manager.repo_name,
                                     coverage_files=pr.non_test_modified_python_files)

    append_event(
        Event(pr_nb=-1, message=f"Compiling {cloned_repo_manager.repo_name} at commit {commit} in container {container_name}"))

    # to trigger re-compilation (e.g., for pandas or scikit-learn)
    docker_executor.execute_python_code(
        f"import {cloned_repo_manager.module_name}")

    append_event(
        Event(pr_nb=pr.number, message=f"Done with compiling {cloned_repo_manager.repo_name} at commit {commit}"))

    try:
        if Config.use_program_merger:
            outputs = merge_tests_and_execute(test_executions, docker_executor)
            assert len(outputs) == len(test_executions)
            for output, test_execution in zip(outputs, test_executions):
                test_execution.output = output
                append_event(TestExecutionEvent(pr_nb=pr.number,
                                                message="Test execution",
                                                code=test_execution.code,
                                                output=output))
        else:
            for test_execution in test_executions:
                execute_test(test_execution, docker_executor)
                append_event(TestExecutionEvent(pr_nb=pr.number,
                                                message="Test execution",
                                                code=test_execution.code,
                                                output=test_execution.output))
    except RecursionError as e:
        raise BugGPTException(
            f"Exception during merge_tests_and_execute: {str(e)}")


def is_crash(output):
    return "Traceback (most recent call last)" in output or \
        "error" in output.lower() or \
        "fail" in output.lower()


def generate_tests_with_prompt(pr, prompt, model, nb_samples=1):
    raw_answer = model.query(prompt, nb_samples)
    append_event(LLMEvent(pr_nb=pr.number,
                 message="Raw answer", content="\n---(next sample)---".join(raw_answer)))

    generated_tests = prompt.parse_answer(raw_answer)
    for idx, test in enumerate(generated_tests):
        append_event(LLMEvent(pr_nb=pr.number,
                     message=f"Generated test {idx+1}", content=test))
    return generated_tests


def remove_tests_with_private_call(tests):
    result = []
    for test in tests:
        if not has_private_accesses_or_fails_to_parse(test):
            result.append(test)
    return result


def generate_tests(pr, github_repo, changed_functions):
    # prepare context used by one or more prompts
    full_diff = pr.get_full_diff()
    filtered_diff = pr.get_filtered_diff()

    all_tests = []

    if len(full_diff.split("\n")) <= 200:
        # full diff with GPT4
        prompt_full_diff = RegressionTestGeneratorPrompt(
            github_repo.name, changed_functions, full_diff)
        all_tests.extend(generate_tests_with_prompt(
            pr, prompt_full_diff, llm))

        # full diff with GPT3.5
        # all_tests.extend(generate_tests_with_prompt(
        #     pr, prompt_full_diff, gpt35, nb_samples=10))

    if len(filtered_diff.split("\n")) <= 200 and filtered_diff != full_diff:
        # filtered diff with GPT4
        prompt_filtered_diff = RegressionTestGeneratorPrompt(
            github_repo.name, changed_functions, filtered_diff)
        all_tests.extend(generate_tests_with_prompt(
            pr, prompt_filtered_diff, llm))

        # filtered diff with GPT3.5
        # all_tests.extend(generate_tests_with_prompt(
        #     pr, prompt_filtered_diff, gpt35, nb_samples=10))

    # de-dup tests
    nb_tests_before_dedup_and_cleaning = len(all_tests)
    all_tests = list(dict.fromkeys(all_tests))

    # clean tests
    all_tests = remove_tests_with_private_call(all_tests)

    append_event(Event(pr_nb=pr.number,
                 message=f"Generated {len(all_tests)} tests ({nb_tests_before_dedup_and_cleaning} before deduplication and cleaning)"))
    return all_tests


def validate_output_difference(cloned_repo_manager, pr, old_execution, new_execution):
    assert (old_execution.output is not None)
    assert (new_execution.output is not None)

    # re-execute test on old and new version and ignore flaky differences
    for _ in range(10):
        old_execution_repeated = TestExecution(old_execution.code)
        execute_tests_on_commit(cloned_repo_manager,
                                pr, [old_execution_repeated], pr.pre_commit)
        new_execution_repeated = TestExecution(new_execution.code)
        execute_tests_on_commit(cloned_repo_manager,
                                pr, [new_execution_repeated], pr.post_commit)
        if old_execution.output != old_execution_repeated.output:
            return False
        if new_execution.output != new_execution_repeated.output:
            return False
    return True


def reduce_test(cloned_repo_manager, pr, old_execution, new_execution):
    assert (old_execution.code == new_execution.code)
    assert (old_execution.output != new_execution.output)

    # create increasingly smaller variants of the test (by removing lines at the end)
    increasingly_smaller_tests = []
    lines = old_execution.code.split("\n")
    for line_nb in reversed(range(1, len(lines)+1)):  # last line to second line
        if lines[line_nb-1] == "" or lines[line_nb-1].startswith("#"):
            continue
        reduced_code = "\n".join(lines[:line_nb])
        increasingly_smaller_tests.append(reduced_code)

    # execute all variants
    old_executions = [TestExecution(t) for t in increasingly_smaller_tests]
    new_executions = [TestExecution(t) for t in increasingly_smaller_tests]
    execute_tests_on_commit(cloned_repo_manager, pr,
                            old_executions, pr.pre_commit)
    execute_tests_on_commit(cloned_repo_manager, pr,
                            new_executions, pr.post_commit)

    # find the last test that still shows a difference
    reduced_old_execution = old_execution
    reduced_new_execution = new_execution
    assert reduced_old_execution.output != reduced_new_execution.output
    for (reduced_old_execution_candidate, reduced_new_execution_candidate) in zip(old_executions, new_executions):
        if reduced_old_execution_candidate.output == reduced_new_execution_candidate.output:
            break
        reduced_old_execution = reduced_old_execution_candidate
        reduced_new_execution = reduced_new_execution_candidate
        assert reduced_old_execution.output != reduced_new_execution.output
        append_event(ComparisonEvent(pr_nb=pr.number,
                                     message="Different outputs (also after test reduction)",
                                     test_code=reduced_old_execution.code,
                                     old_output=reduced_old_execution.output,
                                     new_output=reduced_new_execution.output))

    return reduced_old_execution, reduced_new_execution


def check_if_present_in_main(cloned_repo_manager, pr, new_execution):
    main_execution = TestExecution(new_execution.code)
    execute_tests_on_commit(cloned_repo_manager, pr, [
                            main_execution], "main")
    return main_execution.output == new_execution.output


def classify_regression(project_name, pr, changed_functions, docstrings, old_execution, new_execution, no_cache=False, nb_samples=1):
    append_event(PreClassificationEvent(pr_nb=pr.number,
                                        message="Pre-classification",
                                        test_code=old_execution.code,
                                        old_output=old_execution.output,
                                        new_output=new_execution.output))

    prompt = RegressionClassificationPrompt(
        project_name, pr, changed_functions, docstrings, old_execution.code, old_execution.output, new_execution.output)
    raw_answer = llm.query(prompt,
                           temperature=Config.classification_temp,
                           no_cache=no_cache,
                           nb_samples=nb_samples)
    append_event(LLMEvent(pr_nb=pr.number,
                          message="Raw answer", content="\n---(next sample)---".join(raw_answer)))
    assert (nb_samples == len(raw_answer))

    all_results = []
    for raw_answer_sample in raw_answer:
        is_relevant_change, is_deterministic, is_public, is_legal, is_surprising, correct_output = prompt.parse_answer(
            [raw_answer_sample])
        append_event(ClassificationEvent(pr_nb=pr.number,
                                         message="Classification",
                                         is_relevant_change=is_relevant_change,
                                         is_deterministic=is_deterministic,
                                         is_public=is_public,
                                         is_legal=is_legal,
                                         is_surprising=is_surprising,
                                         correct_output=correct_output,
                                         old_is_crash=is_crash(
                                             old_execution.output),
                                         new_is_crash=is_crash(new_execution.output)))
        result = is_relevant_change and is_deterministic and is_public and is_legal and is_surprising
        all_results.append(result)
    if nb_samples == 1:
        return all_results[0]
    return all_results


def select_expected_behavior(project_name, pr, old_execution, new_execution, docstrings):
    """Ask LLM which of two possible outputs is the expected behavior."""
    prompt = SelectExpectedBehaviorPrompt(
        project_name, old_execution.code, old_execution.output, new_execution.output, docstrings)
    raw_answer = llm.query(prompt, temperature=Config.classification_temp)
    append_event(LLMEvent(pr_nb=pr.number,
                          message="Raw answer", content="\n---(next sample)---".join(raw_answer)))
    expected_behavior = prompt.parse_answer(raw_answer)
    append_event(SelectBehaviorEvent(pr_nb=pr.number,
                                     message="Selected expected behavior",
                                     expected_output=expected_behavior))
    return expected_behavior


def check_pr(github_repo, cloned_repo_manager, pr):
    # ignore if too few or too many files changed
    # nb_modified_code_files = len(pr.non_test_modified_python_files)
    nb_modified_code_files = len(pr.non_test_modified_code_files)
    if nb_modified_code_files == 0:
        append_event(Event(
            pr_nb=pr.github_pr.number, message="Ignoring because no non-test code files were modified"))
        return
    if nb_modified_code_files > 3:
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because too many non-test code files were modified"))
        return

    # ignore if PR has more than one parent
    if Config.single_parent_PRs_only and len(pr.parents) != 1:
        append_event(
            Event(pr_nb=pr.number, message=f"Ignoring because PR has != 1 parent"))
        return

    # ignore if only comment changes
    if not pr.has_non_comment_change():
        append_event(
            Event(pr_nb=pr.number, message="Ignoring because only comments changed"))
        return

    # ignore if labeled as documentation-only change
    if pr.title.startswith("DOC"):
        append_event(
            Event(pr_nb=pr.number, message="Ignoring because labeled as 'DOC'"))
        return

    # extract diff and names of changed functions
    changed_functions = pr.get_changed_function_names()

    # generate tests via LLM
    generated_tests = generate_tests(pr, github_repo, changed_functions)
    if not generated_tests:
        append_event(Event(pr_nb=pr.number,
                           message="Ignoring because no tests were generated"))
        return

    if cloned_repo_manager.repo_name == "pandas":
        # make sure the tests import pandas
        updated_tests = []
        for test in generated_tests:
            if "import pandas" not in test:
                updated_tests.append("import pandas as pd\n" + test)
            else:
                updated_tests.append(test)
        generated_tests = updated_tests

    # ask LLM to fix undefined references in tests
    if Config.fix_undefined_refs:
        fixed_tests = []
        for test in generated_tests:
            undefined_refs = get_undefined_references(test)
            if undefined_refs:
                prompt = UndefinedRefsFixingPrompt(test, undefined_refs)
                raw_answer = llm.query(prompt)[0]
                append_event(LLMEvent(pr_nb=pr.number,
                                      message="Raw answer", content=raw_answer))
                fixed_test = prompt.parse_answer(raw_answer)
                append_event(LLMEvent(pr_nb=pr.number,
                                      message="Fixed undefined references", content=fixed_test))
                fixed_tests.append(fixed_test)
            else:
                fixed_tests.append(test)
        generated_tests = fixed_tests

    # execute tests
    old_executions = [TestExecution(t) for t in generated_tests]
    new_executions = [TestExecution(t) for t in generated_tests]

    execute_tests_on_commit(cloned_repo_manager, pr,
                            old_executions, pr.pre_commit)
    execute_tests_on_commit(cloned_repo_manager, pr,
                            new_executions, pr.post_commit)

    assert None not in [e.output for e in old_executions]

    # analyze coverage during test execution
    for (old_execution, new_execution) in zip(old_executions, new_executions):
        assert old_execution.coverage_report is not None
        assert new_execution.coverage_report is not None

        diff_coverage_old = summarize_coverage(
            pr, old_execution, is_old_version=True)
        diff_coverage_new = summarize_coverage(
            pr, new_execution, is_old_version=False)

        details = f"Old: {diff_coverage_old}, New: {diff_coverage_new}"
        append_event(CoverageEvent(pr_nb=pr.number,
                                   message="Diff coverage",
                                   details=details))

    # analyze behavior of executions
    for (old_execution, new_execution) in zip(old_executions, new_executions):
        assert old_execution.output is not None
        assert new_execution.output is not None

        # check for behavioral differences
        difference_found = old_execution.output != new_execution.output
        if is_crash(old_execution.output) and is_crash(new_execution.output):
            # ignore differences if both tests crash
            append_event(ComparisonEvent(pr_nb=pr.number,
                                         message=f"Both tests failed, considering them the same",
                                         test_code=old_execution.code, old_output=old_execution.output,
                                         new_output=new_execution.output))
            continue
        if difference_found:
            # double-check differences by re-executing the tests
            difference_found_again = validate_output_difference(cloned_repo_manager,
                                                                pr, old_execution, new_execution)
            if not difference_found_again:
                difference_found = False

        if not difference_found:
            append_event(ComparisonEvent(pr_nb=pr.number,
                                         message=f"Same output",
                                         test_code=old_execution.code, old_output=old_execution.output,
                                         new_output=new_execution.output))
            continue

        append_event(ComparisonEvent(pr_nb=pr.number,
                                     message=f"Different outputs",
                                     test_code=old_execution.code, old_output=old_execution.output,
                                     new_output=new_execution.output))

        # if difference found, reduce the test while still observing a difference
        old_execution, new_execution = reduce_test(cloned_repo_manager,
                                                   pr, old_execution, new_execution)
        assert old_execution.output != new_execution.output

        # check if new output is still present in head of current main branch
        if not check_if_present_in_main(cloned_repo_manager, pr, new_execution):
            append_event(Event(pr_nb=pr.number,
                               message="Difference not present in main anymore"))

        # find docstrings
        cloned_repo_of_new_commit = cloned_repo_manager.get_cloned_repo(
            pr.post_commit)
        docstrings = retrieve_relevant_docstrings(
            cloned_repo_of_new_commit, new_execution.code)

        # if difference found, classify regression
        assert old_execution.code == new_execution.code
        is_regression_bug = classify_regression(
            github_repo.name, pr, changed_functions, docstrings, old_execution, new_execution)

        # if classified as regression bug, ask LLM which behavior is expected (to handle coincidental bug fixes)
        if is_regression_bug:
            select_expected_behavior(
                github_repo.name, pr, old_execution, new_execution, docstrings)


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

    logs = glob.glob('logs_*.json') + glob.glob('done_prs*.json')
    for log in logs:
        with open(log, "r") as f:
            entries = json.load(f)
        for entry in entries:
            if entry["message"] == "Done with PR":
                done_prs.add(entry["pr_nb"])

    return done_prs


def filter_and_sort_prs_by_risk(github_prs, cloned_repo_manager):
    # split into chunks of 20
    chunks = [github_prs[i:i + 20] for i in range(0, len(github_prs), 20)]

    # ask LLM to rank PRs by risk of introducing a regression bug
    all_high_risk_prs = []
    all_medium_risk_prs = []
    for chunk in chunks:
        prompt = PRRegressionBugRanking(chunk, cloned_repo_manager.repo_name)
        raw_answer = llm.query(prompt)
        append_event(LLMEvent(pr_nb=0,
                              message="Raw answer", content="\n---(next sample)---".join(raw_answer)))
        ranking_result = prompt.parse_answer(raw_answer)
        if ranking_result is None:
            append_event(Event(pr_nb=0,
                               message="Failed to parse ranking result; keeping them all"))
            all_medium_risk_prs.extend(chunk)
        else:
            high_risk_prs, medium_risk, _ = ranking_result
            all_high_risk_prs.extend(high_risk_prs)
            all_medium_risk_prs.extend(medium_risk)

    result = all_high_risk_prs + all_medium_risk_prs
    append_event(Event(
        pr_nb=0, message=f"Keeping {len(result)} high/medium-risk PRs out of {len(github_prs)} total PRs"))
    return result


def get_repo(project_name):
    if project_name == "pandas":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "pandas", "pandas-dev/pandas", "pandas-dev", "pandas")
    elif project_name == "scikit-learn":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "scikit-learn", "scikit-learn/scikit-learn", "scikit-learn-dev", "sklearn")
    elif project_name == "scipy":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "scipy", "scipy/scipy", "scipy-dev", "scipy")
    elif project_name == "numpy":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "numpy", "numpy/numpy", "numpy-dev", "numpy")
    elif project_name == "transformers":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "transformers", "huggingface/transformers", "transformers-dev", "transformers")
    elif project_name == "keras":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "keras", "keras-team/keras", "keras-dev", "keras")
    elif project_name == "marshmallow":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "marshmallow", "marshmallow-code/marshmallow", "marshmallow-dev", "marshmallow")
    elif project_name == "pytorch_geometric":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "pytorch_geometric", "pyg-team/pytorch_geometric", "pytorch_geometric-dev", "torch_geometric")
    elif project_name == "scapy":
        cloned_repo_manager = ClonedRepoManager(
            "../clones", "scapy", "secdev/scapy", "scapy-dev", "scapy")

    cloned_repo = cloned_repo_manager.get_cloned_repo("main")
    cloned_repo.repo.git.pull()
    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))
    github_repo = github.get_repo(cloned_repo_manager.repo_id)

    return github_repo, cloned_repo_manager


def main():
    start_logging()
    project, pr_nb = EvalTaskManager.fetch_task()
    while project and pr_nb:
        github_repo, cloned_repo_manager = get_repo(project)
        github_pr = github_repo.get_pull(pr_nb)
        pr = PullRequest(github_pr, github_repo, cloned_repo_manager)

        # check the PR
        append_event(PREvent(pr_nb=pr_nb,
                             message="Starting to check PR",
                             title=pr.github_pr.title, url=pr.github_pr.html_url))
        try:
            check_pr(github_repo, cloned_repo_manager, pr)
        except BugGPTException as e:
            append_event(ErrorEvent(
                pr_nb=pr_nb, message="Caught BugGPTError; will continue with next PR", details=str(e)))
            continue
        append_event(PREvent(pr_nb=pr_nb,
                             message="Done with PR",
                             title=pr.github_pr.title, url=pr.github_pr.html_url))

        # store log on disk and into DB
        store_logs()
        log = get_logs_as_json()
        EvalTaskManager.write_results(project, pr_nb, log)
        reset_logs()

        project, pr_nb = EvalTaskManager.fetch_task()

    print("No more tasks to work on")


if __name__ == "__main__":
    main()
