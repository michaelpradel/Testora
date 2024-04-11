from dataclasses import dataclass

from buggpt.util.BugsInPy import get_code_and_patch_range, get_test_code
from buggpt.util.PythonCodeUtil import extract_target_function, extract_tests_of_fut, get_name_of_defined_function, get_surrounding_class


@dataclass
class CodeContext:
    fut: str
    fut_name: str
    surrounding_class: str
    tests: str


def gather_code_context(project, id):
    code, patch_range = get_code_and_patch_range(project, id)
    all_test_code = get_test_code(project, id)
    fut_code = extract_target_function(code, patch_range)
    fut_name = get_name_of_defined_function(fut_code)
    tests = extract_tests_of_fut(all_test_code, fut_name)
    
    surrounding_class = get_surrounding_class(code, patch_range, fut_name)
    if surrounding_class:
        surrounding_class_nb_lines = len(surrounding_class.split("\n"))
        if surrounding_class_nb_lines > 30:
            print(f"Surrounding class is too long ({surrounding_class_nb_lines} lines), omitting it")
            surrounding_class = None
    
    return CodeContext(fut_code, fut_name, surrounding_class, tests)
