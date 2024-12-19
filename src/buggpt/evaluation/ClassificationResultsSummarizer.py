import json
from buggpt.evaluation.ResultsManager import result_files_for_project


print("Project, PR, Prediction, Label")
for project in ["keras", "marshmallow", "scipy", "pandas"]:
    for result_file in result_files_for_project(project, is_classification=True):
        with open(result_file, "r") as f:
            result_json = json.load(f)
            for entry in result_json:
                if entry["message"] == "Classification result":
                    print(f"{project}, "
                          f"{entry['pr_nb']}, "
                          f"{entry['prediction']}, "
                          f"{entry['label']}")
