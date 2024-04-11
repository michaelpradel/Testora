from buggpt.util.PythonCodeUtil import get_name_of_defined_function, remove_function_with_name


class TestGenerationPrompt:
    def __init__(self, code_context, hypothesis):
        self.code_context = code_context
        self.hypothesis = hypothesis

    def create_prompt(self):
        prompt_template_code_part = """
Consider this Python function:
```python
<CODE>
```

The function may have a bug:
<HYPOTHESIS>

"""

        prompt_template_tests_part = """
As context, here are existing tests for the function:
```python
<TESTS>
```

"""

        prompt_template_class_part = """
As context, here is the class that contains the function:
```python
<CLASS>
```

"""

        prompt_template_instruction_part = """
Complete the following template into a complete, self-contained test case that exposes this bug:
```python
import unittest
from my_module import <FUNCTION_NAME>
# Any other required imports here

# Any mocks or stubs here

class MyTest(unittest.TestCase):
    def test(self):
```

Respond only with Python, i.e., no explanations.
```python
"""
        prompt = prompt_template_code_part.replace(
            "<CODE>", self.code_context.fut).replace(
            "<HYPOTHESIS>", self.hypothesis)
        if self.code_context.tests:
            prompt += prompt_template_tests_part.replace(
                "<TESTS>", self.code_context.tests)
        if self.code_context.surrounding_class:
            prompt += prompt_template_class_part.replace(
                "<CLASS>", self.code_context.surrounding_class)
        prompt += prompt_template_instruction_part.replace(
            "<FUNCTION_NAME>", self.code_context.fut_name)

        return prompt

    def parse_answer(self, raw_answer):
        generated_test = ""

        # extract code
        in_code = False
        for line in raw_answer.split("\n"):
            if line.strip() == "```":
                break
            if in_code:
                generated_test += line + "\n"
            if line == "```python" or line.startswith("import"):
                in_code = True

        # remove any copy (or modified version) of the code to check
        generated_test = remove_function_with_name(
            generated_test, self.code_context.fut_name)

        # insert the code to check
        fut_import_stmt = f"from my_module import {self.code_context.fut_name}"
        if fut_import_stmt in generated_test:
            full_code = generated_test.replace(
                fut_import_stmt, f"\n{self.code_context.fut}\n")
        else:
            full_code = f"{self.code_context.fut}\n{generated_test}"

        return full_code
