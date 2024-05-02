from typing import List


class PythonProject:
    def __init__(self, git_url, installation_commands):
        self.git_url = git_url
        self.installation_commands = installation_commands
        self.project_id = self.git_url.replace(
            "https://github.com/", "").replace(".git", "")
        self.name = self.project_id.split("/")[1]


pandas_project = PythonProject(
    git_url="https://github.com/pandas-dev/pandas.git",
    installation_commands=[
        "python -m pip install -r requirements-dev.txt",
        "python -m pip install -ve . --no-build-isolation --config-settings editable-verbose=true"
    ]
)
