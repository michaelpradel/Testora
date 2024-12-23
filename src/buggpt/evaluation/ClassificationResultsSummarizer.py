import json
from buggpt.evaluation.ResultsManager import result_files_for_project


print("Project, PR, Prediction, Label, Result")
for project in ["keras", "marshmallow", "scipy", "pandas"]:
    for result_file in result_files_for_project(project, is_classification=True):
        with open(result_file, "r") as f:
            result_json = json.load(f)
            for entry in result_json:
                if entry["message"] == "Classification result":
                    # compare label and prediction
                    result = ""
                    if entry["label"] in ["unintended", "coincidental fix"]:
                        if entry["prediction"] == "unintended":
                            result = "TP"
                        elif entry["prediction"] == "intended":
                            result = "FN"
                        else:
                            raise ValueError(f"Invalid prediction: {
                                             entry['prediction']}")
                    elif entry["label"] == "intended":
                        if entry["prediction"] == "intended":
                            result = "TN"
                        elif entry["prediction"] == "unintended":
                            result = "FP"
                        else:
                            raise ValueError(f"Invalid prediction: {
                                             entry['prediction']}")
                    else:
                        raise ValueError(f"Invalid label: {entry['label']}, {entry["pr_nb"]}")

                    # print into CSV
                    print(f"{project}, "
                          f"{entry['pr_nb']}, "
                          f"{entry['prediction']}, "
                          f"{entry['label']}, "
                          f"{result}"
                          )
