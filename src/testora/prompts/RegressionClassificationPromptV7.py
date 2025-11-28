# Prompt for classifying whether a code change introduces a regression
# V7: Variant of V4 optimized by https://platform.openai.com/chat/edit?models=gpt-5&optimize=true for use with GPT-5

import json
import re

from testora.util.ClassificationResult import Classification, ClassificationResult


class RegressionClassificationPromptV7:
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
For the pull request titled "{pr_title}" in the {project_name} project, which modifies the following function(s): {fut_qualified_names}, your task is to assess whether the change introduces an unintended regression bug—that is, a change in functional behavior not intended by the author. This is important, as even small code changes can introduce unexpected effects.

Begin with a concise checklist (3-7 conceptual steps) of what you will do before starting your detailed analysis.

## Pull Request Details
{pr_details}

## Diff
{diff}

## Relevant API Docstrings
{docstrings}

## Usage Example with Changed Behavior
```python
{test_code}
```

### Output Before the Change
{old_output}

### Output After the Change
{new_output}

## Instructions
- Explain your reasoning clearly and succinctly.
- After completing your analysis, answer the following five questions:

1. Is the difference in output a noteworthy change in behavior (e.g., a completely different computed value), or a minor change (e.g., different warning/error message or formatting)? Respond with "minor" or "noteworthy".
2. Is the different output likely caused by non-determinism (such as randomness or unpredictable ordering) or is it deterministic? Respond with "deterministic" or "non-deterministic".
3. Does the usage example only use public APIs of {project_name}, or does it access project-internal functions? Respond with "public" or "project-internal".
4. Does the usage example use inputs as intended by the API documentation, or are any inputs illegal (such as type errors)? Respond with "legal" or "illegal".
5. Does the changed output match the pull request author's intent? Consider the stated purpose and logical implications of the PR. Respond with "intended" if the behavior matches the PR description or "unintended" if it appears to be an accidental regression bug.

### Output Format
Return your answer as a JSON object following this schema:

{{
  "thoughts": string,          // Detail your reasoning and any observations.
  "answer1": string,           // "minor" or "noteworthy"
  "answer2": string,           // "deterministic" or "non-deterministic"
  "answer3": string,           // "public" or "project-internal"
  "answer4": string,           // "legal" or "illegal"
  "answer5": string            // "intended" or "unintended"
}}

Example output:
```
{{
  "thoughts": "The pull request addresses a corner case bug as stated in the PR. Test code uses valid inputs and public APIs. The updated output aligns with expected behavior and is deterministic.",
  "answer1": "noteworthy",
  "answer2": "deterministic",
  "answer3": "public",
  "answer4": "legal",
  "answer5": "intended"
}}
```

If any required detail (such as diffs, docstrings, outputs, or test code) is missing, mention this in the "thoughts" field and answer the other questions based on the available information.
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

    def parse_answer(self, raw_answer) -> ClassificationResult:
        assert type(raw_answer) == list
        assert len(raw_answer) == 1

        raw_answer = raw_answer[0]

        backtick_regexp = re.sub(
            r"^```(?:json)?|```$", "", raw_answer.strip(),
            flags=re.MULTILINE)
        cleaned = backtick_regexp.strip()
        extracted = cleaned[cleaned.find("{"):cleaned.rfind("}")+1]
        answer = json.loads(extracted)

        if answer["answer1"] == "noteworthy" and \
            answer["answer2"] == "deterministic" and \
            answer["answer3"] == "public" and \
            answer["answer4"] == "legal" and \
            answer["answer5"] == "intended":
            classification = Classification.REGRESSION
        else:
            classification = Classification.INTENDED_CHANGE

        classification_result = ClassificationResult(
            test_code=self.test_code,
            old_output=self.old_output,
            new_output=self.new_output,
            classification=classification,
            classification_explanation=answer["thoughts"]
        )

        return classification_result
