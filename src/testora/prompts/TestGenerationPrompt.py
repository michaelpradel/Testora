class TestGenerationPrompt:
    def __init__(self, project_name, qualified_api):
        self.project_name = project_name
        self.qualified_api = qualified_api
        self.use_json_output = False

    def create_prompt(self):
        template = """
Generate ten unit-level tests for the {qualified_api} function of the {project_name} project.
Focus on legal usage scenarios.
Add assertions to check the output of the function.

Each example must be an executable piece of Python code, including all necessary imports and definitions.

Wrap each individual example into Python code blocks by using the following output format:
```python
# Example 1:
...
```
```python
# Example 2:
...
```
```python
# Example 3:
...
```
etc.
"""
        return template.format(project_name=self.project_name,
                               qualified_api=self.qualified_api)

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
        raw_answer = raw_answer[0]

        tests = []

        in_code = False
        next_test = ""
        for line in raw_answer.split("\n"):
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
