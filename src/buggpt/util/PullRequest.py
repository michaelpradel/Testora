from unidiff import PatchSet
import urllib.request

from buggpt.util.PythonCodeUtil import equal_modulo_docstrings, extract_target_function_by_range, get_name_of_defined_function
from buggpt import Config


class PullRequest:
    def __init__(self, github_pr, github_repo, cloned_repo_manager):
        self.github_pr = github_pr
        self.cloned_repo_manager = cloned_repo_manager
        self.number = github_pr.number
        self.title = github_pr.title
        self.post_commit = github_pr.merge_commit_sha
        self.parents = github_repo.get_commit(self.post_commit).parents
        self.pre_commit = self.parents[0].sha

        self._pr_url_to_patch()
        self._get_non_test_modified_files()
        self._get_modified_lines()

    def _pr_url_to_patch(self):
        diff_url = self.github_pr.html_url + ".diff"
        diff = urllib.request.urlopen(diff_url)
        encoding = diff.headers.get_charsets()[0]
        self.patch = PatchSet(diff, encoding=encoding)

    def _get_non_test_modified_files(self):
        module_name = self.cloned_repo_manager.module_name

        # Python files only
        modified_python_files = [
            f for f in self.patch.modified_files if f.path.endswith(".py") or f.path.endswith(".pyx")]
        self.non_test_modified_python_files = [
            f.path for f in modified_python_files if "test" not in f.path and (f.path.startswith(module_name) or f.path.startswith(f"src/{module_name}"))]

        # Python and other PLs
        modified_code_files = [
            f for f in self.patch.modified_files if
            f.path.endswith(".py") or
            f.path.endswith(".pyx") or
            f.path.endswith(".c") or
            f.path.endswith(".cpp") or
            f.path.endswith(".h")
        ]
        self.non_test_modified_code_files = [
            f.path for f in modified_code_files if "test" not in f.path and (f.path.startswith(module_name) or f.path.startswith(f"src/{module_name}"))]

    def get_modified_files(self):
        if Config.code_change_pl == "python":
            return self.non_test_modified_python_files
        elif Config.code_change_pl == "all":
            return self.non_test_modified_code_files

    def has_non_comment_change(self):
        if Config.code_change_pl == "all":
            return len(self.non_test_modified_code_files) > 0

        pre_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.pre_commit)
        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)

        self.files_with_non_comment_changes = []
        for modified_file in self.non_test_modified_python_files:
            with open(f"{pre_commit_cloned_repo.repo.working_dir}/{modified_file.path}", "r") as f:
                old_file_content = f.read()
            with open(f"{post_commit_cloned_repo.repo.working_dir}/{modified_file.path}", "r") as f:
                new_file_content = f.read()
            if not equal_modulo_docstrings(old_file_content, new_file_content):
                self.files_with_non_comment_changes.append(modified_file.path)

        self.files_with_non_comment_changes = list(dict.fromkeys(
            self.files_with_non_comment_changes))  # turn into set while preserving order
        return len(self.files_with_non_comment_changes) > 0

    def _get_relevant_changed_files(self) -> list[str]:
        if Config.code_change_pl == "python":
            return self.files_with_non_comment_changes
        elif Config.code_change_pl == "all":
            return self.non_test_modified_code_files
        else:
            raise Exception(
                f"Unexpected configuration value: {Config.code_change_pl}")

    def get_filtered_diff(self):
        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)

        diff_parts = []
        for file_path in self._get_relevant_changed_files():
            raw_diff = post_commit_cloned_repo.repo.git.diff(
                self.pre_commit, self.post_commit, file_path)
            diff_parts.append(raw_diff)

        return "\n\n".join(diff_parts)

    def get_full_diff(self):
        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)

        return post_commit_cloned_repo.repo.git.diff(self.pre_commit, self.post_commit)

    def get_changed_function_names(self):
        result = []

        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)

        for modified_file in self.patch.modified_files:
            if modified_file.path in self._get_relevant_changed_files():
                with open(f"{post_commit_cloned_repo.repo.working_dir}/{modified_file.path}", "r") as f:
                    new_file_content = f.read()

                module_name = modified_file.path.replace(
                    "/", ".").replace(".pyx", "").replace(".py", "")

                for hunk in modified_file:
                    start_line = hunk.target_start
                    end_line = hunk.target_start + hunk.target_length
                    patch_range = (start_line, end_line)
                    fct_code = extract_target_function_by_range(
                        new_file_content, patch_range)
                    if fct_code is not None:
                        fct_name = get_name_of_defined_function(fct_code)
                        if fct_name:
                            result.append(f"{module_name}.{fct_name}")

        result = list(dict.fromkeys(result))
        return result

    def _get_modified_lines(self):
        self.old_file_path_to_modified_lines = {}
        self.new_file_path_to_modified_lines = {}

        post_commit_cloned_repo = self.cloned_repo_manager.get_cloned_repo(
            self.post_commit)
        diff = post_commit_cloned_repo.repo.git.diff(
            self.pre_commit, self.post_commit)
        patch = PatchSet(diff)

        for patched_file in patch:
            for hunk in patched_file:
                for line in hunk:
                    if line.is_removed:
                        self.old_file_path_to_modified_lines.setdefault(
                            patched_file.path, []).append(line.target_line_no)
                    elif line.is_added:
                        self.new_file_path_to_modified_lines.setdefault(
                            patched_file.path, []).append(line.source_line_no)
