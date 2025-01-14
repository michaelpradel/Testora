class RegressionClassificationPromptV4:
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
You should explain your reasoning and then answer five questions:
1) Is the different output a noteworthy change in behavior, such as a completely different value being computed, or is it a minor change, such as a change in a warning/error message or a change in formatting? Answer either "minor" or "noteworthy".
2) Is the different output likely due to non-determinism, e.g., because of random sampling or a non-deterministically ordered set? Answer either "deterministic" or "non-deterministic".
3) Does the usage example refer only to public APIs of {project_name}, or does it use any project-internal functionality? Answer either "public" or "project-internal".
4) Does the usage example pass inputs as intended by the API documentation, or does it pass any illegal (e.g., type-incorrect) inputs? Answer either "legal" or "illegal".
5) Does the different output match the intent of the developer of the pull request? A difference is "intended" if it is in line with the description of the pull request or a logical consequence of it. In contrast, a difference is "unintended" if it is caused by an accidentally introduced regression bug. For example, a pull request that optimizes performance typically is not expected to modify the functional behavior of the code. As another example, a pull request aiming to fix a bug triggered by a specific corner case input is usually not expected to modify the behavior when executing with other inputs. In your thoughts, state the intent of the pull request, summarize how the output differs, and then reason about whether the intent and the actual output difference are consistent. Answer either "intended" or "unintended".

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
<ANSWER4>
...
</ANSWER4>
<ANSWER5>
...
</ANSWER5>
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

        in_answer = 0
        is_relevant_change = None
        is_deterministic = None
        is_public = None
        is_legal = None
        is_surprising = None
        correct_output = -1
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
                if line.strip() == "public":
                    is_public = True
                elif line.strip() == "project-internal":
                    is_public = False
            elif in_answer == 4:
                if line.strip() == "legal":
                    is_legal = True
                elif line.strip() == "illegal":
                    is_legal = False
            elif in_answer == 5:
                if line.strip() == "intended":
                    is_surprising = False
                elif line.strip() == "unintended":
                    is_surprising = True

            if line.strip() == "</ANSWER1>" or line.strip() == "</ANSWER2>" or line.strip() == "</ANSWER3>":
                in_answer = 0
            if line.strip() == "<ANSWER1>":
                in_answer = 1
            if line.strip() == "<ANSWER2>":
                in_answer = 2
            if line.strip() == "<ANSWER3>":
                in_answer = 3
            if line.strip() == "<ANSWER4>":
                in_answer = 4
            if line.strip() == "<ANSWER5>":
                in_answer = 5

        return is_relevant_change, is_deterministic, is_public, is_legal, is_surprising, correct_output
