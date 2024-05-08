import glob
import json
import re
from github import Github, Auth
from git import Repo
from buggpt.execution.DockerExecutor import DockerExecutor
from buggpt.execution.TestExecution import TestExecution
from buggpt.llms.LLMCache import LLMCache
from buggpt.prompts.PRRegressionBugRanking import PRRegressionBugRanking
from buggpt.prompts.RegressionClassificationPrompt import RegressionClassificationPrompt
from buggpt.prompts.RegressionTestGeneratorPrompt import RegressionTestGeneratorPrompt
from buggpt.util.PullRequest import PullRequest
from buggpt.execution import PythonProjects
from buggpt.llms.OpenAIGPT import OpenAIGPT, gpt4_model, gpt35_model
from buggpt.util.Logs import ClassificationEvent, PREvent, TestExecutionEvent, append_event, Event, ComparisonEvent, LLMEvent
from buggpt.util.PythonCodeUtil import has_private_calls_or_fails_to_parse


gpt4 = LLMCache(OpenAIGPT(gpt4_model))
gpt35 = LLMCache(OpenAIGPT(gpt35_model))


def clean_output(output):
    # pandas-specific cleaning (to remove build output)
    result = []
    for line in output.split("\n"):
        if line == "+ /usr/local/bin/ninja":
            continue
        # check if line starts with "[1/1]", "[2/4]", etc.
        if len(line) >= 6 and line.startswith("[") and \
                line[1].isdigit() and \
                line[2] == "/" and \
                line[3].isdigit() and \
                line[4] == "]" and \
                line[5] == " ":
            continue
        result.append(line)
    return "\n".join(result)


def execute_tests_on_commit(pr_number, test_executions, commit):
    docker_executor = DockerExecutor("pandas-dev")

    append_event(
        Event(pr_nb=pr_number, message=f"Compiling pandas at commit {commit}"))

    cloned_repo.git.checkout(commit)
    # to trigger pandas re-compilation
    docker_executor.execute_python_code("import pandas")

    append_event(
        Event(pr_nb=pr_number, message=f"Done with compiling pandas at commit {commit}"))

    for test_execution in test_executions:
        stdout_output, stderr_output = docker_executor.execute_python_code(
            test_execution.code)
        output = stdout_output + "\n" + stderr_output
        test_execution.output = clean_output(output)
        append_event(TestExecutionEvent(pr_nb=pr_number,
                                        message="Test execution",
                                        code=test_execution.code,
                                        output=output))


def is_crash(output):
    return "Traceback (most recent call last)" in output


def generate_tests_with_prompt(prompt, model):
    raw_answer = model.query(prompt)
    append_event(LLMEvent(pr_nb=pr.number,
                 message="Raw answer", content=raw_answer))
    generated_tests = prompt.parse_answer(raw_answer)
    for idx, test in enumerate(generated_tests):
        append_event(LLMEvent(pr_nb=pr.number,
                     message=f"Generated test {idx+1}", content=test))
    return generated_tests


def remove_tests_with_private_call(tests):
    result = []
    for test in tests:
        if not has_private_calls_or_fails_to_parse(test):
            result.append(test)
    return result


def generate_tests(pr, github_repo, changed_functions):
    # prepare context used by one or more prompts
    full_diff = pr.get_full_diff()
    filtered_diff = pr.get_filtered_diff()

    all_tests = []

    if len(full_diff.split("\n")) <= 200:
        # full diff with GPT4
        prompt_full_diff = RegressionTestGeneratorPrompt(
            github_repo.name, changed_functions, full_diff)
        all_tests.extend(generate_tests_with_prompt(prompt_full_diff, gpt4))

        # full diff with GPT3.5
        all_tests.extend(generate_tests_with_prompt(prompt_full_diff, gpt35))

    if len(filtered_diff.split("\n")) <= 200 and filtered_diff != full_diff:
        # filtered diff with GPT4
        prompt_filtered_diff = RegressionTestGeneratorPrompt(
            github_repo.name, changed_functions, filtered_diff)
        all_tests.extend(generate_tests_with_prompt(
            prompt_filtered_diff, gpt4))

        # filtered diff with GPT3.5
        all_tests.extend(generate_tests_with_prompt(
            prompt_filtered_diff, gpt35))

    # de-dup tests
    nb_tests_before_dedup_and_cleaning = len(all_tests)
    all_tests = list(set(all_tests))

    # clean tests
    all_tests = remove_tests_with_private_call(all_tests)

    append_event(Event(pr_nb=pr.number,
                 message=f"Generated {len(all_tests)} tests ({nb_tests_before_dedup_and_cleaning} before deduplication and cleaning)"))
    return all_tests


