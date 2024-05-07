class RegressionTestGeneratorPrompt:
    def __init__(self, project_name, fut_qualified_names, diff):
        self.project_name = project_name
        self.fut_qualified_names = fut_qualified_names
        self.diff = diff
        self.use_json_output = False

    def create_prompt(self):
        template = """
Your task is to generate usage examples of the {project_name} project that expose behavioral differences introduced by the following diff:

{diff}

The diff affects the following functions: {fut_qualified_names}.

The usage examples you create may use only the public API of the {project_name} project. You can assume that the project is installed and ready to be imported. Do NOT use any randomly generated data or timestamps in your examples; instead use fixed or deterministically created inputs. Create usage examples that are diverse and cover a wide range of scenarios, e.g., by (not) passing optional parameters or using different APIs to achieve the same purpose.

Answer by giving ten usage examples that cover normal usage scenarios and ten usage examples that focus on corner cases (e.g., unusual values, such as None, NaN or empty lists).
Each example must be an executable piece of Python code, including all necessary imports, wrapped into
```python
```
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
        tests = []

        in_code = False
        next_test = ""
        for line in raw_answer.split("\n"):
            if line.strip() == "```":
                in_code = False
                if next_test:
                    next_test = self.remove_unnecessary_indentation(next_test)
                    tests.append(next_test)
                    next_test = ""
            if in_code:
                next_test += line + "\n"
            if line.strip() == "```python":
                in_code = True

        return tests

