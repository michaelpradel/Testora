
from testora.prompts.CodeExtractor import get_code_and_patch
from testora.prompts.Prompt1 import Prompt1
from testora.llms.LLMCache import LLMCache
import testora.llms.OpenAIGPT as uncached_llm
llm = LLMCache(uncached_llm)


code, _ = get_code_and_patch("Jsoup", 10, version="b")
p = Prompt1(code)
raw_answer = llm.query(p)
print("Raw answer:")
print(raw_answer)
answer = p.parse_answer(raw_answer)
print("Parsed answer:")
print(answer)

