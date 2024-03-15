from os.path import join
from unidiff import PatchSet

all_bugs_file = "data/bugsInPy_bugs_shuffled_March_14_2024.csv"
bugs_dir = "/home/m/research/collabs/BugsInPy"

with open(all_bugs_file, 'r') as f:
    bug_info_files = [line.strip() for line in f.readlines()]
    # format: projects/luigi/bugs/3/bug.info

for bug_info_file in bug_info_files:
    _, project, _, id, _ = bug_info_file.split("/")
    
    # filter based on nb of hunks
    patch_file = join(bugs_dir, "projects", project, "bugs", id, "bug_patch.txt")
    patch = PatchSet.from_filename(patch_file)
    if len(patch.modified_files) != 1:
        print(f"(Ignoring {project} {id} because it has {len(patch.modified_files)} modified files)")
        continue
    modified_file = patch.modified_files[0]
    if len(modified_file) != 1:
        print(f"(Ignoring {project} {id} because it has {len(modified_file)} hunks)")
        continue

    # print commit URL
    with open(join(bugs_dir, bug_info_file), 'r') as f:
        bug_info_lines = f.readlines()
    
    fixed_commit_id_line = [l for l in bug_info_lines if "fixed_commit_id" in l][0]
    _, _, commit_id = fixed_commit_id_line.partition("=")
    commit_id = commit_id.strip()
    commit_id = commit_id.replace("\"", "")

    with open(join(bugs_dir, "projects", project, "project.info"), 'r') as f:
        project_info_lines = f.readlines()
    project_url_line = [l for l in project_info_lines if "github_url" in l][0]
    _, _, project_url = project_url_line.partition("=")
    project_url = project_url.strip()
    project_url = project_url.replace("\"", "")
        
    print(f"{project}-{id}: {project_url}/commit/{commit_id}")

    # Status: Inspected all until keras-27 (inclusive)