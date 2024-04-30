from unidiff import PatchSet
import urllib.request
from github import Github
from buggpt.util.PythonCodeUtil import extract_target_function, get_name_of_defined_function


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

    print(f"Changed function: {fct_name}")


def check_pr(pr, github_repo):
    # check if pull request is in scope for testing
    if not pr_is_in_scope(pr):
        return

    print(f"PR in scope: {pr.html_url}")

    # identify changed code and how to access it via public APIs
    find_API_to_test(pr, github_repo)


def get_recent_prs(github_repo):
    prs = github_repo.get_pulls(state="merged")
    pr_urls = []
    for pr in prs[:10]:
        pr_urls.append(pr)
    return pr_urls


# testing
# pr_url_1 = "https://github.com/pandas-dev/pandas/pull/58479"
# check_pr(pr_url_1)
project_id = "pandas-dev/pandas"
github = Github()
github_repo = github.get_repo(project_id)
prs = get_recent_prs(github_repo)
for pr in prs:
    check_pr(pr, github_repo)
