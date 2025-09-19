# Prompt for generating regression tests based on a given diff
# V2: Variant of V1 optimized by https://platform.openai.com/chat/edit?models=gpt-5&optimize=true for use with GPT-5

class RegressionTestGeneratorPromptV2:
    def __init__(self, project_name, fut_qualified_names, diff):
        self.project_name = project_name
        self.fut_qualified_names = fut_qualified_names
        self.diff = diff
        self.use_json_output = False

    def create_prompt(self):
        template = """
Developer: Begin with a concise checklist (3-7 bullets) of what you will do; keep items conceptual, not implementation-level.

Your task is to create usage examples for the {project_name} project, specifically designed to highlight behavioral differences introduced by the following diff:

{diff}

This diff modifies the following functions: {fut_qualified_names}.

Instructions:
- Use only the public API from {project_name}. Assume the package is installed and importable.
- Avoid using any randomly generated data or dynamic timestamps. All inputs must be fixed or deterministic.
- Generate a total of 20 executable Python usage examples, each in a separate, clearly marked code block.
- The first 10 examples should demonstrate standard/typical usage scenarios.
- The next 10 (examples 11-20) should focus on corner cases and edge conditions, such as unusual values (e.g., None, NaN, empty lists, etc.).
- Each Python code block must:
    - Be self-contained, including all necessary imports.
    - Begin with a comment: e.g., '# Example 1: <short description>'.
    - Include clear print statements for input arguments, outputs, and any intermediate values that help show differences in behavior.
    - If an exception is expected for an edge case, wrap the code in a try/except and print only the exception message (avoid printing stack traces).
- Use the following output format for each example:
```python
# Example <N>: <short description>
<example code>
```

Output Requirements:
- Submit exactly 20 Python code blocks, numbered sequentially from 1 to 20.
- Code blocks 1-10: Standard use cases.
- Code blocks 11-20: Edge/corner cases.
- Every block is executable and prints human-readable inputs and results.
- Exceptions are handled and their messages printed only.

After generating all examples, validate that each code block is executable and correctly numbered. If any do not meet the requirements, revise as needed before final submission.
"""

        return template.format(project_name=self.project_name,
                               fut_qualified_names=", ".join(
                                   self.fut_qualified_names),
                               diff=self.diff)

    def remove_unnecessary_indentation(self, code):
        lines = code.split("\n")
        if len(lines) > 0:
            # find number of leading spaces in first line
            num_spaces = len(lines[0]) - len(lines[0].lstrip())
            if num_spaces > 0:
                return "\n".join([line[num_spaces:] for line in lines])
        return code

    def parse_answer(self, raw_answer):
        assert type(raw_answer) == list

        tests = []

        for answer in raw_answer:
            in_code = False
            next_test = ""
            for line in answer.split("\n"):
                if line.strip() == "```":
                    in_code = False
                    if next_test:
                        next_test = self.remove_unnecessary_indentation(
                            next_test)
                        tests.append(next_test)
                        next_test = ""
                if in_code:
                    next_test += line + "\n"
                if line.strip() == "```python":
                    in_code = True

        return tests
