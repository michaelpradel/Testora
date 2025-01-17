from github import Github, Auth, GithubException
from buggpt.RegressionFinder import get_recent_prs
from buggpt.evaluation import EvalTaskManager


def write_recent_PR_tasks_into_database(project_name, project_id):
    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))
    github_repo = github.get_repo(project_id)
    github_prs = get_recent_prs(github_repo, nb=100)
    recent_pr_nbs = [pr.number for pr in github_prs]
    pr_numbers_to_analyze = [n for n in recent_pr_nbs if n > 59907]
    EvalTaskManager.write_tasks(project_name, pr_numbers_to_analyze, "tasks")


def write_specific_PR_tasks_into_database(project_name, project_id, pr_numbers):
    pr_numbers_to_analyze = pr_numbers
    EvalTaskManager.write_tasks(project_name, pr_numbers_to_analyze, "tasks")


def write_range_of_PR_tasks_into_database(project_name, project_id, start_pr_nb, total):
    print(f"Searching PRs for {project_name}")

    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))
    github_repo = github.get_repo(project_id)

    most_recent_pr_nb = get_recent_prs(github_repo, nb=1)[0].number

    print(f"Most recent PR number: {most_recent_pr_nb}")
    result_pr_nbs = []
    next_candidate_pr_nb = start_pr_nb
    while next_candidate_pr_nb <= most_recent_pr_nb and len(result_pr_nbs) < total:
        try:
            github_repo.get_pull(next_candidate_pr_nb)
        except Exception:
            # not a valid PR number
            print(f"Skipping number {next_candidate_pr_nb} (not a valid PR number)")
            next_candidate_pr_nb += 1
            continue

        # found a valid PR number -- add to list
        print(f"Adding PR number {next_candidate_pr_nb} into the list")
        result_pr_nbs.append(next_candidate_pr_nb)
        next_candidate_pr_nb += 1

    EvalTaskManager.write_tasks(project_name, result_pr_nbs, "tasks")


if __name__ == "__main__":
    # write_recent_PR_tasks_into_database("pandas", "pandas-dev/pandas")
    # write_PR_tasks_into_database("pandas", "pandas-dev/pandas",
    #                              [57399, 57595, 56841,
    #                               58376, 55108, 57205,
    #                               57046, 57034])  # known true positives
    write_range_of_PR_tasks_into_database(
        "pandas", "pandas-dev/pandas", 59908, 100)

    # write_recent_PR_tasks_into_database("scipy", "scipy/scipy")
    # write_PR_tasks_into_database("scipy", "scipy/scipy",
    #                              [20089, 20974, 21036,
    #                               20751, 21076, 19776,
    #                               19861, 19853, 19680,
    #                               19428, 19263, 21553])  # known true positives
    write_range_of_PR_tasks_into_database("scipy", "scipy/scipy", 21652, 100)

    # write_recent_PR_tasks_into_database("keras", "keras-team/keras")
    # write_PR_tasks_into_database("keras", "keras-team/keras",
    #                              [19814])  # known true positives
    write_range_of_PR_tasks_into_database("keras", "keras-team/keras", 20264, 100)

    # write_recent_PR_tasks_into_database("marshmallow", "marshmallow-code/marshmallow")
    # write_PR_tasks_into_database("marshmallow", "marshmallow-code/marshmallow",
    #                              [1399, 2215])  # known true positives
    write_range_of_PR_tasks_into_database("marshmallow", "marshmallow-code/marshmallow", 2277, 100)
