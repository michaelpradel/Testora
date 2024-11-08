import os
from datetime import datetime


base_dir = "data/results/"


def result_files():
    for project_dir in os.listdir(base_dir):
        for pr_result_file in os.listdir(os.path.join(base_dir, project_dir)):
            if pr_result_file.endswith(".json"):
                yield os.path.join(base_dir, project_dir, pr_result_file)


def result_files_for_project(project_name):
    for pr_result_file in os.listdir(os.path.join(base_dir, project_name)):
        if pr_result_file.endswith(".json"):
            yield os.path.join(base_dir, project_name, pr_result_file)


def current_results():
    project_to_prs_and_timestamps = {}
    for project_dir in os.listdir(base_dir):
        project_to_prs_and_timestamps[project_dir] = []
        for pr_result_file in os.listdir(os.path.join(base_dir, project_dir)):
            if pr_result_file.endswith(".json"):
                pr_nb, timestamp = pr_result_file.replace(
                    ".json", "").split("_")
                project_to_prs_and_timestamps[project_dir].append(
                    [pr_nb, timestamp])
    return project_to_prs_and_timestamps


def add_result(project_name, pr_nb, timestamp, result):
    old_results = current_results()

    # Write new result to file
    if not os.path.exists(os.path.join(base_dir, project_name)):
        os.makedirs(os.path.join(base_dir, project_name))

    target_file = os.path.join(base_dir, project_name,
                               f"{pr_nb}_{timestamp}.json")
    with open(target_file, "w") as f:
        f.write(result)

    # Check if it replaces an old result (if yes, move old result to archive)
    for old_pr_nb, old_timestamp in old_results[project_name]:
        if old_pr_nb == pr_nb:
            old_target_file = os.path.join(base_dir, project_name,
                                           f"{old_pr_nb}_{old_timestamp}.json")
            archive_dir = os.path.join(base_dir, project_name, "archive")
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            os.rename(old_target_file, os.path.join(
                archive_dir, f"{old_pr_nb}_{old_timestamp}.json"))
            print(f"Moved old result to {archive_dir}")
            break

    print(f"New result in {target_file}")
