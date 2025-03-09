from os.path import join
from unidiff import PatchSet

from testora.util.BugsInPy import bugs_in_py_dir, all_bugs_file, get_commit_url

with open(all_bugs_file, 'r') as f:
    bug_info_files = [line.strip() for line in f.readlines()]
    # format: projects/luigi/bugs/3/bug.info


for bug_info_file in bug_info_files:
    _, project, _, id, _ = bug_info_file.split("/")

    # filter based on nb of hunks
    patch_file = join(bugs_in_py_dir, "projects", project,
                      "bugs", id, "bug_patch.txt")
    patch = PatchSet.from_filename(patch_file)
    if len(patch.modified_files) != 1:
        print(
            f"(Ignoring {project} {id} because it has {len(patch.modified_files)} modified files)")
        continue
    modified_file = patch.modified_files[0]
    if len(modified_file) != 1:
        print(
            f"(Ignoring {project} {id} because it has {len(modified_file)} hunks)")
        continue

    # print commit URL
    print(f"{project}-{id}: {get_commit_url(bug_info_file)}")

    # Status: Inspected all until keras-27 (inclusive)
