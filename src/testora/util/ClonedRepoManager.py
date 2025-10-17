from dataclasses import dataclass
import json
from os.path import exists
from pathlib import Path
import shutil
import subprocess
from typing import List
from git import Repo

from testora.util.PythonLanguageServer import PythonLanguageServer


@dataclass
class ClonedRepo:
    repo: Repo
    container_name: str
    language_server: PythonLanguageServer


class ClonedRepoManager:
    nb_clones = 3

    def __init__(self, pool_dir, repo_name, repo_id, container_base_name, module_name):
        self.pool_dir = pool_dir
        self.repo_name = repo_name
        self.repo_id = repo_id
        self.container_base_name = container_base_name
        self.module_name = module_name

        self.clone_state_file = f"{self.pool_dir}/clone_state.json"
        self._read_clone_state()

        self.usage_order: List[str] = [f"clone{i}" for i in range(
            1, self.nb_clones + 1)]  # last = last used

        self._reset_and_clean_all_clones()

        # start one language server for each clone
        self.clone_id_to_language_server = {}
        for i in range(1, self.nb_clones + 1):
            server = PythonLanguageServer(
                f"{self.pool_dir}/clone{i}/{self.repo_name}")
            self.clone_id_to_language_server[f"clone{i}"] = server

    def _read_clone_state(self):
        if not exists(self.clone_state_file):
            self.clone_id_to_state = {
                f"clone{i}": {"commit": "unknown", "container_name": f"{self.container_base_name}{i}"} for i in range(1, self.nb_clones + 1)}
            return

        with open(self.clone_state_file, "r") as f:
            self.clone_id_to_state = json.load(f)

        assert len(self.clone_id_to_state) == self.nb_clones

    def _write_clone_state(self):
        assert len(self.clone_id_to_state) == self.nb_clones
        with open(self.clone_state_file, "w") as f:
            json.dump(self.clone_id_to_state, f)

    def _reset_and_clean_all_clones(self):
        for clone_id, _ in self.clone_id_to_state.items():
            cloned_repo_dir = f"{self.pool_dir}/{clone_id}/{self.repo_name}"
            cloned_repo = Repo(cloned_repo_dir)
            cloned_repo.git.rm('--cached', '-rf', '.')
            cloned_repo.git.reset('--hard')
            cloned_repo.git.clean('-f', '-d')
            origin = cloned_repo.remotes.origin
            origin.fetch()

    def _get_least_recently_used_clone_id(self) -> str:
        return self.usage_order[0]

    def _have_used_clone_id(self, clone_id: str):
        self.usage_order.remove(clone_id)
        self.usage_order.append(clone_id)

    def _safe_checkout(self, cloned_repo: Repo, commit: str):
        try:
            cloned_repo.git.checkout(commit)
            cloned_repo.git.submodule('update', '--init', '--recursive')
        except Exception:
            if commit == "main":
                self._safe_checkout(cloned_repo, "master")
            elif commit == "master":
                self._safe_checkout(cloned_repo, "dev")
            else:
                cloned_repo.git.rm('--cached', '-rf', '.')
                cloned_repo.git.reset('--hard')
                cloned_repo.git.clean('-f', '-d')
                origin = cloned_repo.remotes.origin
                origin.fetch()
                try:
                    cloned_repo.git.checkout(commit)
                except Exception:
                    # we get here when submodules are in a strange state
                    self._remove_and_reinit_submodules(cloned_repo, commit)

    def _remove_and_reinit_submodules(self, cloned_repo: Repo, commit: str):
        # 1) de-initialize all submodules
        cloned_repo.git.submodule('deinit', '-f', '--all')

        # 2) remove all submodule working trees
        root = Path(cloned_repo.working_dir)
        ls_output = subprocess.run(
            ["git", "ls-files", "-s"], capture_output=True, text=True, check=True
        ).stdout.splitlines()
        for line in ls_output:
            parts = line.split()
            if len(parts) >= 4 and parts[0] == "160000":
                path = " ".join(parts[3:])
                shutil.rmtree(root / path, ignore_errors=True)

        # 3) remove all submodule git metadata under .git/modules
        modules_dir = root / ".git" / "modules"
        if modules_dir.exists():
            for child in modules_dir.iterdir():
                shutil.rmtree(child, ignore_errors=True)

        # 4) checkout the desired commit
        cloned_repo.git.checkout(commit)

        # 5) re-initialize submodules recursively
        cloned_repo.git.submodule('update', '--init', '--recursive')

    def get_cloned_repo(self, commit) -> ClonedRepo:
        # reuse existing clone if possible
        for clone_id, state in self.clone_id_to_state.items():
            if state["commit"] == commit:
                self._have_used_clone_id(clone_id)
                cloned_repo_dir = f"{self.pool_dir}/{clone_id}/{self.repo_name}"

                return ClonedRepo(Repo(cloned_repo_dir),
                                  state["container_name"],
                                  self.clone_id_to_language_server[clone_id])

        # checkout desired commit
        clone_id = self._get_least_recently_used_clone_id()
        cloned_repo_dir = f"{self.pool_dir}/{clone_id}/{self.repo_name}"
        cloned_repo = Repo(cloned_repo_dir)
        self._safe_checkout(cloned_repo, commit)

        # update clone state
        state = self.clone_id_to_state[clone_id]
        state["commit"] = commit
        self.clone_id_to_state[clone_id] = state
        self._write_clone_state()
        self._have_used_clone_id(clone_id)

        return ClonedRepo(cloned_repo,
                          state["container_name"],
                          self.clone_id_to_language_server)
