from unidiff import PatchSet
import urllib.request
from github import Github, Auth
from buggpt.execution.DockerExecutor import DockerExecutor
from buggpt.execution.RepoManager import ClonedRepo
from buggpt.util.PythonCodeUtil import extract_target_function, get_name_of_defined_function
from buggpt.execution import PythonProjects


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
        print(
            f"Ignoring PR {pr.html_url} because no non-test Python files were modified")
        return False
    if len(non_test_modified_python_files) > 1:
        print(
            f"Ignoring PR {pr.html_url} because too many files were modified")
        return False
    return True


def find_API_to_test(pr, github_repo):
    patch = pr_url_to_patch(pr.html_url)
    non_test_modified_python_files = get_non_test_modified_files(patch)
    hunks = []
    for modified_file in non_test_modified_python_files:
        hunks.extend(modified_file)
    if len(hunks) > 1:
        print(
            f"Couldn't find API to test in PR {pr.html_url} (too many hunks)")
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

    fct_code = extract_target_function(code, patch_range)
    if fct_code is None:
        print(f"No or too many functions got changed in PR {pr.html_url}")
        return False
    fct_name = get_name_of_defined_function(fct_code)

    module_name = modified_gh_file.filename.replace(
        "/", ".").replace(".py", "")

    return f"{module_name}.{fct_name}"


def check_pr(pr, github_repo):
    # check if pull request is in scope for testing
    if not pr_is_in_scope(pr):
        return

    print(f"PR in scope: {pr.html_url}")

    # identify changed code and how to access it via public APIs
    qualified_function_name = find_API_to_test(pr, github_repo)
    if qualified_function_name:
        print(f"Found function to test: {qualified_function_name}")


def get_recent_prs(github_repo):
    prs = github_repo.get_pulls(state="merged")
    pr_urls = []
    for pr in prs[:30]:
        pr_urls.append(pr)
    return pr_urls


# testing
# pr_url_1 = "https://github.com/pandas-dev/pandas/pull/58479"
# check_pr(pr_url_1)

# project = PythonProjects.pandas_project

cloned_repo = ClonedRepo("./data/repos/pandas")
cloned_repo.checkout("79067a76adc448d17210f2cf4a858b0eb853be4c")

docker_executor = DockerExecutor("pandas-dev")
# docker_executor.install_project_under_test(project)
# docker_executor.checkout_commit(project, "79067a76adc448d17210f2cf4a858b0eb853be4c")  # just before the bug
# docker_executor.checkout_commit(project, "0bdbc44babac09225bdde02b642252ce054723e3")  # introduces the bug

test_code = """
import pandas as pd

i = pd.Index(['a', 'b', 'c', None], dtype='category')
i.difference(['1', None])
"""

res = docker_executor.execute_python_test(test_code, is_test=False)
print(res)

# token = open(".github_token", "r").read().strip()
# github = Github(auth=Auth.Token(token))

# github_repo = github.get_repo(project.project_id)
# prs = get_recent_prs(github_repo)
# for pr in prs:
#     check_pr(pr, github_repo)
