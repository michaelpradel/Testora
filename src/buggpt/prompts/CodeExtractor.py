from os.path import join
import subprocess
from tempfile import TemporaryDirectory
from dataclasses import dataclass
from unidiff import PatchSet
from buggpt.Constants import defects4j_root_path


def get_changed_code_and_patch(project_id, bug_id, version="b"):
    code = ""

    with TemporaryDirectory() as tmp_dir:
        # checkout buggy or fixed version
        cmd = f"defects4j checkout -p {project_id} -v {bug_id}{version} -w {tmp_dir}"

        result = subprocess.run(
            cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(result.stdout)
            raise RuntimeError(
                f"Failed to checkout version of {project_id} {bug_id}")

        # find the modified parts of the code
        patch_path = join(defects4j_root_path,
                          f"framework/projects/{project_id}/patches/{bug_id}.src.patch")

        # note: patches introduce the bug into the fixed version (i.e., "wrong" way around)
        patch = PatchSet.from_filename(patch_path)

        assert len(patch.added_files) == 0, "Patch contains added files"
        assert len(patch.removed_files) == 0, "Patch contains removed files"
        assert len(patch.modified_files) > 0, "Patch contains no modified files"

        for modified_file in patch.modified_files:
            assert modified_file.is_modified_file, "Patch contains a file that is not modified"
            assert not modified_file.is_rename, "Patch contains a renamed file"

            for hunk in modified_file:
                if version == "b":
                    start_line = hunk.target_start
                    end_line = hunk.target_start + hunk.target_length - 1
                elif version == "f":
                    start_line = hunk.source_start
                    end_line = hunk.source_start + hunk.source_length - 1
                else:
                    raise ValueError(
                        f"Invalid version (must be 'b' or 'f'): {version}")

                code += f"File: {modified_file.path}. Lines: {start_line}-{end_line}\n"

                modified_file_path = join(tmp_dir, modified_file.path)

                with open(modified_file_path, "r") as f:
                    lines = f.readlines()
                    code += "".join(lines[start_line-1:end_line])+"\n"

    return code, patch