def validate_output_difference(pr, old_execution, new_execution):
    # re-execute test on old and new version and ignore flaky differences
    old_execution_repeated = TestExecution(old_execution.code)
    execute_tests_on_commit(
        pr.number, [old_execution_repeated], pr.pre_commit)
    new_execution_repeated = TestExecution(new_execution.code)
    execute_tests_on_commit(
        pr.number, [new_execution_repeated], pr.post_commit)
    return old_execution.output == old_execution_repeated.output and new_execution.output == new_execution_repeated.output and old_execution.output != new_execution.output


def reduce_test(pr, old_execution, new_execution):
    assert (old_execution.code == new_execution.code)
    assert (old_execution.output != new_execution.output)

    # create increasingly smaller variants of the test (by removing lines at the end)
    increasingly_smaller_tests = []
    lines = old_execution.code.split("\n")
    for line_nb in reversed(range(1, len(lines)+1)):  # last line to second line
        if lines[line_nb-1] == "" or lines[line_nb-1].startswith("#"):
            continue
        reduced_code = "\n".join(lines[:line_nb])
        increasingly_smaller_tests.append(reduced_code)

    # execute all variants
    old_executions = [TestExecution(t) for t in increasingly_smaller_tests]
    new_executions = [TestExecution(t) for t in increasingly_smaller_tests]
    execute_tests_on_commit(pr.number, old_executions, pr.pre_commit)
    execute_tests_on_commit(pr.number, new_executions, pr.post_commit)

    # find the last test that still shows a difference
    reduced_old_execution = old_execution
    reduced_new_execution = new_execution
    assert reduced_old_execution.output != reduced_new_execution.output
    for (reduced_old_execution_candidate, reduced_new_execution_candidate) in zip(old_executions, new_executions):
        if reduced_old_execution_candidate.output == reduced_new_execution_candidate.output:
            break
        reduced_old_execution = reduced_old_execution_candidate
        reduced_new_execution = reduced_new_execution_candidate
        assert reduced_old_execution.output != reduced_new_execution.output
        append_event(ComparisonEvent(pr_nb=pr.number,
                                     message="Different outputs (also after test reduction)",
                                     test_code=reduced_old_execution.code,
                                     old_output=reduced_old_execution.output,
                                     new_output=reduced_new_execution.output))

    return reduced_old_execution, reduced_new_execution


