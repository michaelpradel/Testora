class RegressionClassificationPromptV6:
    def __init__(self, project_name, pr, fut_qualified_names, docstrings, test_code, old_output, new_output):
        self.project_name = project_name
        self.pr = pr
        self.fut_qualified_names = fut_qualified_names
        self.docstrings = docstrings
        self.test_code = test_code
        self.old_output = old_output
        self.new_output = new_output
        self.use_json_output = False

    def extract_pr_details(self):
        comments = ""
        comments += f"Comment by {self.pr.github_pr.user.login}:\n"
        comments += f"{self.pr.github_pr.body}\n\n"
        for comment in self.pr.github_pr.get_issue_comments():
            new_comment = f"Comment by {comment.user.login}:\n"
            new_comment += f"{comment.body}\n\n"
            if len(comments) + len(new_comment) > 2000:
                comments += "(...)\n\n"
                break
            comments += new_comment

        review_comments = ""
        for comment in self.pr.github_pr.get_comments():
            new_review_comment = f"Comment by {comment.user.login}:\n"
            new_review_comment += f"{comment.body}\n\n"
            if len(review_comments) + len(new_review_comment) > 2000:
                review_comments += "(...)\n\n"
                break
            review_comments += new_review_comment

        commit_messages = ""
        commit_messages += "## Commit messages\n"
        for commit in self.pr.github_pr.get_commits():
            new_commit_message = f"{commit.commit.message}\n\n"
            if len(commit_messages) + len(new_commit_message) > 2000:
                commit_messages += "(...)\n\n"
                break
            commit_messages += new_commit_message

        result = ""
        result += "## Comments\n"
        result += comments
        result += "## Review comments\n"
        result += review_comments
        result += "## Commit messages\n"
        result += commit_messages
        return result

    def create_prompt(self):
        template = """
The pull request "{pr_title}" of the {project_name} project changes the {fut_qualified_names} function(s).
Your tasks is to determine whether this change accidentally introduces a regression bug, i.e., an unintended change in the functional behavior of the code. This task is important because code changes sometimes have unintended consequences.

# Details about the pull request
{pr_details}

# Diff of the pull request
{diff}

# Docstrings of Relevant APIs
{docstrings}

# Usage example that changes its behavior
```python
{test_code}
```

# Output of the usage example before the change
{old_output}

# Output of the usage example after the change
{new_output}

# Task
You should explain your reasoning and then answer this question:
Does the different output match the intent of the developer of the pull request? A difference is "intended" if it is in line with the description of the pull request or a logical consequence of it. In contrast, a difference is "unintended" if it is caused by an accidentally introduced regression bug. For example, a pull request that optimizes performance typically is not expected to modify the functional behavior of the code. As another example, a pull request aiming to fix a bug triggered by a specific corner case input is usually not expected to modify the behavior when executing with other inputs. In your thoughts, state the intent of the pull request, summarize how the output differs, and then reason about whether the intent and the actual output difference are consistent. Answer either "intended" or "unintended".

Explain your reasoning and then give your answers in the following format:
<THOUGHTS>
...
</THOUGHTS>
<ANSWER>
...
</ANSWER>
"""

        query = template.format(project_name=self.project_name,
                                pr_title=self.pr.github_pr.title,
                                fut_qualified_names=", ".join(
                                    self.fut_qualified_names),
                                docstrings=self.docstrings,
                                pr_details=self.extract_pr_details(),
                                diff=self.pr.get_full_diff(),
                                test_code=self.test_code,
                                old_output=self.old_output,
                                new_output=self.new_output)
        if len(query) < 30000:
            return query

        # too long, try with filtered diff
        query = template.format(project_name=self.project_name,
                                pr_title=self.pr.github_pr.title,
                                fut_qualified_names=", ".join(
                                    self.fut_qualified_names),
                                docstrings=self.docstrings,
                                pr_details=self.extract_pr_details(),
                                diff=self.pr.get_filtered_diff(),
                                test_code=self.test_code,
                                old_output=self.old_output,
                                new_output=self.new_output)
        if len(query) < 30000:
            return query

        # still too long, try without diff
        query = template.format(project_name=self.project_name,
                                pr_title=self.pr.github_pr.title,
                                fut_qualified_names=", ".join(
                                    self.fut_qualified_names),
                                docstrings=self.docstrings,
                                pr_details=self.extract_pr_details(),
                                diff="(omitted due to length)",
                                test_code=self.test_code,
                                old_output=self.old_output,
                                new_output=self.new_output)
        if len(query) < 30000:
            return query

        # still too long, omit some PR details
        chars_to_save = len(query) - 30000
        full_pr_details = self.extract_pr_details()
        shortened_pr_details = full_pr_details[:(
            len(full_pr_details) - chars_to_save)]

        query = template.format(project_name=self.project_name,
                                pr_title=self.pr.github_pr.title,
                                fut_qualified_names=", ".join(
                                    self.fut_qualified_names),
                                docstrings=self.docstrings,
                                pr_details=shortened_pr_details,
                                diff="(omitted due to length)",
                                test_code=self.test_code,
                                old_output=self.old_output,
                                new_output=self.new_output)

        return query

    def parse_answer(self, raw_answer):
        assert type(raw_answer) == list
        assert len(raw_answer) == 1

        raw_answer = raw_answer[0]

        in_answer = False
        is_surprising = None
        for line in raw_answer.split("\n"):
            if in_answer:
                if line.strip() == "intended":
                    is_surprising = False
                elif line.strip() == "unintended":
                    is_surprising = True

            if line.strip() == "<ANSWER>":
                in_answer = True
            if line.strip() == "</ANSWER>":
                break

        return is_surprising
