
from buggpt.prompts.CodeExtractor import get_changed_code_and_patch
from buggpt.prompts.Prompt import Prompt
from buggpt.llms.LLMCache import LLMCache
# import buggpt.llms.MockModel as llm
import buggpt.llms.GPT_3_5_Turbo_0125 as uncached_llm
llm = LLMCache(uncached_llm)


code, _ = get_changed_code_and_patch("Jsoup", 10, version="b")
p = Prompt(code)
raw_answer = llm.query(p)
print("Raw answer:")
print(raw_answer)
answer = p.parse_answer(raw_answer)
print("Parsed answer:")
print(answer)

