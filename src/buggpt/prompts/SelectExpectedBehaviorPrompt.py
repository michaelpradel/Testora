import re

answer_pattern = re.compile(r"<ANSWER>(.*)</ANSWER>")


class SelectExpectedBehaviorPrompt:
    def __init__(self, project_name, test_code, output1, output2):
        self.project_name = project_name
        self.test_code = test_code
        self.output1 = output1
        self.output2 = output2

    def create_prompt(self):
        template = """
The following is a usage example of the {project_name} project:
```python
{test_code}
```

Consider the following two outputs that the above example could produce.

Output 1:
{output1}

Output 2:
{output2}

Which of the two outputs is the expected behavior of the example? Explain your reasoning, and then write in <ANSWER> and </ANSWER> tags either "Output 1" or "Output 2".
"""
        return template.format(project_name=self.project_name,
                               test_code=self.test_code,
                               output1=self.output1,
                               output2=self.output2)

    def parse_answer(self, raw_answer):
        answer = re.search(answer_pattern, raw_answer).group(1)
        if answer == "Output 1":
            return 1
        elif answer == "Output 2":
            return 2
        else:
            return 0
