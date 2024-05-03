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
The pull request "{pr_title}" of the {project_name} project changes the behavior of the {fut_qualified_name} function. Your task is to determine whether this change is intended or unintended.

# Details about the pull request
{pr_details}

# Usage example that changes its behavior:
```python
{test_code}
```

# Output of the usage example before the change
{old_output}

# Output of the usage example after the change
{new_output}

# Task
You should answer the question "Is this behavioral change intended?".
Explain your reasoning and then give your verdict in the following format:
<THOUGHTS>
...
</THOUGHTS>
<VERDICT>
...
</VERDICT>
The verdict should be a single word: "intended" or "unintended".
"""

        return template.format(project_name=self.project_name,
                               pr_title=self.pr.title,
                               fut_qualified_name=self.fut_qualified_name,
                               pr_details=self.extract_pr_details(),
                               test_code=self.test_code,
                               old_output=self.old_output,
                               new_output=self.new_output)

    def parse_answer(self, raw_answer):
        in_verdict = False
        for line in raw_answer.split("\n"):
            if in_verdict:
                if line.strip() == "intended":
                    return "intended"
                elif line.strip() == "unintended":
                    return "unintended"
                else:
                    return "unclear"
            if line.strip() == "</VERDICT>":
                in_verdict = False
            if line.strip() == "<VERDICT>":
                in_verdict = True

        return "unclear"
