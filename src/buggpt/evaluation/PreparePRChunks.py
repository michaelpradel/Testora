from github import Github, Auth

from buggpt.RegressionFinder import get_recent_prs
from buggpt.evaluation import EvalTaskManager


def write_PR_tasks_into_database(project_name, project_id):
    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))

    github_repo = github.get_repo(project_id)
    github_prs = get_recent_prs(github_repo, nb=75)
    recent_pr_nbs = [pr.number for pr in github_prs]

    recent_pr_nbs = [n for n in recent_pr_nbs if n < 59926]

    EvalTaskManager.write_tasks(project_name, recent_pr_nbs)


if __name__ == "__main__":
    write_PR_tasks_into_database("pandas", "pandas-dev/pandas")
    # write_PR_tasks_into_database("scipy", "scipy/scipy")
    # write_PR_tasks_into_database("keras", "keras-team/keras")
    # write_PR_tasks_into_database("marshmallow", "marshmallow-code/marshmallow")

    # write_PR_tasks_into_database("scikit-learn", "scikit-learn/scikit-learn")
    # write_PR_tasks_into_database("numpy", "numpy/numpy")
    # write_PR_tasks_into_database("transformers", "huggingface/transformers")
    # write_PR_tasks_into_database("pytorch_geometric", "pyg-team/pytorch_geometric")
    # write_PR_tasks_into_database("scapy", "secdev/scapy")
