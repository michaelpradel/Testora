import json
from buggpt.util.Logs import LLMEvent, append_event


class PRRegressionBugRanking:
    def __init__(self, github_prs):
        self.github_prs = github_prs
        self.use_json_output = True

    def create_prompt(self):
        template = """
The following is a list of titles of pull requests in the pandas project. Rank them by their likelihood to accidentally introduce a regression bug.

<pr_titles>

Provide your answer using this JSON format:
```json
{
    "high risk": [
        "PR title 1",
        "PR title 2",
        ...
    ],
    "medium risk": [
        "PR title 3",
        "PR title 4",
        ...
    ],
    "low risk": [
        "PR title 5",
        "PR title 6",
        ...
    ]
}
```
Make sure to include ALL the given pull requests into the output.
"""
        pr_titles = [github_pr.title for github_pr in self.github_prs]
        return template.replace("<pr_titles>", "\n".join(pr_titles))

    def parse_answer(self, raw_answer):
        assert type(raw_answer) == list
        assert len(raw_answer) == 1

        raw_answer = raw_answer[0]

        try:
            risk_to_titles = json.loads(raw_answer)
        except json.JSONDecodeError:
            return None

        if not isinstance(risk_to_titles, dict):
            return None

        if not all(isinstance(risk_to_titles.get(risk), list) for risk in ["high risk", "medium risk", "low risk"]):
            return None

        high_risk_titles = set(risk_to_titles.get("high risk"))
        medium_risk_titles = set(risk_to_titles.get("medium risk"))
        low_risk_titles = set(risk_to_titles.get("low risk"))

        high_risk_prs = []
        medium_risk_prs = []
        low_risk_prs = []
        for github_pr in self.github_prs:
            if github_pr.title in high_risk_titles:
                high_risk_prs.append(github_pr)
            elif github_pr.title in medium_risk_titles:
                medium_risk_prs.append(github_pr)
            elif github_pr.title in low_risk_titles:
                low_risk_prs.append(github_pr)
            else:
                append_event(LLMEvent(
                    pr_nb=github_pr.number, message=f"PRRegressionBugRanking omitted a PR title; assuming it's medium-risk", content=github_pr.title))
                medium_risk_prs.append(github_pr)

        return high_risk_prs, medium_risk_prs, low_risk_prs
