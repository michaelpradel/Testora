import json
from testora.evaluation.PotentialBug import PotentialBug
from testora.util import Stats
from testora.util.Defects4J import get_target_bugs
from testora.util.PythonCodeUtil import add_call_to_test_function, is_parsable

from testora.execution.DockerExecutor import DockerExecutor
from testora.prompts.BugHypothesesPrompt import BugHypothesesPrompt
from testora.prompts.TestGenerationPrompt import TestGenerationPrompt
from testora.util.BugsInPy import get_commit_url
from testora.llms.LLMCache import LLMCache
from testora.prompts.CodeContext import gather_code_context
import testora.llms.OpenAIGPT as uncached_llm
llm = LLMCache(uncached_llm)


def create_bug_hypotheses(code_context):
    prompt = BugHypothesesPrompt(code_context)
    raw_answer = llm.query(prompt)
    print(raw_answer)
    answer = prompt.parse_answer(raw_answer)
    print(json.dumps(answer, indent=2))
    hypotheses = [bug["explanation"] for bug in answer["bugs"]]
    return hypotheses


def create_and_execute_test_case(code_context, hypothesis, project, id):
    print(f"Creating test case for hypothesis:\n{hypothesis}")
    executor = DockerExecutor()
    prompt = TestGenerationPrompt(code_context, hypothesis)
    raw_answer = llm.query(prompt)
    print("------ Raw answer:")
    print(raw_answer)
    generated_test = prompt.parse_answer(raw_answer)
    print("------ Generated test:")
    print(generated_test)
    parses = is_parsable(generated_test)
    print(f"Parsable: {parses}")
    if parses:
        Stats.parsable_tests += 1
        has_produced_failure, test_output = executor.execute_python_test(
            generated_test)
        if has_produced_failure:
            return PotentialBug(project, id, hypothesis, generated_test, test_output)
    else:
        Stats.unparsable_tests += 1


# for testing on a single function:
# target_bugs = [("scrapy", 29)]
# for testing on tens of manually selected functions:
# target_bugs = get_target_bugs(
#     "./data/bugsInPy_manually_selected_target_bugs.csv")
# for testing on 15 automatically selected functions:
target_bugs = get_target_bugs(
    "./data/bugsInPy_auto_selected_April_11_2024.csv")[4:]

potential_bugs = []

for project, id in target_bugs:
    Stats.attempted_target_bugs += 1
    print(
        f"========================= Starting to check {project} {id} =========================\n")
    print(f"Fix commit: {get_commit_url(project, id)}\n")

    print(f"++++++++++++++++++++++++++++++\nCreating hypotheses about bug\n++++++++++++++++++++++++++++++\n")
    code_context = gather_code_context(project, id)
    hypotheses = create_bug_hypotheses(code_context)
    for idx, hypothesis in enumerate(hypotheses):
        Stats.attempted_hypotheses += 1
        print(
            f"+++++++++++++++++++++++++++++++++++++++++\nGenerating test to validate hypothesis {idx}\n+++++++++++++++++++++++++++++++++++++++++\n")
        potential_bug = create_and_execute_test_case(
            code_context, hypothesis, project, id)
        if potential_bug:
            potential_bugs.append(potential_bug)

print(f"\n{len(potential_bugs)} potential bugs found\n")

# detailed output
for potential_bug in potential_bugs:
    print("####################")
    print(potential_bug)
    print()

# summary table
print("Summary of potential bugs:")
for potential_bug in potential_bugs:
    print(f"{potential_bug.project} {potential_bug.id}")
