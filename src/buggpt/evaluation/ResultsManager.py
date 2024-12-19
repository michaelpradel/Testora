import os
from datetime import datetime


results_base_dir = "data/results/"
classification_results_base_dir = "data/classification_results/"


def result_files():
    for project_dir in os.listdir(results_base_dir):
        for pr_result_file in os.listdir(os.path.join(results_base_dir, project_dir)):
            if pr_result_file.endswith(".json"):
                yield os.path.join(results_base_dir, project_dir, pr_result_file)


def result_files_for_project(project_name, minimum_timestamp=None, is_classification=False):
    base_dir = classification_results_base_dir if is_classification else results_base_dir
    for pr_result_file in os.listdir(os.path.join(base_dir, project_name)):
        if pr_result_file.endswith(".json"):
            if minimum_timestamp:
                pr_timestamp = pr_result_file.replace(
                    ".json", "").split("_")[1]
                if datetime.strptime(pr_timestamp, "%Y-%m-%d %H:%M:%S") < datetime.strptime(minimum_timestamp, "%Y-%m-%d %H:%M:%S"):
                    continue

            yield os.path.join(base_dir, project_name, pr_result_file)


def current_results(include_archive=True):
    project_to_prs_and_timestamps = {}
    for project_dir in os.listdir(results_base_dir):
        project_to_prs_and_timestamps[project_dir] = []
        result_dirs = [os.path.join(results_base_dir, project_dir)]
        if include_archive:
            result_dirs.append(os.path.join(
                results_base_dir, project_dir, "archive"))
        for result_dir in result_dirs:
            for pr_result_file in os.listdir(result_dir):
                if pr_result_file.endswith(".json"):
                    pr_nb, timestamp = pr_result_file.replace(
                        ".json", "").split("_")
                    project_to_prs_and_timestamps[project_dir].append(
                        [pr_nb, timestamp])
    return project_to_prs_and_timestamps


def add_result(project_name, pr_nb, timestamp, result, is_classification):
    base_dir = classification_results_base_dir if is_classification else base_dir

    all_old_results = current_results()
    non_archive_old_results = current_results(False)

    # check if result already exists
    for old_pr_nb, old_timestamp in all_old_results[project_name]:
        if old_pr_nb == pr_nb and old_timestamp == timestamp:
            return

    # Write new result to file
    if not os.path.exists(os.path.join(base_dir, project_name)):
        os.makedirs(os.path.join(base_dir, project_name))

    target_file = os.path.join(base_dir, project_name,
                               f"{pr_nb}_{timestamp}.json")
    with open(target_file, "w") as f:
        f.write(result)

    # Check if it replaces an old result (if yes, move old result to archive)
    for old_pr_nb, old_timestamp in non_archive_old_results[project_name]:
        if old_pr_nb == pr_nb:
            old_target_file = os.path.join(base_dir, project_name,
                                           f"{old_pr_nb}_{old_timestamp}.json")
            archive_dir = os.path.join(base_dir, project_name, "archive")
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            renamed_target_file = os.path.join(
                archive_dir, f"{old_pr_nb}_{old_timestamp}.json")
            os.rename(old_target_file, renamed_target_file)
            print(f"Moved old result to {renamed_target_file}")
            break

    print(f"New result in {target_file}")
