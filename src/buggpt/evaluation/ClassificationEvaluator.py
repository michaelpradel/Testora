import argparse

from buggpt.util.LogParser import parse_log_files, PRResult


def create_ground_truth_template(log_file):
    pr_results, _ = parse_log_files([log_file])
    pr_result = pr_results[0]

    if pr_result.nb_different_behavior == 0:
        print("No differentiating test case found in log file")
        return
    
    # CONT: use pr_result.differentiating_tests (to be filled by improved logging)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--create_ground_truth_template', type=str,
                        help='Create a ground truth template from the given log file')
    args = parser.parse_args()

    if args.create_ground_truth_template:
        create_ground_truth_template(args.create_ground_truth_template)
