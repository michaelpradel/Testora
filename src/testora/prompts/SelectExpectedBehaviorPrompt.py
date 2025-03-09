import re

from testora.util.Exceptions import TestoraException

answer_pattern = re.compile(r"<ANSWER>(.*?)</ANSWER>", re.DOTALL)


class SelectExpectedBehaviorPrompt:
    def __init__(self, project_name, test_code, output1, output2, docstrings):
        self.project_name = project_name
        self.test_code = test_code
        self.output1 = output1
        self.output2 = output2
        self.docstrings = docstrings
        self.use_json_output = False

    def create_prompt(self):
        template = """
# Usage Example
The following is a usage example of the {project_name} project:
```python
{test_code}
```

# Docstrings of Relevant APIs
{docstrings}

# Possible Outputs
Consider the following two outputs that the above example could produce.

Output 1:
{output1}

Output 2:
{output2}

# Question
Which of the two outputs is the expected behavior of the example? Explain your reasoning, and then write in <ANSWER> and </ANSWER> tags either "Output 1" or "Output 2".
"""
        return template.format(project_name=self.project_name,
                               test_code=self.test_code,
                               docstrings=self.docstrings,
                               output1=self.output1,
                               output2=self.output2)

    def parse_answer(self, raw_answer):
        assert type(raw_answer) == list
        assert len(raw_answer) == 1

        raw_answer = raw_answer[0]
        
        match = re.search(answer_pattern, raw_answer)
        if match is None:
            raise TestoraException("Could not find answer in the response.")
        answer = match.group(1)
        if answer.strip() == "Output 1":
            return 1
        elif answer.strip() == "Output 2":
            return 2
        else:
            return 0
