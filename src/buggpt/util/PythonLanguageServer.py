from multilspy import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger
from pathlib import Path


class PythonLanguageServer:
    def __init__(self, repo_path):
        config = MultilspyConfig.from_dict({"code_language": "python"})
        logger = MultilspyLogger()
        self.lsp = SyncLanguageServer.create(
            config, logger, repo_path)

    def get_hover_text(self, file_path, line, column):
        with self.lsp.start_server():
            raw_result = self.lsp.request_hover(file_path, line, column)
            if type(raw_result) == dict and "contents" in raw_result:
                return raw_result["contents"]["value"]
            else:
                return ""


# for testing
if __name__ == "__main__":
    server = PythonLanguageServer("/home/m/research/collabs/BugGPT/data/repos/pandas/")
    r = server.get_hover_text("/home/m/research/collabs/BugGPT/data/repos/pandas/buggpt_code/test.py", 2, 23)
    print(r)
