import json
import os


base_dir = "data/target_prs/"


def project_to_target_prs():
    project_to_prs = {}
    for project_file in os.listdir(base_dir):
        if project_file.endswith(".json"):
            project_name = project_file.replace(".json", "")
            with open(os.path.join(base_dir, project_file), "r") as f:
                project_to_prs[project_name] = json.load(f)

    return project_to_prs
