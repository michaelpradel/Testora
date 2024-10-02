import os
from datetime import datetime


base_dir = "data/results/"


def current_results():
    project_to_prs_and_timestamps = {}
    for project_dir in os.listdir(base_dir):
        if project_dir == "old_results":
            continue
        project_to_prs_and_timestamps[project_dir] = []
        for pr_result_file in os.listdir(os.path.join(base_dir, project_dir)):
            pr_nb, timestamp = pr_result_file.replace(".json", "").split("_")
            project_to_prs_and_timestamps[project_dir].append(
                [pr_nb, timestamp])
    return project_to_prs_and_timestamps


def add_result(project_name, pr_nb, timestamp, result):
    if not os.path.exists(os.path.join(base_dir, project_name)):
        os.makedirs(os.path.join(base_dir, project_name))

    with open(os.path.join(base_dir, project_name, f"{pr_nb}_{timestamp}.json"), "w") as f:
        f.write(result)
