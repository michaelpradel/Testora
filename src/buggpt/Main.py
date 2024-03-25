from dataclasses import dataclass
import json
from buggpt.util import Stats
from buggpt.util.Defects4J import get_target_bugs
from buggpt.util.PythonCodeUtil import add_call_to_test_function, is_parsable

from buggpt.execution.DockerExecutor import DockerExecutor
from buggpt.prompts.BugHypothesesPrompt import BugHypothesesPrompt
from buggpt.prompts.TestGenerationPrompt import TestGenerationPrompt
from buggpt.util.BugsInPy import get_code_to_check
from buggpt.llms.LLMCache import LLMCache
import buggpt.llms.GPT_3_5_Turbo_0125 as uncached_llm
llm = LLMCache(uncached_llm)


@dataclass
class CodeToCheck:
    code: str


def create_bug_hypotheses(code_to_check):
    prompt = BugHypothesesPrompt(code_to_check)
    raw_answer = llm.query(prompt)
    print(raw_answer)
    answer = prompt.parse_answer(raw_answer)
    print(json.dumps(answer, indent=2))
    hypotheses = [bug["explanation"] for bug in answer["bugs"]]
    return hypotheses


def create_and_execute_test_case(code_to_check, hypothesis):
    print(f"Creating test case for hypothesis:\n{hypothesis}")
    executor = DockerExecutor()
    prompt = TestGenerationPrompt(code_to_check, hypothesis)
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
        executor.execute_python_test(generated_test)
    else:
        Stats.unparsable_tests += 1


# for testing on a single function:
# target_bugs = [("scrapy", 29)]
# for testing on tens of functions:
target_bugs = get_target_bugs(
    "data/bugsInPy_manually_selected_target_bugs.csv")[:5]

for target_bug in target_bugs:
    Stats.attempted_target_bugs += 1
    print(
        f"========================= Starting to check {target_bug[0]} {target_bug[1]} =========================\n")
    code_to_check = get_code_to_check(target_bug[0], target_bug[1])

    print(f"++++++++++++++++++++++++++++++\nCreating hypotheses about bug\n++++++++++++++++++++++++++++++\n")
    hypotheses = create_bug_hypotheses(code_to_check)
    for idx, hypothesis in enumerate(hypotheses):
        Stats.attempted_hypotheses += 1
        print(
            f"+++++++++++++++++++++++++++++++++++++++++\nGenerating test to validate hypothesis {idx}\n+++++++++++++++++++++++++++++++++++++++++\n")
        create_and_execute_test_case(code_to_check, hypothesis)
