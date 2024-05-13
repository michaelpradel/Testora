from multilspy import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger


class PythonLanguageServer:
    def __init__(self, repo_path):
        config = MultilspyConfig.from_dict({"code_language": "python"})
        logger = MultilspyLogger()
        self.lsp = SyncLanguageServer.create(
            config, logger, repo_path)
        self.lsp.start_server()

    def get_hover_text(self, line, column, file_name="buggpt_code/test.py"):
        raw_result = self.lsp.request_hover(file_name, line, column)
        if type(raw_result) == dict and "contents" in raw_result:
            return raw_result["contents"]["value"]
        else:
            return ""
