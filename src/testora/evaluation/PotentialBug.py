from dataclasses import dataclass


@dataclass
class PotentialBug:
    project: str
    id: str
    hypothesis: str
    test: str
    test_output: str

    def __str__(self):
        result = f"Potential bug in {self.project} {self.id}\n"
        result += f"Hypothesis:\n{self.hypothesis}\n"
        result += f"Test case:\n{self.test}\n"
        result += f"Test output:\n{self.test_output}\n"
        return result

