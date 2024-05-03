from unidiff import PatchSet
import urllib.request
from github import Github, Auth
from git import Repo
import ast
from buggpt.execution.DockerExecutor import DockerExecutor
from buggpt.execution.TestExecution import TestExecution
from buggpt.llms.LLMCache import LLMCache
from buggpt.prompts.RegressionClassificationPrompt import RegressionClassificationPrompt
from buggpt.prompts.RegressionTestGeneratorPrompt import RegressionTestGeneratorPrompt
from buggpt.util.PythonCodeUtil import extract_target_function_by_name, extract_target_function_by_range, get_name_of_defined_function
from buggpt.execution import PythonProjects
import buggpt.llms.OpenAIGPT as uncached_llm
from buggpt.util.Logs import append_event, Event, ComparisonEvent, LLMEvent
llm = LLMCache(uncached_llm)


def pr_url_to_patch(pr_url):
    diff_url = pr_url + ".diff"
    diff = urllib.request.urlopen(diff_url)
    encoding = diff.headers.get_charsets()[0]
    return PatchSet(diff, encoding=encoding)


def get_non_test_modified_files(patch):
    modified_python_files = [
        f for f in patch.modified_files if f.path.endswith(".py")]
    non_test_modified_python_files = [
        f for f in modified_python_files if "test" not in f.path]
    return non_test_modified_python_files


def pr_is_in_scope(pr):
    patch = pr_url_to_patch(pr.html_url)
    non_test_modified_python_files = get_non_test_modified_files(patch)
    if len(non_test_modified_python_files) < 1:
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because no non-test Python files were modified"))
        return False
    if len(non_test_modified_python_files) > 1:
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because too many non-test Python files were modified"))
        return False
    return True


def find_fut(pr, github_repo):
    patch = pr_url_to_patch(pr.html_url)
    non_test_modified_python_files = get_non_test_modified_files(patch)
    hunks = []
    for modified_file in non_test_modified_python_files:
        hunks.extend(modified_file)
    if len(hunks) > 1:
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because couldn't find function to test (too many hunks)"))
        return False

    hunk = hunks[0]
    # TODO extract exactly the changed lines, not the entire hunk
    start_line = hunk.target_start
    end_line = hunk.target_start + hunk.target_length
    patch_range = (start_line, end_line)

    gh_files = pr.get_files()
    modified_gh_file = [
        f for f in gh_files if f.filename == modified_file.path][0]

    most_recent_commit = pr.get_commits().reversed[0]
    file_contents = github_repo.get_contents(
        modified_gh_file.filename, ref=most_recent_commit.sha)
    code = file_contents.decoded_content.decode("utf-8")

    fct_code = extract_target_function_by_range(code, patch_range)
    if fct_code is None:
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because too many functions got changed in PR"))
        return False
    fct_name = get_name_of_defined_function(fct_code)

    module_name = modified_gh_file.filename.replace(
        "/", ".").replace(".py", "")

    return f"{module_name}.{fct_name}", modified_gh_file.filename


def extract_fut_code(cloned_repo, commit, file_path, qualified_function_name):
    cloned_repo.git.checkout(commit)
    with open(f"{cloned_repo.working_dir}/{file_path}", "r") as f:
        code = f.read()
    function_code = extract_target_function_by_name(
        code, qualified_function_name.split(".")[-1])
    return function_code


def execute_tests_on_commit(test_executions, commit):
    docker_executor = DockerExecutor("pandas-dev")

    cloned_repo.git.checkout(commit)
    # to trigger pandas re-compilation
    docker_executor.execute_python_code("import pandas")

    for test_execution in test_executions:
        output = docker_executor.execute_python_code(test_execution.code)
        test_execution.output = output


def get_ast_without_docstrings(code):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        # Remove docstrings
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            node.body = [n for n in node.body if not (
                isinstance(n, ast.Expr) and isinstance(n.value, ast.Str))]
    return tree


def equal_modulo_docstrings(code1, code2):
    ast1 = get_ast_without_docstrings(code1)
    ast2 = get_ast_without_docstrings(code2)
    return ast.dump(ast1) == ast.dump(ast2)


