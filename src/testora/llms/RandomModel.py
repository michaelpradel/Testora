import json
from random import choice, randint


def query(prompt):
    # random decide to report a bug in 1 out of n cases
    n = 2
    if randint(1, n) == 1:
        # randomly decide where to report the bug
        code_lines = prompt.code.split("\n")
        selected_line = choice(code_lines)
        warnings = [{"code": [selected_line],
                     "description": "I've randomly decided that this is a bug",
                     "severity": 5}]
        return json.dumps({"warnings": warnings})
    else:
        return '{"warnings": []}'
