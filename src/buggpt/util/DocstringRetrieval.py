import os
from buggpt.util.ClonedRepoManager import ClonedRepo
from buggpt.util.PythonCodeUtil import get_locations_of_calls


def retrieve_relevant_docstrings(cloned_repo: ClonedRepo, code: str) -> str:
    # copy code into project
    code_dir = f"{cloned_repo.repo.working_dir}/buggpt_code/"
    os.makedirs(code_dir, exist_ok=True)
    code_path = f"{code_dir}/test.py"
    with open(code_path, "w") as f:
        f.write(code)

    # find all calls in the code
    call_locations = get_locations_of_calls(code)

    # query language server for hover text for each call
    server = cloned_repo.language_server
    docs = []
    for call_location in call_locations:
        line = call_location.start.line - 1  # LSP lines are 0-based
        column = call_location.start.column
        doc = server.get_hover_text(code_path, line, column)
        docs.append(doc)

    # enforce limits: max 2000 chars per docstring, max 6000 chars overall
    result = ""
    for doc in docs:
        result += "-------"
        result += doc[:2000]

    return result[:6000]
