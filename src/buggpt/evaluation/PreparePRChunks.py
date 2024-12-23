from github import Github, Auth

from buggpt.RegressionFinder import get_recent_prs
from buggpt.evaluation import EvalTaskManager


def write_PR_tasks_into_database(project_name, project_id, pr_numbers=None):
    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))

    github_repo = github.get_repo(project_id)
    if pr_numbers is None:
        github_prs = get_recent_prs(github_repo, nb=280)
        recent_pr_nbs = [pr.number for pr in github_prs]
        pr_numbers_to_analyze = [n for n in recent_pr_nbs if n < 59760]
    else:
        pr_numbers_to_analyze = pr_numbers

    EvalTaskManager.write_tasks(project_name, pr_numbers_to_analyze, "tasks")


if __name__ == "__main__":
    # write_PR_tasks_into_database("pandas", "pandas-dev/pandas")
    # write_PR_tasks_into_database("pandas", "pandas-dev/pandas",
    #                              [57399, 57595, 56841,
    #                               58376, 55108, 57205,
    #                               57046, 57034])  # known true positives

    # write_PR_tasks_into_database("scipy", "scipy/scipy")
    # write_PR_tasks_into_database("scipy", "scipy/scipy",
    #                              [20089, 20974, 21036,
    #                               20751, 21076, 19776,
    #                               19861, 19853, 19680,
    #                               19428, 19263, 21553])  # known true positives

    # write_PR_tasks_into_database("keras", "keras-team/keras")
    # write_PR_tasks_into_database("keras", "keras-team/keras",
    #                              [19814])  # known true positives

    # write_PR_tasks_into_database("marshmallow", "marshmallow-code/marshmallow")
    # write_PR_tasks_into_database("marshmallow", "marshmallow-code/marshmallow",
    #                              [1399, 2215])  # known true positives
