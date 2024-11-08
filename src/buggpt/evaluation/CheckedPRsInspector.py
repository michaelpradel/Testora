## Helper script to find PRs that are in-scope for checking (i.e., that are not discarded because of changing only test files, having to many changes, etc.)

from buggpt.evaluation.ResultsManager import result_files_for_project
from buggpt.util.LogParser import parse_log_files

for project in ["keras", "marshmallow", "scipy", "pandas"]:
    print(f"Project {project}:")
    pr_results, _ = parse_log_files(result_files_for_project(project))
    nb = 0
    for pr_result in pr_results:
        if pr_result.status() == "checked":
            print(f"  {pr_result.number}")
            nb += 1
    print(f"--> {nb} PRs in-scope\n")
    print()