def check_pr(pr):
    # ignore if too few or too many files changed
    if len(pr.non_test_modified_python_files) == 0:
        append_event(Event(
            pr_nb=pr.github_pr.number, message="Ignoring because no non-test Python files were modified"))
        return
    if len(pr.non_test_modified_python_files) > 3:
        append_event(Event(
            pr_nb=pr.number, message="Ignoring because too many non-test Python files were modified"))
        return

    # ignore if PR has more than one parent
    if len(pr.parents) != 1:
        append_event(
            Event(pr_nb=pr.number, message=f"Ignoring because PR has != 1 parent"))
        return

    # ignore if only comment changes
    if not pr.has_non_comment_change():
        append_event(
            Event(pr_nb=pr.number, message="Ignoring because only comments changed"))
        return

    # extract diff and names of changed functions
    changed_functions = pr.get_changed_function_names()

    # generate tests via LLM
    generated_tests = generate_tests(pr, github_repo, changed_functions)
    if not generated_tests:
        append_event(Event(pr_nb=pr.number,
                           message="Ignoring because no tests were generated"))
        return

    # make sure the tests import pandas
    updated_tests = []
    for test in generated_tests:
        if "import pandas" not in test:
            updated_tests.append("import pandas as pd\n" + test)
        else:
            updated_tests.append(test)
    generated_tests = updated_tests

    # execute tests
    old_executions = [TestExecution(t) for t in generated_tests]
    new_executions = [TestExecution(t) for t in generated_tests]

    execute_tests_on_commit(pr.number, old_executions, pr.pre_commit)
    execute_tests_on_commit(pr.number, new_executions, pr.post_commit)

    for (old_execution, new_execution) in zip(old_executions, new_executions):
        # check and validate that outputs are different
        difference_found = old_execution.output != new_execution.output
        if difference_found:
            difference_found_again = validate_output_difference(
                pr, old_execution, new_execution)
            if not difference_found_again:
                difference_found = False
        append_event(ComparisonEvent(pr_nb=pr.number,
                                     message=f"{'Different' if difference_found else 'Same'} outputs",
                                     test_code=old_execution.code, old_output=old_execution.output,
                                     new_output=new_execution.output))

        if not difference_found:
            continue

        # if difference found, reduce the test while still observing a difference
        old_execution, new_execution = reduce_test(
            pr, old_execution, new_execution)
        assert old_execution.output != new_execution.output

        # if difference found, classify regression
        assert old_execution.code == new_execution.code
        prompt = RegressionClassificationPrompt(
            github_repo.name, pr, changed_functions, old_execution.code, old_execution.output, new_execution.output)
        raw_answer = gpt4.query(prompt)
        append_event(LLMEvent(pr_nb=pr.number,
                              message="Raw answer", content=raw_answer))
        is_relevant_change, is_deterministic, is_regression_bug = prompt.parse_answer(
            raw_answer)
        append_event(ClassificationEvent(pr_nb=pr.number,
                                         message="Classification",
                                         is_relevant_change=is_relevant_change,
                                         is_deterministic=is_deterministic,
                                         is_regression_bug=is_regression_bug,
                                         old_is_crash=is_crash(
                                             old_execution.output),
                                         new_is_crash=is_crash(new_execution.output)))


def get_recent_prs(github_repo, nb=50):
    all_prs = github_repo.get_pulls(state="closed")
    merged_prs = []
    for github_pr in all_prs:
        if github_pr.is_merged():
            merged_prs.append(github_pr)
        if len(merged_prs) >= nb:
            break
    return merged_prs


def find_prs_checked_in_past():
    done_prs = set()

    logs = glob.glob('logs_*.json')
    for log in logs:
        with open(log, "r") as f:
            entries = json.load(f)
        for entry in entries:
            if entry["message"] == "Done with PR":
                done_prs.add(entry["pr_nb"])

    return done_prs


def filter_and_sort_prs_by_risk(github_prs):
    # split into chunks of 20
    chunks = [github_prs[i:i + 20] for i in range(0, len(github_prs), 20)]

    # ask LLM to rank PRs by risk of introducing a regression bug
    all_high_risk_prs = []
    all_medium_risk_prs = []
    for chunk in chunks:
        prompt = PRRegressionBugRanking(chunk)
        raw_answer = gpt4.query(prompt)
        append_event(LLMEvent(pr_nb=0,
                              message="Raw answer", content=raw_answer))
        ranking_result = prompt.parse_answer(raw_answer)
        if ranking_result is None:
            append_event(Event(pr_nb=0,
                               message="Failed to parse ranking result; keeping them all"))
            all_medium_risk_prs.extend(chunk)
        else:
            high_risk_prs, medium_risk, _ = ranking_result
            all_high_risk_prs.extend(high_risk_prs)
            all_medium_risk_prs.extend(medium_risk)

    result = all_high_risk_prs + all_medium_risk_prs
    append_event(Event(
        pr_nb=0, message=f"Keeping {len(result)} high/medium-risk PRs out of {len(github_prs)} total PRs"))
    return result


