from dataclasses import dataclass
from enum import Enum


class Classification(str, Enum):
    UNKNOWN = "unknown"
    INTENDED_CHANGE = "intended_change"
    COINCIDENTAL_FIX = "coincidental_fix"
    REGRESSION = "regression"


@dataclass
class ClassificationResult:
    test_code: str
    old_output: str
    new_output: str
    classification: Classification
    classification_explanation: str
