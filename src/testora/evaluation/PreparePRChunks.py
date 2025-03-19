from github import Github, Auth
from testora.RegressionFinder import get_merged_prs
from testora.evaluation import EvalTaskManager


def write_specific_PR_tasks_into_database(project_name, project_id, pr_numbers):
    pr_numbers_to_analyze = pr_numbers
    EvalTaskManager.write_tasks(project_name, pr_numbers_to_analyze, "tasks")


def write_range_of_PR_tasks_into_database(project_name, project_id, start_pr_nb, total):
    print(f"Searching PRs for {project_name}")

    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))
    github_repo = github.get_repo(project_id)

    merged_prs = get_merged_prs(github_repo, max_prs=1)
    most_recent_pr_nb = merged_prs[0].number

    print(f"Most recent PR number: {most_recent_pr_nb}")
    result_pr_nbs = []
    next_candidate_pr_nb = start_pr_nb
    while next_candidate_pr_nb <= most_recent_pr_nb and len(result_pr_nbs) < total:
        # check if nb is a PR
        try:
            pr = github_repo.get_pull(next_candidate_pr_nb)
        except Exception:
            # not a valid PR number
            print(f"Skipping number {
                  next_candidate_pr_nb} (not a valid PR number)")
            next_candidate_pr_nb += 1
            continue
        
        # check if PR is closed
        if not pr.is_merged():
            print(f"Skipping number {next_candidate_pr_nb} (PR not merged)")
            next_candidate_pr_nb += 1
            continue
        
        # found a valid PR number -- add to list
        print(f"Adding PR number {next_candidate_pr_nb} into the list")
        result_pr_nbs.append(next_candidate_pr_nb)
        next_candidate_pr_nb += 1

    EvalTaskManager.write_tasks(project_name, result_pr_nbs, "tasks")


if __name__ == "__main__":
    write_range_of_PR_tasks_into_database(
        "pandas", "pandas-dev/pandas", 60322, 300)

    write_range_of_PR_tasks_into_database(
        "scipy", "scipy/scipy", 22031, 300)

    write_range_of_PR_tasks_into_database(
        "keras", "keras-team/keras", 20711, 300)

    write_range_of_PR_tasks_into_database(
        "marshmallow", "marshmallow-code/marshmallow", 2804, 300)
