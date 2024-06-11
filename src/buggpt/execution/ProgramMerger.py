import ast
from textwrap import dedent
import re

from buggpt.util.Exceptions import BugGPTException


def merge_programs(programs):
    function_def_snippets = []
    for program_idx, program in enumerate(programs):
        # Parse the snippet into an AST node
        try:
            parsed_snippet = ast.parse(dedent(program))
        except Exception as _:
            function_def_snippets.append(
                f"def program_{program_idx}():\n    pass # Couldn't parse generated test")
            continue

        # Create a function definition for the parsed snippet
        function_def = ast.FunctionDef(
            name=f"program_{program_idx}",
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[]
            ),
            body=parsed_snippet.body,
            decorator_list=[],
            returns=None
        )

        # Print function definitions to string
        code = ast.unparse(ast.fix_missing_locations(function_def))
        function_def_snippets.append(code)

    result = "import sys\nimport traceback\nimport io\n\n"
    for function_def_snippet in function_def_snippets:
        result += function_def_snippet + "\n\n"

    for fct_idx in range(len(function_def_snippets)):
        result += f"""print('XXXXX Program {fct_idx} starting XXXXX')
try:
    my_stdout = io.StringIO()
    my_stderr = io.StringIO()
    sys.stdout = my_stdout
    sys.stderr = my_stderr
    program_{fct_idx}()
except BaseException as e:
    details = traceback.format_exc()
    print(details, file=my_stderr)
finally:
    sys.stdout.flush()
    sys.stderr.flush()
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print(my_stdout.getvalue(), end="")
    print(my_stderr.getvalue(), end="")
print('XXXXX Program {fct_idx} done XXXXX')
"""

    return result


program_start_pattern = re.compile(r"XXXXX Program (\d+) starting XXXXX")
program_end_pattern = re.compile(r"XXXXX Program (\d+) done XXXXX")


def separate_outputs(output):
    in_program = None
    current_output = None
    result = []
    for line in output.split("\n"):
        program_start_match = program_start_pattern.match(line)
        if program_start_match:
            in_program = int(program_start_match.group(1))
            current_output = ""
            continue
        program_end_match = program_end_pattern.match(line)
        if program_end_match:
            program_nb = int(program_end_match.group(1))
            if program_nb != in_program:
                raise BugGPTException(f"Unexpected output of merged tests:\n{str(output)}")
            in_program = None
            result.append(current_output)
        elif in_program is not None:
            current_output += line + "\n"
    return result


# for testing
if __name__ == "__main__":
    program1 = """
import pandas as pd

df = pd.DataFrame({'A': [1.112, 3.456, 7.890], 'B': [9.876, 5.432, 1.234]})
rounded_df = df.round(1)
print(rounded_df)
"""

    program2 = """
import pandas as pd

series_strings = pd.Series(['a', 'b', 'c'])
# This will result in an error as rounding is not applicable to strings
try:
    rounded_strings = series_strings.round(2)
    print(rounded_strings)
except TypeError as e:
    print(f"Error: {e}")
"""

    program3 = """
import pandas as pd

# Normal usage scenario
data = [1.234, 2.345, 3.456]
ser = pd.Series(data)
rounded_ser = ser.round(decimals=1)
print(rounded_ser)

# Normal usage scenario
ser = pd.Series([-1.234, -2.345, -3.456])
rounded_ser = ser.round()
print(rounded_ser)

# Normal usage scenario
ser = pd.Series([5.678, 6.789, 7.890])
rounded_ser = ser.round(decimals=2)
print(rounded_ser)

# Normal usage scenario
ser = pd.Series([1000, 2000, 3000])
rounded_ser = ser.round(decimals=-2)
print(rounded_ser)
"""

    program4 = """
import pandas as pd
import numpy as np

data = np.array([1.234, 2.345, 3.456])
ser = pd.Series(data)
print(ser)
r = ser / zero
print(r)
"""

    result = merge_programs([program1, program2, program3, program4])
    print(result)

    output = """
XXXXX Program 0 starting XXXXX
     A    B
0  1.1  9.9
1  3.5  5.4
2  7.9  1.2
XXXXX Program 0 done XXXXX
XXXXX Program 1 starting XXXXX
0    a
1    b
2    c
dtype: object
XXXXX Program 1 done XXXXX
XXXXX Program 2 starting XXXXX
0    1.2
1    2.3
2    3.5
dtype: float64
0   -1.0
1   -2.0
2   -3.0
dtype: float64
0    5.68
1    6.79
2    7.89
dtype: float64
0    1000
1    2000
2    3000
dtype: int64
XXXXX Program 2 done XXXXX
XXXXX Program 3 starting XXXXX
0    1.234
1    2.345
2    3.456
dtype: float64
Traceback (most recent call last):
  File "/tmp/TestRemoveMe.py", line 74, in <module>
    program_3()
  File "/tmp/TestRemoveMe.py", line 41, in program_3
    r = ser / zero
              ^^^^
NameError: name 'zero' is not defined

XXXXX Program 3 done XXXXX
"""

    split_outputs = separate_outputs(output)
    for idx, split_output in enumerate(split_outputs):
        print(f"Program {idx} output:")
        print(split_output)
        print()
