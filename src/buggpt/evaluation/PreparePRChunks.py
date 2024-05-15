import os
from github import Github, Auth

from buggpt.RegressionFinder import get_recent_prs
from buggpt.execution import PythonProjects


if __name__ == "__main__":
    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))
    project = PythonProjects.pandas_project
    github_repo = github.get_repo(project.project_id)
    github_prs = get_recent_prs(github_repo, nb=1000)
    recent_pr_nbs = [pr.number for pr in github_prs]
    
    chunk_size = 50
    chunks = [recent_pr_nbs[i:i + chunk_size]
              for i in range(0, len(recent_pr_nbs), chunk_size)]
    
    out_dir = "./data/pr_chunks/"
    os.makedirs(out_dir, exist_ok=True)
    
    for chunk in chunks:
        file_path = f"{out_dir}/{project.name}_pr_chunk_{chunk[0]}_{chunk[-1]}.json"
        with open(file_path, "w") as f:
            f.write(str(chunk))
