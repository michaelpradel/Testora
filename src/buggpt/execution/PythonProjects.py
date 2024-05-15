class PythonProject:
    def __init__(self, git_url):
        self.git_url = git_url
        self.project_id = self.git_url.replace(
            "https://github.com/", "").replace(".git", "")
        self.name = self.project_id.split("/")[1]


pandas_project = PythonProject(
    git_url="https://github.com/pandas-dev/pandas.git"
)
