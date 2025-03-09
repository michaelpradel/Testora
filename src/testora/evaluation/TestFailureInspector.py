# Helper script to inspect logs of test failures and identify the root cause of the failure

from collections import Counter
from testora.evaluation.ResultsManager import result_files
from testora.util.LogParser import parse_log_files

pr_results, _ = parse_log_files(result_files())

error_ctr = Counter()

for pr_result in pr_results:
    if pr_result.nb_test_failures > 0:
        for entry in pr_result.entries:
            if entry["message"] == "Test execution" and "Traceback (most recent call last)" in entry["output"]:
                # print(entry["output"])
                last_line = entry["output"].split("\n")[-2:-1][0]
                # print(last_line)
                # print("--------------------------------------------\n")
                if "Error" in last_line:
                    error_type = last_line.split(":")[0]
                    error_ctr[error_type] += 1

                if "NameError" in last_line:
                    # print(last_line)
                    print(entry["code"])
                    print(">>>")
                    print(entry["output"])
                    print("--------------------------------------------\n")


print("\n\n\n")

for error_type, count in error_ctr.most_common():
    print(f"{error_type}: {count}")

                
