
from buggpt.prompts.CodeExtractor import get_code_and_patch
from buggpt.prompts.Prompt1 import Prompt1
from buggpt.llms.LLMCache import LLMCache
# import buggpt.llms.MockModel as llm
import buggpt.llms.OpenAIGPT as uncached_llm
llm = LLMCache(uncached_llm)


code, _ = get_code_and_patch("Jsoup", 10, version="b")
p = Prompt1(code)
raw_answer = llm.query(p)
print("Raw answer:")
print(raw_answer)
answer = p.parse_answer(raw_answer)
print("Parsed answer:")
print(answer)

