from os.path import join
from unidiff import PatchSet

from buggpt.util.BugsInPy import bugs_in_py_dir, all_bugs_file, get_code_and_patch_range
from buggpt.util.FunctionFilter import remove_based_on_undefined_references, remove_because_not_self_explanatory
from buggpt.util.PythonCodeUtil import extract_target_function

with open(all_bugs_file, 'r') as f:
    bug_info_files = [line.strip() for line in f.readlines()]

print(f"Checking {len(bug_info_files)} bugs")

candidates = ["Project,Id,Comment"]
for idx, bug_info_file in enumerate(bug_info_files):
    _, project, _, id, _ = bug_info_file.split("/")

    print(f"====== Checking: {project} {id} ({idx+1} / {len(bug_info_files)}) ======")

    # filter based on nb of files and hunks
    patch_file = join(bugs_in_py_dir, "projects", project,
                      "bugs", id, "bug_patch.txt")
    patch = PatchSet.from_filename(patch_file)
    if len(patch.modified_files) != 1:
        print(
            f"Ignoring {project} {id} because it has {len(patch.modified_files)} modified files")
        continue
    modified_file = patch.modified_files[0]
    if len(modified_file) != 1:
        print(
            f"Ignoring {project} {id} because it has {len(modified_file)} hunks")
        continue

    # check if we can extract a single function under test
    code, patch_range = get_code_and_patch_range(project, id)
    fut_code = extract_target_function(code, patch_range)
    if fut_code is None:
        print(
            f"Ignoring {project} {id} because the target function could not be extracted")
        continue

    nb_fut_lines = fut_code.count("\n") + 1
    if nb_fut_lines > 80:
        print(
            f"Ignoring {project} {id} because the target function has {nb_fut_lines} lines")
        continue

    if remove_based_on_undefined_references(fut_code):
        print(
            f"Ignoring {project} {id} because it has too many undefined references")
        continue

    if remove_because_not_self_explanatory(fut_code):
        print(
            f"Ignoring {project} {id} because it is not self-explanatory")
        continue

    print(f"=> Candidate function {project} {id}")
    print(fut_code)
    print()
    candidates.append(f"{project},{id},")

with open("bugsInPy_candidates.csv", "w") as f:
    f.write("\n".join(candidates))
    print("Wrote candidates to bugsInPy_candidates.csv")