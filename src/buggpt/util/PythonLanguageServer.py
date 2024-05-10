from multilspy import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger
from datetime import datetime

# temporarily copy our test code into the project


# start language server
config = MultilspyConfig.from_dict({"code_language": "python"})
logger = MultilspyLogger()
start_indexing = datetime.now()
lsp = SyncLanguageServer.create(
    config, logger, "/home/m/research/collabs/BugGPT/data/repos/pandas")
print(f"Indexing time: {datetime.now() - start_indexing}")



with lsp.start_server():
    # result = lsp.request_definition(
    #     # Filename of location where request is being made
    #     "src/buggpt/RegressionFinder.py",
    #     298,  # line number of symbol for which request is being made
    #     42  # column number of symbol for which request is being made
    # )
    # result = lsp.request_hover("src/buggpt/RegressionFinder.py", 298, 4)
    # result = lsp.request_hover("my_code/test.py", 1, 15)
    result = lsp.request_hover("pandas/core/reshape/pivot.py", 135, 15)
    print(result)
