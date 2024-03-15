from dataclasses import dataclass
import json

from buggpt.prompts.BugHypothesesPrompt import BugHypothesesPrompt
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


def create_and_execute_test_case(hypothesis):
    print(f"Creating test case for hypothesis:\n{hypothesis}")


# for testing
code_to_check = get_code_to_check("scrapy", 29)

hypotheses = create_bug_hypotheses(code_to_check)
for hypothesis in hypotheses:
    create_and_execute_test_case(hypothesis)
