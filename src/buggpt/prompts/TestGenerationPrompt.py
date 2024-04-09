from buggpt.util.PythonCodeUtil import get_name_of_defined_function, remove_function_with_name


class TestGenerationPrompt:
   # NOTE: when changing the system message, must remove the old cache
    system_message = """
You are an experienced Python developer.
"""

    instruction = """
Consider this Python code:
```python
<CODE>
```

The code may have a bug:
<HYPOTHESIS>

Complete the following template into a complete, self-contained test case that exposes this bug:
```python
import unittest
from my_module import <FUNCTION_NAME>
# Any other required imports here

# Any mocks or stubs here

class MyTest(unittest.TestCase):
    def test_bug(self):
```

Respond only with Python, i.e., no explanations.
```python
"""

    def __init__(self, code_to_check, hypothesis):
        self.code_to_check = code_to_check
        self.fut_name = get_name_of_defined_function(self.code_to_check)
        self.hypothesis = hypothesis
        self.use_json_output = False

    def create_prompt(self):

        prompt = self.instruction.replace(
            "<CODE>", self.code_to_check).replace(
            "<HYPOTHESIS>", self.hypothesis).replace(
            "<FUNCTION_NAME>", self.fut_name)
        return prompt

    def parse_answer(self, raw_answer):
        generated_test = ""

        # extract code
        in_code = False
        for line in raw_answer.split("\n"):
            if line == "```":
                break
            if in_code:
                generated_test += line + "\n"
            if line == "```python" or line.startswith("import"):
                in_code = True

        # remove any copy (or modified version) of the code to check
        generated_test = remove_function_with_name(generated_test, self.fut_name)
         
        # insert the code to check
        fut_import_stmt = f"from my_module import {self.fut_name}"
        if fut_import_stmt in generated_test:
            full_code = generated_test.replace(
                fut_import_stmt, f"\n{self.code_to_check}\n")
        else:
            full_code = f"{self.code_to_check}\n{generated_test}"

        return full_code