if __name__ == "__main__":

    # setup for testing on pandas
    cloned_repo = Repo("./data/repos/pandas")
    cloned_repo.git.checkout("main")
    cloned_repo.git.pull()
    token = open(".github_token", "r").read().strip()
    github = Github(auth=Auth.Token(token))
    project = PythonProjects.pandas_project
    github_repo = github.get_repo(project.project_id)

    # testing with motivating example
    # pr = github_repo.get_pull(55108)
    # check_pr(pr, github_repo, cloned_repo)

    # run on recent PRs, excluding those we've already checked
    # done_pr_numbers = find_prs_checked_in_past()
    # print(f"Already checked {len(done_pr_numbers)} PRs")
    # # github_prs = get_recent_prs(github_repo, nb=1000)
    # recent_pr_nbs = [58617, 58614, 58610, 58608, 58607, 58606, 58605, 58599, 58597, 58596, 58595, 58590, 58589, 58588, 58587, 58580, 58579, 58575, 58574, 58573, 58572, 58571, 58568, 58567, 58566, 58565, 58564, 58563, 58562, 58561, 58560, 58558, 58556, 58550, 58542, 58540, 58537, 58535, 58534, 58533, 58532, 58528, 58527, 58526, 58525, 58522, 58521, 58518, 58515, 58514, 58513, 58512, 58511, 58510, 58509, 58508, 58507, 58506, 58497, 58493, 58492, 58491, 58490, 58489, 58486, 58484, 58481, 58479, 58477, 58476, 58468, 58467, 58457, 58456, 58454, 58453, 58443, 58442, 58441, 58440, 58439, 58438, 58437, 58435, 58434, 58433, 58432, 58431, 58430, 58429, 58426, 58423, 58422, 58417, 58416, 58415, 58413, 58411, 58408, 58407, 58406, 58402, 58401, 58400, 58399, 58398, 58396, 58393, 58390, 58389, 58387, 58386, 58385, 58384, 58383, 58381, 58379, 58378, 58377, 58376, 58374, 58371, 58370, 58369, 58368, 58367, 58364, 58360, 58359, 58358, 58357, 58356, 58355, 58353, 58352, 58349, 58343, 58342, 58341, 58339, 58335, 58334, 58333, 58331, 58330, 58326, 58325, 58323, 58322, 58319, 58314, 58310, 58309, 58305, 58301, 58298, 58296, 58295, 58294, 58293, 58275, 58273, 58271, 58269, 58268, 58267, 58266, 58265, 58261, 58256, 58254, 58250, 58249, 58245, 58242, 58241, 58237, 58235, 58231, 58228, 58227, 58226, 58223, 58218, 58213, 58211, 58209, 58208, 58206, 58204, 58203, 58202, 58201, 58200, 58199, 58198, 58197, 58195, 58192, 58189, 58188, 58187, 58183, 58181, 58180, 58175, 58172, 58171, 58168, 58167, 58166, 58161, 58158, 58157, 58155, 58148, 58140, 58138, 58137, 58135, 58127, 58126, 58125, 58122, 58119, 58118, 58115, 58114, 58107, 58105, 58103, 58101, 58100, 58097, 58096, 58095, 58093, 58091, 58090, 58089, 58087, 58085, 58083, 58080, 58079, 58077, 58076, 58075, 58060, 58059, 58058, 58057, 58056, 58053, 58050, 58047, 58043, 58040, 58039, 58038, 58036, 58034, 58032, 58030, 58029, 58028, 58027, 58025, 58023, 58022, 58019, 58018, 58017, 58016, 58012, 58011, 58010, 58009, 58008, 58006, 58005, 58004, 58003, 58002, 58000, 57999, 57998, 57997, 57996, 57991, 57990, 57987, 57985, 57983, 57981, 57978, 57977, 57975, 57974, 57973, 57971, 57970, 57969, 57968, 57966, 57965, 57961, 57957, 57947, 57946, 57943, 57940, 57939, 57938, 57935, 57933, 57929, 57920, 57919, 57918, 57917, 57916, 57915, 57913, 57910, 57908, 57907, 57905, 57904, 57903, 57902, 57901, 57899, 57898, 57897, 57893, 57892, 57889, 57888, 57886, 57883, 57881, 57880, 57879, 57877, 57875, 57874, 57871, 57870, 57869, 57867, 57866, 57865, 57863, 57862, 57861, 57860, 57858, 57857, 57856, 57855, 57854, 57851, 57848, 57844, 57843, 57842, 57841, 57839, 57834, 57833, 57832, 57830, 57827, 57826, 57825, 57824, 57823, 57822, 57821, 57820, 57819, 57818, 57816, 57815, 57814, 57812, 57808, 57807, 57806, 57805, 57804, 57803, 57802, 57801, 57800, 57799, 57797, 57796, 57795, 57793, 57791, 57789, 57788, 57787, 57786, 57785, 57784, 57783, 57782, 57780, 57779, 57776, 57772, 57770, 57769, 57768, 57767, 57766, 57764, 57763, 57760, 57759, 57758, 57757, 57756, 57755, 57751, 57746, 57744, 57743, 57742, 57741, 57740, 57737, 57729, 57728, 57726, 57721, 57720, 57715, 57711, 57710, 57708, 57707, 57705, 57704, 57701, 57699, 57697, 57695, 57692, 57689, 57684, 57679, 57678, 57675, 57674, 57671, 57670, 57668, 57667, 57665, 57654, 57653, 57652, 57651, 57649, 57648, 57647, 57638, 57637, 57632, 57630, 57627, 57625, 57618, 57616, 57615, 57614, 57613, 57612, 57611, 57609, 57606, 57605, 57603, 57601, 57600, 57599, 57598, 57595, 57588, 57586, 57583, 57582, 57581, 57579, 57576,
    #                  57575, 57573, 57571, 57570, 57568, 57563, 57562, 57561, 57560, 57558, 57557, 57556, 57555, 57554, 57553, 57552, 57551, 57548, 57542, 57541, 57538, 57537, 57536, 57535, 57534, 57533, 57532, 57530, 57528, 57527, 57522, 57519, 57518, 57516, 57515, 57513, 57510, 57509, 57507, 57504, 57503, 57502, 57497, 57496, 57490, 57489, 57488, 57487, 57486, 57485, 57484, 57482, 57481, 57479, 57478, 57477, 57476, 57474, 57473, 57471, 57467, 57466, 57464, 57461, 57460, 57459, 57455, 57454, 57450, 57446, 57445, 57444, 57442, 57439, 57434, 57430, 57428, 57426, 57425, 57422, 57415, 57414, 57413, 57410, 57408, 57406, 57405, 57404, 57402, 57399, 57394, 57393, 57389, 57388, 57387, 57385, 57384, 57383, 57381, 57380, 57379, 57376, 57375, 57372, 57371, 57370, 57369, 57368, 57367, 57365, 57364, 57363, 57361, 57360, 57359, 57358, 57357, 57356, 57354, 57353, 57352, 57348, 57347, 57346, 57345, 57344, 57343, 57342, 57341, 57340, 57339, 57337, 57336, 57334, 57333, 57332, 57331, 57330, 57329, 57328, 57327, 57326, 57325, 57324, 57323, 57322, 57321, 57319, 57314, 57311, 57309, 57308, 57307, 57306, 57304, 57302, 57300, 57297, 57296, 57295, 57294, 57292, 57289, 57288, 57285, 57283, 57282, 57279, 57278, 57275, 57273, 57272, 57271, 57270, 57269, 57266, 57265, 57261, 57256, 57255, 57254, 57253, 57252, 57250, 57249, 57247, 57246, 57243, 57242, 57241, 57240, 57239, 57238, 57237, 57236, 57235, 57234, 57233, 57232, 57231, 57230, 57228, 57227, 57226, 57225, 57223, 57222, 57221, 57220, 57218, 57212, 57211, 57210, 57208, 57207, 57206, 57205, 57203, 57202, 57201, 57200, 57199, 57198, 57194, 57190, 57186, 57185, 57184, 57182, 57180, 57179, 57175, 57174, 57173, 57172, 57169, 57167, 57164, 57163, 57162, 57160, 57159, 57157, 57156, 57153, 57146, 57145, 57144, 57143, 57142, 57141, 57140, 57139, 57136, 57135, 57134, 57133, 57132, 57131, 57127, 57126, 57122, 57121, 57120, 57118, 57117, 57116, 57114, 57112, 57109, 57108, 57105, 57103, 57102, 57101, 57096, 57091, 57090, 57089, 57086, 57084, 57081, 57079, 57078, 57072, 57062, 57061, 57060, 57059, 57058, 57057, 57046, 57042, 57034, 57029, 57026, 57025, 57023, 57021, 57020, 57018, 57015, 57014, 57013, 57011, 57009, 57005, 56998, 56997, 56993, 56990, 56989, 56987, 56986, 56985, 56983, 56982, 56981, 56980, 56974, 56971, 56970, 56969, 56967, 56964, 56963, 56962, 56961, 56960, 56953, 56952, 56950, 56949, 56948, 56947, 56945, 56944, 56943, 56941, 56938, 56937, 56933, 56931, 56930, 56928, 56926, 56925, 56924, 56922, 56921, 56919, 56916, 56915, 56914, 56910, 56909, 56907, 56906, 56905, 56904, 56902, 56901, 56900, 56898, 56896, 56895, 56894, 56893, 56892, 56891, 56889, 56886, 56884, 56881, 56880, 56879, 56878, 56875, 56873, 56871, 56870, 56868, 56867, 56863, 56862, 56861, 56859, 56855, 56854, 56849, 56843, 56841, 56838, 56835, 56834, 56833, 56832, 56831, 56830, 56829, 56828, 56827, 56824, 56823, 56822, 56820, 56819, 56818, 56817, 56816, 56814, 56813, 56812, 56811, 56809, 56808, 56807, 56806, 56803, 56802, 56800, 56799, 56795, 56792, 56790, 56789, 56788, 56787, 56786, 56785, 56783, 56782, 56780, 56772, 56771, 56770, 56769, 56767, 56766, 56762, 56761, 56760, 56758, 56757, 56751, 56749, 56746, 56745, 56744, 56743, 56739, 56738, 56737, 56731, 56730, 56726, 56725, 56724, 56723, 56721, 56720, 56719, 56715, 56709, 56708, 56704, 56699, 56698, 56691, 56689, 56688, 56686, 56685, 56684, 56683, 56682, 56680, 56677, 56675, 56672, 56671, 56669, 56668, 56667, 56666, 56665, 56664, 56662, 56660, 56658, 56656, 56655, 56654, 56650, 56648, 56647, 56644, 56643, 56641, 56640, 56639]
    # recent_pr_nbs = [
    #     pr_nb for pr_nb in recent_pr_nbs if pr_nb not in done_pr_numbers]
    # github_prs = []
    # for pr_nb in recent_pr_nbs:
    #     github_prs.append(github_repo.get_pull(pr_nb))
    #     print(f"Added PR {pr_nb}")
    # github_prs = filter_and_sort_prs_by_risk(github_prs)
    # for github_pr in github_prs:
    #     # if github_pr.number in done_pr_numbers:
    #     #     print(f"Skipping PR {github_pr.number} because already analyzed")
    #     #     continue

    #     pr = PullRequest(github_pr, github_repo, cloned_repo)

    #     append_event(PREvent(pr_nb=pr.number,
    #                          message="Starting to check PR",
    #                          title=pr.github_pr.title, url=pr.github_pr.html_url))
    #     check_pr(pr)
    #     append_event(PREvent(pr_nb=pr.number,
    #                          message="Done with PR",
    #                          title=pr.github_pr.title, url=pr.github_pr.html_url))

    # testing on specific PRs
    # interesting_pr_numbers = [58479, 58390, 58369, 58322, 58148]
    # interesting_pr_numbers = [55108, 56841]  # known regression bugs
    interesting_pr_numbers = [58376, 58301, 58271, 57825, 57787,
                              57701, 57651, 57595, 58422]  # nine cases inspected on May 8
    github_prs = [github_repo.get_pull(pr_nb)
                  for pr_nb in interesting_pr_numbers]
    prs = [PullRequest(github_pr, github_repo, cloned_repo)
           for github_pr in github_prs]
    for pr in prs:
        append_event(PREvent(pr_nb=pr.number,
                             message="Starting to check PR",
                             title=pr.github_pr.title, url=pr.github_pr.html_url))
        check_pr(pr)
        append_event(PREvent(pr_nb=pr.number,
                             message="Done with PR",
                             title=pr.github_pr.title, url=pr.github_pr.html_url))
