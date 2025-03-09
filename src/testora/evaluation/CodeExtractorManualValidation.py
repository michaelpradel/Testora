from testora.prompts.CodeExtractor import get_hunk_windows_and_patch as get_code_and_patch
from testora.util.Defects4J import get_target_bugs

target_bugs = get_target_bugs(
    "./data/defects4j_bugs_shuffled_March_7_2024_subset10.csv")

for project_id, bug_id in target_bugs:
    input("Press Enter to see next bug...")
    print("==========================================\n")
    print(f"{project_id} {bug_id}:\n")
    code, patch = get_code_and_patch(project_id, bug_id, "b")
    print(code)
    input("Press Enter to see the patch...")
    print(patch)
