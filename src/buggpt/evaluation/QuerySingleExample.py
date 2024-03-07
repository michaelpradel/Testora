
from buggpt.prompts.CodeExtractor import get_changed_code_and_patch
from buggpt.prompts.Prompt import Prompt
import buggpt.llms.GPT_3_5_Turbo_0125 as LLM
# import buggpt.llms.MockModel as LLM

code, _ = get_changed_code_and_patch("Jsoup", 10, version="b")
p = Prompt(code)
raw_answer = LLM.query(p)
print("Raw answer:")
print(raw_answer)
answer = p.parse_answer(raw_answer)
print("Parsed answer:")
print(answer)

