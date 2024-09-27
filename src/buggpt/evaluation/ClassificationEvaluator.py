import argparse

from buggpt.util.LogParser import parse_log_files, PRResult, pr_results_as_dict


def extract_case(log_file: str) -> PRResult:
    # find PR number
    pr_number = None
    for segment in log_file.split("_"):
        if segment.startswith("pr"):
            pr_number = int(segment[2:].replace(".json", ""))
            break
    if pr_number is None:
        raise ValueError(f"Could not find PR number in file name {log_file}")

    # read logs
    pr_to_info, _ = parse_log_files(log_files=[log_file])
    pr_number_to_result = pr_results_as_dict(pr_to_info)
    return pr_number_to_result[pr_number]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--tp_logs", nargs="+", required=True)
    parser.add_argument("--fp_logs", nargs="+", required=True)
    args = parser.parse_args()

    tp_cases = [extract_case(log_file) for log_file in args.tp_logs]
    fp_cases = [extract_case(log_file) for log_file in args.fp_logs]

    print(f"Parsed {len(tp_cases)} TP cases and {len(fp_cases)} FP cases.")
    print("TP cases:")
    for case in tp_cases:
        print(f"{case}\n")
    print("FP cases:")
    for case in fp_cases:
        print(f"{case}\n")
