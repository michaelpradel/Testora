from datetime import date
import json
from os import makedirs
from os.path import join, exists
import atexit

cache_base_dir = "./data/llm_cache/"
if not exists(cache_base_dir):
    makedirs(cache_base_dir)


class LLMCache:
    def __init__(self, llm_module):
        self.llm_module = llm_module

        name = llm_module.__name__.split(".")[-1]
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

        atexit.register(lambda: self.finalize())

    def finalize(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f)
        print(
            f"LLMCache with {len(self.cache)} entries saved. {self.nb_hits} hits, {self.nb_misses} misses.")

    def query(self, prompt):
        prompt_str = prompt.create_prompt()
        result = self.cache.get(prompt_str)
        if result is not None:
            self.nb_hits += 1
            print(f"Prompt:\n{prompt_str}\nReturning cached result\n")
            return result

        result = self.llm_module.query(prompt)
        self.cache[prompt_str] = result
        self.nb_misses += 1
        return result
