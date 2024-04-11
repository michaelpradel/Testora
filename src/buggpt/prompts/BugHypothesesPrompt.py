class BugHypothesesPrompt:
    # NOTE: when changing the system message, must remove the old cache
    system_message = """
You are an experienced Python developer.
"""

    def __init__(self, code_context):
        self.code_context = code_context

    def create_prompt(self):
        prompt_template_code_part = """
Do you see any bugs in this function?
```python
<CODE>
```
The function is extracted from a larger project.
Assume that all necessary imports, other functions, and global variables are available.
Focus on logic errors and missing corner cases.
"""

        prompt_template_tests_part = """
As context, here are existing tests for the function:
<TESTS>

"""

        prompt_template_class_part = """
As context, here is the class that contains the function:
<CLASS>

"""

        prompt_template_instruction = """
Provide your answer as an enumerated list, with one bug on each line.
"""

        prompt_template = prompt_template_code_part
        if self.code_context.tests:
            prompt_template += prompt_template_tests_part
        if self.code_context.surrounding_class:
            prompt_template += prompt_template_class_part
        prompt_template += prompt_template_instruction

        prompt = prompt_template.replace(
            "<CODE>", self.code_context.fut).replace(
            "<TESTS>", self.code_context.tests).replace(
            "<CLASS>", self.code_context.surrounding_class)
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
