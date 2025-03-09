"""
Global counters of various events (mostly for debugging purposes).
"""

import atexit

attempted_target_bugs = 0
attempted_hypotheses = 0

parsable_tests = 0
unparsable_tests = 0

test_execution_attempts = 0
test_passes = 0
test_failures = 0
test_errors = 0
test_crashes = 0
test_other_results = 0


def print_stats():
    print("\n\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("Stats:")
    for k, v in globals().items():
        if k.startswith("__") or callable(v) or type(v) != int:
            continue
        print(f"  {k}: {v}")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")        

atexit.register(print_stats)