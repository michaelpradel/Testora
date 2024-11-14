# Helper script to find PRs that are in-scope for checking (i.e., that are not discarded because of changing only test files, having to many changes, etc.)

from buggpt.evaluation.ResultsManager import result_files_for_project
from buggpt.util.LogParser import parse_log_files
from buggpt.evaluation.TargetPRs import project_to_target_prs

for project in ["keras", "marshmallow", "scipy", "pandas"]:
    print(f"Project {project}:")
    pr_results, _ = parse_log_files(result_files_for_project(project))
    in_scope_pr_nbs = []
    for pr_result in pr_results:
        if pr_result.status() != "ignored":
            in_scope_pr_nbs.append(pr_result.number)
    print(",\n".join([str(n) for n in sorted(in_scope_pr_nbs)]))
    print(f"--> {len(in_scope_pr_nbs)} PRs in-scope\n")
    print()


print("\n\n===========================\n\n")

# print new results as csv
minimum_timestamp = "2024-11-14 09:50:00"
print("Project, PR, Generated tests, Executed tests, Failures, Differences")
for project, target_prs in project_to_target_prs().items():
    pr_results, _ = parse_log_files(
        result_files_for_project(project, minimum_timestamp))
    for target_pr in target_prs:
        pr_result = next(
            (r for r in pr_results if r.number == target_pr), None)
        if pr_result is None:
            entries = [
                project,
                str(target_pr)
            ]
        else:
            entries = [
                project,
                str(target_pr),
                str(pr_result.nb_generated_tests),
                str(pr_result.nb_test_executions),
                str(pr_result.nb_test_failures),
                str(pr_result.nb_different_behavior)
            ]
        print(", ".join(entries))
