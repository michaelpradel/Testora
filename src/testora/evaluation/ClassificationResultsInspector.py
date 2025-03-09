import json
from testora.evaluation.ResultsManager import result_files_for_project


project = "scipy"
pr = 21553
test_case_to_skip = 0

file = list(result_files_for_project(project, is_classification=True))[0]
fp = open(file, "r")
result_json = json.load(fp)
config = result_json[0]["message"]
print("CONFIG:")
print(config)
for entry_idx, entry in enumerate(result_json):
    if entry["pr_nb"] == pr and entry["message"] == "Pre-classification":
        test_case_to_skip -= 1
        if test_case_to_skip != -1:
            continue

        print("\nTEST CODE:")
        print(entry["test_code"])
        print("\nOLD OUTPUT:")
        print(entry["old_output"])
        print("\nNEW OUTPUT:")
        print(entry["new_output"])

        print("\nQUERY:")
        print(result_json[entry_idx+1]["content"])

        print("\nANSWER:")
        print(result_json[entry_idx+3]["content"])
