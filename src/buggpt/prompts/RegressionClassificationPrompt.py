class RegressionClassificationPrompt:
    def __init__(self, project_name, pr, fut_qualified_names, test_code, old_output, new_output):
        self.project_name = project_name
        self.pr = pr
        self.fut_qualified_names = fut_qualified_names
        self.test_code = test_code
        self.old_output = old_output
        self.new_output = new_output
        self.use_json_output = False

    def extract_pr_details(self):
        result = ""

        result += "## Comments\n"
        result += f"Comment by {self.pr.github_pr.user.login}:\n"
        result += f"{self.pr.github_pr.body}\n\n"
        for comment in self.pr.github_pr.get_issue_comments():
            result += f"Comment by {comment.user.login}:\n"
            result += f"{comment.body}\n\n"

        result += "## Review comments\n"
        for comment in self.pr.github_pr.get_comments():
            result += f"Comment by {comment.user.login}:\n"
            result += f"{comment.body}\n\n"

        result += "## Commit messages\n"
        for commit in self.pr.github_pr.get_commits():
            result += f"{commit.commit.message}\n\n"

        return result

    def create_prompt(self):
        template = """
The pull request "{pr_title}" of the {project_name} project changes the {fut_qualified_names} function(s). Your task is to determine whether this change accidentally introduces a regression bug, i.e., an unintended change in behavior.

# Details about the pull request
{pr_details}

# Diff of the pull request
{diff}

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
2) Is the different output likely due to non-determinism, e.g., because of random sampling or a non-deterministically ordered set? Answer either "deterministic" or "non-deterministic".
3) Is the different output surprising given the intent of the pull request, i.e., is this a potential regression bug? Answer either "expected" or "surprising".
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
<ANSWER3>
...
</ANSWER3>
"""

        query = template.format(project_name=self.project_name,
                                pr_title=self.pr.github_pr.title,
                                fut_qualified_names=", ".join(
                                    self.fut_qualified_names),
                                pr_details=self.extract_pr_details(),
                                diff=self.pr.get_full_diff(),
                                test_code=self.test_code,
                                old_output=self.old_output,
                                new_output=self.new_output)
        if len(query) < 10000:
            return query

        query = template.format(project_name=self.project_name,
                                pr_title=self.pr.github_pr.title,
                                fut_qualified_names=", ".join(
                                    self.fut_qualified_names),
                                pr_details=self.extract_pr_details(),
                                diff=self.pr.get_filtered_diff(),
                                test_code=self.test_code,
                                old_output=self.old_output,
                                new_output=self.new_output)
        if len(query) < 10000:
            return query

        query = template.format(project_name=self.project_name,
                                pr_title=self.pr.github_pr.title,
                                fut_qualified_names=", ".join(
                                    self.fut_qualified_names),
                                pr_details=self.extract_pr_details(),
                                diff="(omitted due to length)",
                                test_code=self.test_code,
                                old_output=self.old_output,
                                new_output=self.new_output)
        return query

    def parse_answer(self, raw_answer):
        in_answer = 0
        is_relevant_change = None
        is_deterministic = None
        is_regression_bug = None
        for line in raw_answer.split("\n"):
            if in_answer == 1:
                if line.strip() == "noteworthy":
                    is_relevant_change = True
                elif line.strip() == "minor":
                    is_relevant_change = False
            elif in_answer == 2:
                if line.strip() == "deterministic":
                    is_deterministic = True
                elif line.strip() == "non-deterministic":
                    is_deterministic = False
            elif in_answer == 3:
                if line.strip() == "surprising":
                    is_regression_bug = True
                elif line.strip() == "expected":
                    is_regression_bug = False

            if line.strip() == "</ANSWER1>" or line.strip() == "</ANSWER2>" or line.strip() == "</ANSWER3>":
                in_answer = 0
            if line.strip() == "<ANSWER1>":
                in_answer = 1
            if line.strip() == "<ANSWER2>":
                in_answer = 2
            if line.strip() == "<ANSWER3>":
                in_answer = 3

        return is_relevant_change, is_deterministic, is_regression_bug
