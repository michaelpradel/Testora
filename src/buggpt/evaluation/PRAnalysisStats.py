from collections import Counter
import glob
from os.path import join
from buggpt.util.LogParser import PRResult, parse_log_files, parse_time_stamp, pr_results_as_dict

# PR ranges used for RQ2 (test generation) and RQ4 (costs)
project_to_pr_range = {
    "keras": [20264, 20856],
    "marshmallow": [2277, 2809],
    "pandas": [59908, 60843],
    "scipy": [21652, 22457],
}

base_dir = "data/results"


def parse_pr_results(project, pr_range):
    # list all .json files in base_dir/project
    path = join(base_dir, project, "*.json")
    json_files = glob.glob(path)

    # filter files that are in the PR range
    filtered_files = []
    for json_file in json_files:
        pr_number = int(json_file.split('/')[-1].split('_')[0])
        if pr_range[0] <= pr_number <= pr_range[1]:
            filtered_files.append(json_file)

    # parse the log files
    pr_results, _ = parse_log_files(filtered_files)

    return pr_results


def compute_general_stats(pr_results):
    print(f"Total PRs: {len(pr_results)}")
    ignored_prs = [r for r in pr_results if r.ignored]
    print(f"Ignored PRs: {len(ignored_prs)}")
    reasons_ignored = Counter(r.ignored_reason for r in ignored_prs)
    print(f"Reasons for Ignored PRs: {reasons_ignored}")
    checked_prs = [r for r in pr_results if not r.ignored]
    print(f"Checked PRs: {len(checked_prs)}")
    pr_with_different_behavior = [
        r for r in checked_prs if r.nb_different_behavior > 0]
    print(f"PRs with different behavior: {len(pr_with_different_behavior)}")

    return f"{len(pr_results)} & {len(ignored_prs)} & {len(checked_prs)} & {len(pr_with_different_behavior)}"


def compute_test_generation_stats(pr_results):
    checked_prs = [r for r in pr_results if not r.ignored]

    nbs_generated_tests = [r.nb_generated_tests for r in checked_prs]
    gen_tests_out = f"{min(nbs_generated_tests)} & / & {round(sum(nbs_generated_tests) /
                                                        len(nbs_generated_tests))} & / & {max(nbs_generated_tests)}"
    print(
        f"Generated tests: (min & avg & max) {gen_tests_out}")

    nbs_test_executions = [r.nb_test_executions for r in checked_prs]
    total_execs_out = f"{min(nbs_test_executions)} & / & {round(sum(nbs_test_executions)/len(nbs_test_executions))} & / & {max(nbs_test_executions)}"
    print(
        f"Test executions: (min & avg & max) {total_execs_out}")

    nbs_test_non_failures = [r.nb_test_executions -
                             r.nb_test_failures for r in checked_prs]
    non_failures_out = f"{min(nbs_test_non_failures)} & / & {round(sum(nbs_test_non_failures)/len(nbs_test_non_failures))} & / & {max(nbs_test_non_failures)}"
    print(
        f"Test non-failures: (min & avg & max) {non_failures_out}")

    nbs_diff_covered_tests = [r.nb_diff_covered_tests for r in checked_prs]
    diff_covered_out = f"{min(nbs_diff_covered_tests)} & / & {round(sum(nbs_diff_covered_tests)/len(nbs_diff_covered_tests))} & / & {max(nbs_diff_covered_tests)}"
    print(
        f"Tests with diff-coverage: (min & avg & max) {diff_covered_out}")

    avg_old_diff_coverages = [r.avg_old_diff_coverage for r in checked_prs]
    print(
        f"Avg old diff-coverage: (min & avg & max) {min(avg_old_diff_coverages)} & / & {round(sum(avg_old_diff_coverages)/len(avg_old_diff_coverages), 2)} & / & {max(avg_old_diff_coverages)}")

    avg_new_diff_coverages = [r.avg_new_diff_coverage for r in checked_prs]
    print(
        f"Avg new diff-coverage: (min & avg & max) {min(avg_new_diff_coverages)} & / & {round(sum(avg_new_diff_coverages)/len(avg_new_diff_coverages), 2)} & / & {max(avg_new_diff_coverages)}")

    return f"{gen_tests_out} & {diff_covered_out} & {total_execs_out} & {non_failures_out}"


def compute_cost_stats(pr_results):
    checked_prs = [r for r in pr_results if not r.ignored]

    input_tokens = [r.input_tokens for r in checked_prs]
    print(
        f"Avg input tokens for checked PRs: {round(sum(input_tokens)/len(input_tokens))}")


if __name__ == "__main__":
    general_table_rows = []
    test_generation_table_rows = []

    for project, pr_range in project_to_pr_range.items():
        print(f"\n-------------- {project} -------------")
        pr_results = parse_pr_results(project, pr_range)

        row = compute_general_stats(pr_results)
        general_table_rows.append(f"{project} & {row} \\\\")

        row = compute_test_generation_stats(pr_results)
        test_generation_table_rows.append(f"{project} & {row} \\\\")

        compute_cost_stats(pr_results)

    print("\n\n")
    print("Table w/ general stats:\n")
    print("\n".join(general_table_rows))

    print("\n\n")
    print("Table w/ test generation stats:\n")
    print("\n".join(test_generation_table_rows))