def check_pr(pr, github_repo, cloned_repo):
    # check if pull request is in scope for testing
    if not pr_is_in_scope(pr):
        return

    # identify changed code
    found_fut = find_fut(pr, github_repo)
    if not found_fut:
        return
    qualified_function_name, file_path = found_fut
    append_event(Event(pr_nb=pr.number,
                 message=f"Found function to test: {qualified_function_name}"))

    # get old and new versions of the fut
    post_commit = pr.merge_commit_sha
    parents = github_repo.get_commit(post_commit).parents
    if len(parents) != 1:
        append_event(
            Event(pr_nb=pr.number, message=f"Ignoring because PR has != 1 parent"))
        return
    pre_commit = parents[0].sha

    old_fut_code = extract_fut_code(
        cloned_repo, pre_commit, file_path, qualified_function_name)
    new_fut_code = extract_fut_code(
        cloned_repo, post_commit, file_path, qualified_function_name)
    if old_fut_code is None or new_fut_code is None:
        append_event(
            Event(pr_nb=pr.number, message=f"Ignoring because couldn't find old or new function code"))
        return

    # ignore if only difference is in comments
    if equal_modulo_docstrings(old_fut_code, new_fut_code):
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because old and new functions are the same modulo comments"))
        return

    # generate tests via LLM
    prompt = RegressionTestGeneratorPrompt(
        github_repo.name, qualified_function_name, old_fut_code, new_fut_code)
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

    execute_tests_on_commit(old_executions, pre_commit)
    execute_tests_on_commit(new_executions, post_commit)

    for (old_execution, new_execution) in zip(old_executions, new_executions):
        difference_found = old_execution.output != new_execution.output
        append_event(ComparisonEvent(pr_nb=pr.number,
                                     message=f"{'Different' if difference_found else 'Same'} outputs",
                                     old_function_code=old_execution.code, old_output=old_execution.output,
                                     new_function_code=new_execution.code, new_output=new_execution))

        # if difference found, classify regression
        if difference_found:
            prompt = RegressionClassificationPrompt(
                github_repo.name, pr, qualified_function_name, test, old_execution.output, new_execution.output)
            raw_answer = llm.query(prompt)
            append_event(LLMEvent(pr_nb=pr.number,
                                  message="Raw answer", content=raw_answer))
            classification = prompt.parse_answer(raw_answer)
            append_event(Event(pr_nb=pr.number,
                               message=f"Classification: {classification}"))


def get_recent_prs(github_repo, nb=50):
    all_prs = github_repo.get_pulls(state="closed")
    merged_prs = []
    for pr in all_prs:
        if pr.is_merged():
            merged_prs.append(pr)
        if len(merged_prs) >= nb:
            break
    return merged_prs


# setup for testing on pandas
cloned_repo = Repo("./data/repos/pandas")
cloned_repo.git.checkout("main")
cloned_repo.git.pull()
token = open(".github_token", "r").read().strip()
github = Github(auth=Auth.Token(token))
project = PythonProjects.pandas_project
github_repo = github.get_repo(project.project_id)

# testing with motivating example
pr = github_repo.get_pull(55108)
check_pr(pr, github_repo, cloned_repo)

# testing on recent PRs
# prs = get_recent_prs(github_repo, nb=100)
# for pr in prs[30:]:
#     check_pr(pr, github_repo, cloned_repo)


# cloned_repo = ClonedRepo("./data/repos/pandas")
# # cloned_repo.checkout("79067a76adc448d17210f2cf4a858b0eb853be4c")  # just before the bug
# cloned_repo.checkout("0bdbc44babac09225bdde02b642252ce054723e3")  # introduces the bug

# docker_executor = DockerExecutor("pandas-dev")

# test_code = """
# import pandas as pd

# i = pd.Index(['a', 'b', 'c', None], dtype='category')
# i.difference(['1', None])
# """

# res = docker_executor.execute_python_test(test_code, is_test=False)
# print(res)

# token = open(".github_token", "r").read().strip()
# github = Github(auth=Auth.Token(token))

# github_repo = github.get_repo(project.project_id)
# prs = get_recent_prs(github_repo)
# for pr in prs:
#     check_pr(pr, github_repo)


# testing for PR detail extractor
# prs = get_recent_prs(github_repo, nb=30)
# for pr in prs:
#     details = RegressionClassificationPrompt(
#         "pandas", pr, "", "", "", "").extract_pr_details()
#     print("======================")
#     print(f"PR {pr.number}: {pr.title}\n")
#     print(details)
