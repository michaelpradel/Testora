class BugHypothesesPrompt:
    # NOTE: when changing the system message, must remove the old cache
    system_message = """
You are an experienced Python developer.
"""

    instruction = """
Do you see any bugs in this code?
```python
<CODE>
```
The code is extracted from a larger project.
Assume that all necessary imports, other functions, and global variables are available.
Focus on logic errors, incorrect assumptions, and missing corner cases.
"""

    output_instruction = """
Provide your answer as an enumerated list, with one bug on each line.
"""

    def __init__(self, code_context):
        self.code_context = code_context

    def create_prompt(self):
        prompt = self.instruction.replace(
            "<CODE>", self.code_context.fut) + self.output_instruction
        return prompt

    def parse_answer(self, raw_answer):
        lines = raw_answer.split("\n")
        answer = {"bugs": []}
        for line in lines:
            if any([line.startswith(f"{nb}.") for nb in range(1, 10)]):
                _, _, cleaned_line = line.partition(".")
                cleaned_line = cleaned_line.strip()
                answer["bugs"].append({"explanation": cleaned_line})
        return answer
