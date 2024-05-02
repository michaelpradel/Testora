import subprocess


class ClonedRepo:
    def __init__(self, repo_path):
        self.repo_path = repo_path

    def get_latest(self):
        

    def checkout(self, commit_hash):
        cmd = f"git checkout {commit_hash}"
        result = subprocess.run(
            cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, text=True, cwd=self.repo_path)
        if result.returncode != 0:
            print(result.stdout)
            raise RuntimeError(
                f"Failed to checkout {commit_hash} in {self.repo_path}")
        print(f"Checked out {commit_hash} in {self.repo_path}")
