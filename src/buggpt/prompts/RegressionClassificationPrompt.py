class RegressionClassificationPrompt:
    def __init__(self, project_name, pr, fut_qualified_name, test_code, old_output, new_output):
        self.project_name = project_name
        self.pr = pr
        self.fut_qualified_name = fut_qualified_name
        self.test_code = test_code
        self.old_output = old_output
        self.new_output = new_output
        self.use_json_output = False

    def extract_pr_details(self):
        result = ""

        result += "## Comments\n"
        result += f"Comment by {self.pr.user.login}:\n"
        result += f"{self.pr.body}\n\n"
        for comment in self.pr.get_issue_comments():
            result += f"Comment by {comment.user.login}:\n"
            result += f"{comment.body}\n\n"

        result += "## Review comments\n"
        for comment in self.pr.get_comments():
            result += f"Comment by {comment.user.login}:\n"
            result += f"{comment.body}\n\n"

        result += "## Commit messages\n"
        for commit in self.pr.get_commits():
            result += f"{commit.commit.message}\n\n"

        return result

    def create_prompt(self):
        template = """
The pull request "{pr_title}" of the {project_name} project changes the {fut_qualified_name} function. Your task is to determine whether this change accidentally introduces a regression bug, i.e., an unintended change in behavior.

# Details about the pull request
{pr_details}

# Usage example that changes its behavior
```python
{test_code}
```

# Output of the usage example before the change
{old_output}

# Output of the usage example after the change
{new_output}

# Task
You should explain your reasoning and then answer two questions:
1) Is the different output a noteworthy change in behavior, as opposed to, e.g., a minor change in formatting? Answer either "minor" or "noteworthy".
2) Is the different output surprising given the intent of the pull request, i.e., is this a potential regression bug? Answer either "expected" or "surprising".
Explain your reasoning and then give your answers in the following format:
<THOUGHTS>
...
</THOUGHTS>
<ANSWER1>
...
</ANSWER1>
<ANSWER2>
...
</ANSWER2>
"""

        return template.format(project_name=self.project_name,
                               pr_title=self.pr.title,
                               fut_qualified_name=self.fut_qualified_name,
                               pr_details=self.extract_pr_details(),
                               test_code=self.test_code,
                               old_output=self.old_output,
                               new_output=self.new_output)

    def parse_answer(self, raw_answer):
        in_answer = 0
        is_relevant_change = None
        is_regression_bug = None
        for line in raw_answer.split("\n"):
            if in_answer == 1:
                if line.strip() == "noteworthy":
                    is_relevant_change = True
                elif line.strip() == "minor":
                    is_relevant_change = False
            elif in_answer == 2:
                if line.strip() == "surprising":
                    is_regression_bug = True
                elif line.strip() == "expected":
                    is_regression_bug = False

            if line.strip() == "</ANSWER1>" or line.strip() == "</ANSWER2>":
                in_answer = 0
            if line.strip() == "<ANSWER1>":
                in_answer = 1
            if line.strip() == "<ANSWER2>":
                in_answer = 2

        return is_relevant_change, is_regression_bug
