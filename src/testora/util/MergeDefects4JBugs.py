from os.path import join
from csv import reader
from random import shuffle
from testora.Constants import defects4j_root_path

active_bugs_paths = [
    "framework/projects/Mockito/active-bugs.csv",
    "framework/projects/Closure/active-bugs.csv",
    "framework/projects/Math/active-bugs.csv",
    "framework/projects/Compress/active-bugs.csv",
    "framework/projects/Collections/active-bugs.csv",
    "framework/projects/JacksonDatabind/active-bugs.csv",
    "framework/projects/JacksonCore/active-bugs.csv",
    "framework/projects/Jsoup/active-bugs.csv",
    "framework/projects/JxPath/active-bugs.csv",
    "framework/projects/Gson/active-bugs.csv",
    "framework/projects/Codec/active-bugs.csv",
    "framework/projects/Cli/active-bugs.csv",
    "framework/projects/Lang/active-bugs.csv",
    "framework/projects/Chart/active-bugs.csv",
    "framework/projects/Csv/active-bugs.csv",
    "framework/projects/Time/active-bugs.csv",
    "framework/projects/JacksonXml/active-bugs.csv",
]

out_lines = []
for active_bug_path in active_bugs_paths:
    active_bug_path = join(defects4j_root_path, active_bug_path)
    project_id = active_bug_path.split("/")[-2]
    with open(active_bug_path, "r") as in_file:
        r = reader(in_file)
        next(r)
        for row in r:
            out_lines.append(f"{project_id},{','.join(row)}\n")

shuffle(out_lines)

target_file = "data/defects4j_bugs_shuffled.csv"

with open(target_file, "w") as out_file:
    out_file.write(
        "project.id,bug.id,revision.id.buggy,revision.id.fixed,report.id,report.url\n")
    for l in out_lines:
        out_file.write(l)
