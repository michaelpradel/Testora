from typing import List
from github import Github, Auth
from testora.RegressionFinder import get_merged_prs
from testora.evaluation import EvalTaskManager


def write_specific_PR_tasks_into_database(project_name, project_id, pr_numbers: List[int]):
    pr_numbers_to_analyze = pr_numbers
    EvalTaskManager.write_tasks(project_name, pr_numbers_to_analyze, "tasks")


def write_range_of_PR_tasks_into_database(project_name, project_id, start_pr_nb, total):
    print(f"Searching PRs for {project_name}")

    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))
    github_repo = github.get_repo(project_id)

    merged_prs = get_merged_prs(github_repo, max_prs=1)
    most_recent_pr_nb = merged_prs[0].number

    print(f"Most recent PR number: {most_recent_pr_nb}")
    result_pr_nbs = []
    next_candidate_pr_nb = start_pr_nb
    while next_candidate_pr_nb <= most_recent_pr_nb and len(result_pr_nbs) < total:
        # check if nb is a PR
        try:
            pr = github_repo.get_pull(next_candidate_pr_nb)
        except Exception:
            # not a valid PR number
            print(f"Skipping number {next_candidate_pr_nb}(not a valid PR number)")
            next_candidate_pr_nb += 1
            continue

        # check if PR is closed
        if not pr.is_merged():
            print(f"Skipping number {next_candidate_pr_nb} (PR not merged)")
            next_candidate_pr_nb += 1
            continue

        # found a valid PR number -- add to list
        print(f"Adding PR number {next_candidate_pr_nb} into the list")
        result_pr_nbs.append(next_candidate_pr_nb)
        next_candidate_pr_nb += 1

    EvalTaskManager.write_tasks(project_name, result_pr_nbs, "tasks")


if __name__ == "__main__":
    EvalTaskManager.initialize()

    # write_range_of_PR_tasks_into_database(
    #     "pandas", "pandas-dev/pandas", 60322, 300)

    # write_range_of_PR_tasks_into_database(
    #     "scipy", "scipy/scipy", 22031, 300)

    # write_range_of_PR_tasks_into_database(
    #     "keras", "keras-team/keras", 20711, 300)

    # write_range_of_PR_tasks_into_database(
    #     "marshmallow", "marshmallow-code/marshmallow", 2804, 300)

    # write_specific_PR_tasks_into_database("scipy", "scipy/scipy",
    #                                       [23609, 23607, 23606, 23574, 23521, 23520, 23511, 23502, 23501, 23498, 23497, 23494, 23483, 23475, 23471, 23454, 23442, 23426, 23415, 23388, 23350, 23348, 23341, 23322, 23311, 23298, 23294, 23293, 23280, 23276, 23266, 23235, 23194, 23138, 23121, 23103, 23091, 23071, 23059, 23055, 23048, 23047, 23044, 23019, 23005, 22989, 22982, 22971, 22944, 22941, 22913, 22910, 22899, 22869, 22864, 22855, 22801, 22772, 22763, 22760, 22725, 22718, 22689, 22660, 22651, 22632, 22624, 22611, 22610, 22600, 22585, 22582, 22532, 22494, 22482, 22481, 22475, 22462, 22455, 22447, 22433, 22421, 22398, 22372, 22353, 22344, 22313, 22284, 22283, 22278, 22273, 22251, 22242, 22226, 22221, 22220, 22219, 22215, 22213, 22199])

    # write_specific_PR_tasks_into_database("pandas", "pandas-dev/pandas",
    #                                       [62349, 62325, 62320, 62300, 62298, 62289, 62281, 62280, 62276, 62248, 62246, 62166, 62116, 62101, 62085, 62076, 62073, 62038, 62032, 62025, 61990, 61972, 61969, 61966, 61947, 61946, 61924, 61894, 61891, 61884, 61874, 61855, 61827, 61800, 61786, 61773, 61771, 61743, 61699, 61697, 61658, 61646, 61633, 61625, 61623, 61597, 61541, 61517, 61514, 61508, 61484, 61472, 61467, 61451, 61422, 61399, 61376, 61352, 61340, 61332, 61320, 61293, 61286, 61234, 61229, 61225, 61207, 61198, 61193, 61183, 61162, 61131, 61114, 61105, 61103, 61054, 61046, 61041, 61017, 61008, 60987, 60985, 60983, 60975, 60974, 60963, 60952, 60949, 60936, 60924, 60916, 60906, 60894, 60882, 60867, 60860, 60828, 60826, 60795, 60793])

    # write_specific_PR_tasks_into_database("keras", "keras-team/keras",
    #                                       [21682, 21680, 21650, 21646, 21611, 21603, 21595, 21590, 21588, 21569, 21535, 21534, 21532, 21512, 21496, 21495, 21480, 21473, 21456, 21449, 21440, 21434, 21432, 21428, 21423, 21414, 21412, 21407, 21406, 21399, 21393, 21392, 21373, 21361, 21349, 21336, 21335, 21331, 21317, 21304, 21302, 21291, 21290, 21277, 21256, 21239, 21211, 21192, 21184, 21170, 21163, 21148, 21138, 21129, 21117, 21101, 21095, 21081, 21077, 21066, 21053, 21030, 21014, 21010, 20993, 20989, 20974, 20973, 20956, 20954, 20928, 20926, 20916, 20913, 20909, 20905, 20892, 20879, 20854, 20853, 20829, 20824, 20815, 20791, 20784, 20782, 20777, 20768, 20765, 20758, 20755, 20736, 20689, 20643, 20637, 20630, 20626, 20613, 20612, 20602])

    # write_specific_PR_tasks_into_database("marshmallow", "marshmallow-code/marshmallow",
    #                                       [2803, 2800, 2798, 2797, 2770, 2769, 2764, 2762, 2756, 2755, 2754, 2742, 2741, 2731, 2712, 2706, 2701, 2700, 2699, 2698, 2271, 2264, 2246, 2244, 2215, 2164, 2153, 2081, 2071, 1882, 1868, 1785, 1745, 1702, 1682, 1627, 1574, 1551, 1524, 1501, 1500, 1480, 1448, 1446, 1444, 1443, 1416, 1405, 1401, 1399, 1395, 1392, 1376, 1359, 1354, 1344, 1343, 1340, 1331, 1307, 1306, 1293, 1288, 1276, 1252, 1246, 1209, 1189, 1136, 1087, 1079, 1078, 1063, 1049, 1036, 1010, 1008, 983, 982, 963, 960, 959, 954, 950, 931, 911, 903, 865, 857, 856, 826, 822, 816, 808, 769, 750, 744, 725, 714, 707])
