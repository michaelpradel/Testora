from dataclasses import dataclass
from typing import Optional


@dataclass
class TestExecution:
    code: str
    output: Optional[str] = None
    coverage_report: Optional[str] = None
