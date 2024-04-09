from dataclasses import dataclass

from buggpt.util.BugsInPy import get_code_and_patch_range, get_test_code
from buggpt.util.PythonCodeUtil import extract_target_function, get_name_of_defined_function, get_surrounding_class

@dataclass
class CodeContext:
    fut: str
    fut_name: str
    surrounding_class: str
    tests: str

def gather_code_context(project, id):
    code, patch_range = get_code_and_patch_range(project, id)
    tests = get_test_code(project, id)
    fut_code = extract_target_function(code, patch_range)
    fut_name = get_name_of_defined_function(fut_code)
    surrounding_class = get_surrounding_class(code, patch_range, fut_name)
    return CodeContext(fut_code, fut_name, surrounding_class, tests)
