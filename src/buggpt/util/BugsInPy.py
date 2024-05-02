from genericpath import exists
from os import makedirs, getcwd
from os.path import join
import subprocess
from unidiff import PatchSet

from buggpt.util.PythonCodeUtil import extract_target_function_by_range


all_bugs_file = join(getcwd(), "data/bugsInPy_bugs_shuffled_March_14_2024.csv")
bugs_in_py_dir = "/home/m/research/collabs/BugsInPy"
repo_cache_base_dir = join(getcwd(), "data/bugsinpy_cache/")


def get_project_root_dir(project, id, version: str):
    """
    Values for "version": "b" for buggy, "f" for fixed, and "o" for original (= buggy without the fix-time test)
    """

    project_root_dir = f"{repo_cache_base_dir}/{project}/{id}{version}"

    if exists(project_root_dir):
        return join(project_root_dir, project)

    makedirs(project_root_dir)

    # checkout buggy or fixed version
    if version == "b":
        cmd = f"bugsinpy-checkout -p {project} -i {id} -v 0 -w {project_root_dir}"
    elif version == "f":
        cmd = f"bugsinpy-checkout -p {project} -i {id} -v 1 -w {project_root_dir}"
    elif version == "o":
        cmd = f"bugsinpy-checkout-with-old-test -p {project} -i {id} -v 0 -w {project_root_dir}"

    result = subprocess.run(
        cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(result.stdout)
        raise RuntimeError(
            f"Failed to checkout version of {project} {id}")

    return join(project_root_dir, project)


def get_code_and_patch_range(project, id):
    project_root_dir = get_project_root_dir(project, id, "b")
    patch_file = join(bugs_in_py_dir, "projects", project,
                      "bugs", str(id), "bug_patch.txt")

    patch = PatchSet.from_filename(patch_file)
    assert len(
        patch.modified_files) == 1, f"Expected 1 modified file, got {len(patch.modified_files)}"
    modified_file = patch.modified_files[0]
    assert len(
        modified_file) == 1, f"Expected 1 hunk, got {len(modified_file)}"
    hunk = modified_file[0]
    # TODO extract exactly the changed lines, not the entire hunk
    start_line = hunk.target_start
    end_line = hunk.target_start + hunk.target_length

    with open(join(project_root_dir, modified_file.path), "rb") as f:
        code = f.read()

    return code, (start_line, end_line)


def get_property_from_info_file(file_path, property_name):
    with open(file_path, 'r') as f:
        bug_info_lines = f.readlines()

    target_line = [
        l for l in bug_info_lines if property_name in l][0]
    _, _, val = target_line.partition("=")
    val = val.strip()
    val = val.replace("\"", "")
    return val


def get_property_from_bug_info_file(project, id, property_name):
    bug_info_file = join(bugs_in_py_dir, "projects",
                         project, "bugs", id, "bug.info")
    return get_property_from_info_file(bug_info_file, property_name)


def get_property_from_project_info_file(project, id, property_name):
    project_info_file = join(
        bugs_in_py_dir, "projects", project, "project.info")
    return get_property_from_info_file(project_info_file, property_name)


def get_test_code(project, id):
    project_root_dir = get_project_root_dir(project, id, "o")
    relative_test_file = get_property_from_bug_info_file(
        project, id, "test_file")
    test_file = join(project_root_dir, relative_test_file)
    with open(test_file, "r") as f:
        return f.read()


def get_commit_url(project, id):
    commit_id = get_property_from_bug_info_file(project, id, "fixed_commit_id")
    project_url = get_property_from_project_info_file(
        project, id, "github_url")

    return f"{project_url}/commit/{commit_id}"
