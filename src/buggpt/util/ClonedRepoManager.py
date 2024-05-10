import json
from os.path import exists
from typing import List
from git import Repo


class ClonedRepoManager:
    nb_clones = 3

    def __init__(self, pool_dir, repo_name, container_base_name):
        self.pool_dir = pool_dir
        self.repo_name = repo_name
        self.container_base_name = container_base_name

        self.clone_state_file = f"{self.pool_dir}/clone_state.json"
        self._read_clone_state()

        self.usage_order: List[str] = [f"clone{i}" for i in range(
            1, self.nb_clones + 1)]  # last = last used

        self._hard_reset_all_clones()

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

    def _hard_reset_all_clones(self):
        for clone_id, _ in self.clone_id_to_state.items():
            cloned_repo_dir = f"{self.pool_dir}/{clone_id}/{self.repo_name}"
            cloned_repo = Repo(cloned_repo_dir)
            cloned_repo.git.reset('--hard')

    def _get_least_recently_used_clone_id(self) -> str:
        return self.usage_order[0]

    def _have_used_clone_id(self, clone_id: str):
        self.usage_order.remove(clone_id)
        self.usage_order.append(clone_id)

    def get_cloned_repo_and_container(self, commit):
        # reuse existing clone if possible
        for clone_id, state in self.clone_id_to_state.items():
            if state["commit"] == commit:
                self._have_used_clone_id(clone_id)
                cloned_repo_dir = f"{self.pool_dir}/{clone_id}/{self.repo_name}"
                return Repo(cloned_repo_dir), state["container_name"]

        # checkout desired commit
        clone_id = self._get_least_recently_used_clone_id()
        cloned_repo_dir = f"{self.pool_dir}/{clone_id}/{self.repo_name}"
        cloned_repo = Repo(cloned_repo_dir)
        cloned_repo.git.checkout(commit)

        # update clone state
        state = self.clone_id_to_state[clone_id]
        state["commit"] = commit
        self.clone_id_to_state[clone_id] = state
        self._write_clone_state()

        return cloned_repo, state["container_name"]
