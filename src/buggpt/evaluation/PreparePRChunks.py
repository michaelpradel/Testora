import json
from github import Github, Auth

from buggpt.RegressionFinder import get_recent_prs
from buggpt.execution import PythonProjects
from buggpt.evaluation import EvalTaskManager


def write_PR_chunks_into_database():
    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))
    project = PythonProjects.pandas_project
    github_repo = github.get_repo(project.project_id)
    github_prs = get_recent_prs(github_repo, nb=1000)
    recent_pr_nbs = [pr.number for pr in github_prs]

    chunk_size = 50
    chunks = [recent_pr_nbs[i:i + chunk_size]
              for i in range(0, len(recent_pr_nbs), chunk_size)]

    name_to_task = {}
    for chunk in chunks:
        task_name = f"{chunk[0]}_{chunk[-1]}"
        task = json.dumps(chunk)
        name_to_task[task_name] = task

    EvalTaskManager.write_tasks(name_to_task)


if __name__ == "__main__":
    write_PR_chunks_into_database()
