from genericpath import exists
from os import makedirs, getcwd
from os.path import join
import subprocess
from unidiff import PatchSet

from buggpt.util.PythonExtractor import extract_target_function


all_bugs_file = join(getcwd(), "data/bugsInPy_bugs_shuffled_March_14_2024.csv")
bugs_in_py_dir = "/home/m/research/collabs/BugsInPy"
repo_cache_base_dir = join(getcwd(), "data/bugsinpy_cache/")


def get_project_root_dir(project, id):
    project_root_dir = f"{repo_cache_base_dir}/{project}/{id}b"
    if exists(project_root_dir):
        return join(project_root_dir, project)

    makedirs(project_root_dir)

    # checkout buggy or fixed version
    cmd = f"bugsinpy-checkout -p {project} -i {id} -v 0 -w {project_root_dir}"

    result = subprocess.run(
        cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(result.stdout)
        raise RuntimeError(
            f"Failed to checkout version of {project} {id}")

    return join(project_root_dir, project)


def get_code_to_check(project, id):
    project_root_dir = get_project_root_dir(project, id)
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

    function_code = extract_target_function(code, (start_line, end_line))
    return function_code
