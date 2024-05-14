import json
from os import makedirs
from os.path import join, exists
import atexit
from buggpt.prompts.PromptCommon import system_message
from buggpt.util.Logs import append_event, LLMEvent

cache_base_dir = "./data/llm_cache/"
if not exists(cache_base_dir):
    makedirs(cache_base_dir)


class LLMCache:
    def __init__(self, llm_module):
        self.llm_module = llm_module

        name = llm_module.model
        cache_dir = join(cache_base_dir, name)
        if not exists(cache_dir):
            makedirs(cache_dir)

        self.cache_file = join(cache_dir, "cache.json")
        if exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

        self.nb_hits = 0
        self.nb_misses = 0

        self.nb_unwritten_updates = 0

        atexit.register(lambda: self.write_cache())

    def write_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f)
        print(
            f"LLMCache of {self.llm_module.model} with {len(self.cache)} entries saved. {self.nb_hits} hits, {self.nb_misses} misses.")

    def query(self, prompt, nb_samples=1):
        prompt_str = prompt.create_prompt()

        # check for cached answer
        result = self.cache.get(prompt_str)
        if result is not None:
            cached_answers = []
            if type(result) == str:
                cached_answers.append(result)
            elif type(result) == list:
                cached_answers = result

            if nb_samples <= len(cached_answers):
                append_event(LLMEvent(pr_nb=-1,
                                      message=f"Cached result for querying {self.llm_module.model}",
                                      content=f"System message:\n{system_message}\nUser message:\n{prompt.create_prompt()}"))
                self.nb_hits += 1
                print(f"Prompt:\n{prompt_str}\nReturning cached result\n")
                return cached_answers[:nb_samples]

        # no cached answer, query LLM
        self.nb_misses += 1
        result = self.llm_module.query(prompt)

        # update cache (only if answer is non-empty)
        if result:
            self.cache[prompt_str] = result
            self.nb_unwritten_updates += 1

        # write cache every 10 updates
        if self.nb_unwritten_updates > 10:
            self.write_cache()
            self.nb_unwritten_updates = 0

        return result
