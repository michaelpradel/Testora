from os.path import join
from unidiff import PatchSet
from buggpt.Constants import defects4j_root_path
from buggpt.util.Defects4J import get_project_root_dir


def get_patch(project_id, bug_id, version):
    # find the modified parts of the code
    patch_path = join(defects4j_root_path,
                      f"framework/projects/{project_id}/patches/{bug_id}.src.patch")

    # note: patches introduce the bug into the fixed version (i.e., "wrong" way around)
    patch = PatchSet.from_filename(patch_path)

    # checking assumptions
    assert len(patch.added_files) == 0, "Patch contains added files"
    assert len(patch.removed_files) == 0, "Patch contains removed files"
    assert len(patch.modified_files) > 0, "Patch contains no modified files"

    for modified_file in patch.modified_files:
        assert modified_file.is_modified_file, "Patch contains a file that is not modified"
        assert not modified_file.is_rename, "Patch contains a renamed file"

    return patch


def get_hunk_windows_and_patch(project_id, bug_id, version="b"):
    patch = get_patch(project_id, bug_id, version)
    project_root_dir = get_project_root_dir(project_id, bug_id, version)
    code = ""
    nb_extra_lines = 10  # added both before and after the hunk
    for modified_file in patch.modified_files:
        modified_file_path = join(project_root_dir, modified_file.path)
        with open(modified_file_path, "r") as f:
            lines = f.readlines()

        # 1) find line ranges to extract
        ranges = []
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

            start_line = max(1, start_line - nb_extra_lines)
            end_line = min(len(lines), end_line + nb_extra_lines)
            ranges.append([start_line, end_line])

        # 2) merge overlapping ranges
        merged_ranges = []
        for start_line, end_line in sorted(ranges):
            if not merged_ranges or merged_ranges[-1][1] < start_line:
                merged_ranges.append([start_line, end_line])
            else:
                merged_ranges[-1][1] = max(merged_ranges[-1][1], end_line)

        # 3) extract code
        for start_line, end_line in merged_ranges:
            code += f"File: {modified_file.path}. Lines: {start_line}-{end_line}\n"
            code += "".join(lines[start_line-1:end_line])+"\n"

    return code, patch


def get_full_file_and_patch(project_id, bug_id, version="b"):
    patch = get_patch(project_id, bug_id, version)
    project_root_dir = get_project_root_dir(project_id, bug_id, version)
    code = ""
    for modified_file in patch.modified_files:
        modified_file_path = join(project_root_dir, modified_file.path)

        with open(modified_file_path, "r") as f:
            lines = f.readlines()
            code += f"File: {modified_file.path}:\n"
            code += "".join(lines)
            code += "\n"
            # TODO unfinished; need a way to reduce the code to a reasonable length
            print(
                f"XXXX: {modified_file_path} has {len(lines)} lines = {len(''.join(lines))} characters")

    return code, patch
