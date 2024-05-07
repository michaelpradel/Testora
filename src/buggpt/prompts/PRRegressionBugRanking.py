import json
from buggpt.util.Logs import LLMEvent, append_event


class PRRegressionBugRanking:
    def __init__(self, prs):
        self.prs = prs
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
        pr_titles = [pr.github_pr.title for pr in self.prs]
        return template.replace("<pr_titles>", "\n".join(pr_titles))

    def parse_answer(self, r):
        try:
            risk_to_titles = json.loads(r)
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
        for pr in self.prs:
            if pr.github_pr.title in high_risk_titles:
                high_risk_prs.append(pr)
            elif pr.github_pr.title in medium_risk_titles:
                medium_risk_prs.append(pr)
            elif pr.github_pr.title in low_risk_titles:
                low_risk_prs.append(pr)
            else:
                append_event(LLMEvent(
                    pr_nb=pr.number, message=f"PRRegressionBugRanking omitted a PR title; assuming it's medium-risk", content=pr.github_pr.title))
                medium_risk_prs.append(pr)

        return high_risk_prs, medium_risk_prs, low_risk_prs
