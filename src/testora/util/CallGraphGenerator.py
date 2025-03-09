"""
The following is adapted from https://github.com/r2e-project/r2e.

This file is a wrapper of the pycg, a practical python call graph generator. Please refer to:
1. https://github.com/vitsalis/PyCG
2. https://pypi.org/project/pycg/

Vitalis Salis, Thodoris Sotiropoulos, Panos Louridas, Diomidis Spinellis and 
Dimitris Mitropoulos. PyCG: Practical Call Graph Generation in Python. 
In 43rd International Conference on Software Engineering, ICSE '21, 25–28 May 2021.
"""

import os
import sys
import shutil

try:
    import PyCG as pycg

    sys.modules["pycg"] = pycg
except ImportError as e:
    print(f"Failed to import PyCG: {e}")


from pycg import formats  # type: ignore
from pycg.pycg import CallGraphGenerator as CallGraphGeneratorPyCG  # type: ignore


class CallGraphGenerator:
    @staticmethod
    def construct_call_graph(repo_path: str, max_iter: int = -1) -> dict:
        entry_points = []
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".py"):
                    entry_points.append(
                        os.path.abspath(os.path.join(root, file)))

        cg_generator = CallGraphGeneratorPyCG(
            entry_points, repo_path, max_iter, operation="call-graph"
        )
        cg_generator.analyze()
        call_graph = formats.Simple(cg_generator).generate()

        shutil.rmtree(repo_path)
        return call_graph


if __name__ == "__main__":
    call_graph = CallGraphGenerator.construct_call_graph(".")
    print(call_graph)