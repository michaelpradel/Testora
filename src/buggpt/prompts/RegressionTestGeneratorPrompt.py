class RegressionTestGeneratorPrompt:
    def __init__(self, project_name, fut_qualified_name, old_function_code, new_function_code):
        self.project_name = project_name
        self.fut_qualified_name = fut_qualified_name
        self.old_function_code = old_function_code
        self.new_function_code = new_function_code
        self.use_json_output = False

    def create_prompt(self):
        # TODO: for testing only
        #         old_function_code = """
        #     def _difference(self, other, sort):
        #         # overridden by RangeIndex

        #         this = self.unique()

        #         indexer = this.get_indexer_for(other)
        #         indexer = indexer.take((indexer != -1).nonzero()[0])

        #         label_diff = np.setdiff1d(np.arange(this.size), indexer, assume_unique=True)

        #         the_diff: MultiIndex | ArrayLike
        #         if isinstance(this, ABCMultiIndex):
        #             the_diff = this.take(label_diff)
        #         else:
        #             the_diff = this._values.take(label_diff)
        #         the_diff = _maybe_try_sort(the_diff, sort)

        #         return the_diff
        # """

        #         new_function_code = """
        #     def _difference(self, other, sort):
        #         # overridden by RangeIndex
        #         other = other.unique()
        #         the_diff = self[other.get_indexer_for(self) == -1]
        #         the_diff = the_diff if self.is_unique else the_diff.unique()
        #         the_diff = _maybe_try_sort(the_diff, sort)
        #         return the_diff
        # """

        template = """
Your task is to generate usage examples of the {project_name} project that expose behavioral differences between two versions of the {fut_qualified_name} Python function.

Old version of the function:
```python
{old_function_code}
```

New version of the function:
```python
{new_function_code}
```

The usage examples may use only the public API of the {project_name} project. You can assume that the project is installed and ready to be imported. Do NOT use any randomly generated data in your examples, but instead use fixed data that you provide in the examples.

Answer by giving ten usage examples that cover normal usage scenarios and ten usage examples that focus on corner cases (e.g., unusual values, such as None, NaN or empty lists).
Each example must be an executable piece of Python code, including all necessary imports, wrapped into
```python
```
"""

        return template.format(project_name=self.project_name,
                               fut_qualified_name=self.fut_qualified_name,
                               old_function_code=self.old_function_code,
                               new_function_code=self.new_function_code)

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


if __name__ == "__main__":
    prompt = RegressionTestGeneratorPrompt(
        "pandas", "pandas.core.indexes.base._difference")
    print(prompt.create_prompt())
