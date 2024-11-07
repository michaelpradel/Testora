from collections import Counter
import fnmatch
from os.path import exists
from os import listdir, getcwd
import json
from typing import Dict, List
import mysql.connector
import argparse
from pathlib import Path
from buggpt.evaluation.ResultsManager import current_results, add_result

config = {
    "user": "user_name",
    "host": "sql141.your-server.de",
    "database": "regression_finder_db"
}
with open(".db_token", "r") as f:
    config["password"] = f.read().strip()

with open(".worker_id", "r") as f:
    my_worker_id = f.read().strip()


def connect_and_do(func):
    try:
        conn = None
        conn = mysql.connector.connect(**config)
        print("Database connection established")
        cursor = conn.cursor()

        result = func(conn, cursor)

        conn.commit()
        print("Query executed successfully")
        return result
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if conn.is_connected():
            conn.rollback()
            print("Transaction rolled back")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection is closed")


def write_tasks(project_name, pr_nbs: List[int]):
    def inner(connection, cursor):
        insert_query = "INSERT INTO tasks (project, pr) VALUES (%s, %s)"
        for pr_nb in pr_nbs:
            print(f"Inserting task for PR {pr_nb} of {project_name}")
            cursor.execute(insert_query, (project_name, pr_nb))

    connect_and_do(inner)


def fetch_task():
    def inner(connection, cursor):
        connection.start_transaction()

        # check if there's already an unfinished task assigned to this container; if yes, work on it
        select_query = "SELECT project, pr FROM tasks WHERE worker=%s AND result IS NULL"
        cursor.execute(select_query, (my_worker_id,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

        # otherwise, fetch a new task and mark it as assigned to this container
        target_project_file = Path(".target_project")
        if target_project_file.exists():
            # if we have a target project, only fetch tasks from that project
            with open(target_project_file, "r") as f:
                target_project = f.read().strip()
            select_query = "SELECT project, pr FROM tasks WHERE worker IS NULL AND project=%s LIMIT 1"
            cursor.execute(select_query, (target_project,))
        else:
            select_query = "SELECT project, pr FROM tasks WHERE worker IS NULL LIMIT 1"
            cursor.execute(select_query)

        row = cursor.fetchone()

        if row:
            project, pr = row[0], row[1]
            update_query = "UPDATE tasks SET worker=%s WHERE project=%s AND pr=%s AND worker IS NULL"
            cursor.execute(update_query, (my_worker_id, project, pr))
            connection.commit()
            return project, pr
        else:
            print("No task found.")
            return None, None

    return connect_and_do(inner)


# def fetch_results(existing_result_files: List[str]) -> Dict[str, str]:
#     existing_results = [f.replace("results_", "").replace(
#         ".json", "") for f in existing_result_files]

#     # TODO: update

#     # 1) find results we have not yet downloaded
#     try:
#         conn = mysql.connector.connect(**config)
#         print("Database connection established!")

#         cursor = conn.cursor()
#         conn.start_transaction()

#         select_query = "SELECT name FROM experiments WHERE result is not NULL"
#         cursor.execute(select_query)
#         rows = cursor.fetchall()
#         names_to_download: List[str] = [row[0]
#                                         for row in rows if row[0] not in existing_results]
#     except mysql.connector.Error as err:
#         print(f"Error: {err}")
#         if conn.is_connected():
#             conn.rollback()
#             print("Transaction rolled back")

#     finally:
#         if conn.is_connected():
#             cursor.close()
#             conn.close()
#             print("MySQL connection is closed")

#     # 2) download new results
#     name_to_result = {}
#     for name_to_download in names_to_download:
#         print(f"Downloading result for {name_to_download}")
#         try:
#             conn = mysql.connector.connect(**config)
#             print("Database connection established!")

#             cursor = conn.cursor()
#             conn.start_transaction()

#             select_query = "SELECT result FROM experiments WHERE name=%s"
#             cursor.execute(select_query, (name_to_download,))
#             rows = cursor.fetchall()
#             name_to_result[name_to_download] = rows[0][0]
#         except mysql.connector.Error as err:
#             print(f"Error: {err}")
#             if conn.is_connected():
#                 conn.rollback()
#                 print("Transaction rolled back")

#         finally:
#             if conn.is_connected():
#                 cursor.close()
#                 conn.close()
#                 print("MySQL connection is closed")

#     return name_to_result


def sort_results():
    all_files = listdir(getcwd())
    log_files = [f for f in all_files if fnmatch.fnmatch(f, "results_*.json")]

    log_file_to_timestamp = {}
    for log_file in log_files:
        with open(log_file) as f:
            events = json.load(f)
        last_timestamp = events[-1]["timestamp"]
        log_file_to_timestamp[log_file] = last_timestamp

    sorted_files = sorted(log_file_to_timestamp.items(), key=lambda x: x[1])
    print("Log files (oldest to newest, by last timestamp):")
    for log_file, timestamp in sorted_files:
        print(f"{log_file} -- ({timestamp})")


def show_unfinished_tasks():
    # find unassigned tasks
    try:
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        cursor = conn.cursor()
        conn.start_transaction()
        select_query = "SELECT name, task FROM experiments WHERE worker IS NULL"
        cursor.execute(select_query)
        rows = cursor.fetchall()
        for row in rows:
            print(f"Not assigned to any worker yet: {row[0]}")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if conn.is_connected():
            conn.rollback()
            print("Transaction rolled back")

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection is closed")

    # find assigned tasks that are not finished
    try:
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        cursor = conn.cursor()
        conn.start_transaction()
        select_query = "SELECT name, task, worker FROM experiments WHERE worker IS NOT NULL AND result IS NULL"
        cursor.execute(select_query)
        rows = cursor.fetchall()
        for row in rows:
            print(f"Assigned to worker {row[2]} but not finished: {row[0]}")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if conn.is_connected():
            conn.rollback()
            print("Transaction rolled back")

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection is closed")


def find_existing_result_files():
    all_files = listdir(getcwd())
    log_files = [f for f in all_files if fnmatch.fnmatch(f, "results_*.json")]
    return log_files


def show_status():
    def inner(connection, cursor):
        def count_per_project(query):
            project_to_count = Counter()
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                project_to_count[row[0]] = row[1]
            return project_to_count

        count_all = """
            SELECT project, COUNT(*) AS total_count
            FROM tasks
            GROUP BY project;"""
        project_to_count_all = count_per_project(count_all)

        count_assigned = """
            SELECT project, COUNT(*) AS assigned_count
            FROM tasks
            WHERE worker IS NOT NULL AND result IS NULL
            GROUP BY project;"""
        project_to_count_assigned = count_per_project(count_assigned)

        count_unassigned = """
            SELECT project, COUNT(*) AS unassigned_count
            FROM tasks
            WHERE result IS NULL AND worker IS NULL
            GROUP BY project;"""
        project_to_count_unassigned = count_per_project(count_unassigned)

        count_done = """
            SELECT project, COUNT(*) AS done_count
            FROM tasks
            WHERE result IS NOT NULL
            GROUP BY project;"""
        project_to_count_done = count_per_project(count_done)

        print("############################")
        for project, total_count in project_to_count_all.items():
            assigned_count = project_to_count_assigned.get(project, 0)
            unassigned_count = project_to_count_unassigned.get(project, 0)
            done_count = project_to_count_done.get(project, 0)

            print(f"{project}: {done_count}/{total_count} done, {
                  assigned_count} assigned, {unassigned_count} unassigned")
        print("############################")

    connect_and_do(inner)


def fetch_results():
    def inner(connection, cursor):
        projects_query = "SELECT DISTINCT project FROM tasks"
        cursor.execute(projects_query)
        projects = [row[0] for row in cursor.fetchall()]

        project_to_prs_and_timestamps = current_results()
        print(f"Found {
              sum([len(rs) for _, rs in project_to_prs_and_timestamps.items()])} existing results")

        for project in projects:
            prs_and_timestamps = project_to_prs_and_timestamps[project]

            print(f"Fetching results for {project}")
            done_prs_and_timestamps_query = "SELECT pr, timestamp FROM tasks WHERE project=%s AND result IS NOT NULL"
            cursor.execute(done_prs_and_timestamps_query, (project,))
            done_prs_and_timestamps = [[str(row[0]), str(row[1])]
                                       for row in cursor.fetchall()]

            nb_new_results = 0
            for pr, timestamp in done_prs_and_timestamps:
                if [pr, timestamp] not in prs_and_timestamps:
                    select_query = "SELECT result FROM tasks WHERE project=%s AND pr=%s AND timestamp=%s"
                    cursor.execute(
                        select_query, (project, pr, timestamp))
                    result = cursor.fetchone()[0]
                    add_result(
                        project, pr, timestamp, result)
                    nb_new_results += 1

            print(f"Added {nb_new_results} new results for {project}")

    connect_and_do(inner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage experiments/tasks via MySQL database")
    # parser.add_argument("--fetch_results", action="store_true",
    #                     help="Fetch results for all finished tasks")
    # parser.add_argument("--sort_results", action="store_true",
    #                     help="Sort result files by last timestamp in log")
    # parser.add_argument("--show_unfinished", action="store_true",
    #                     help="Show tasks that are not assigned or finished yet")
    parser.add_argument("--status", action="store_true",
                        help="Show status of tasks")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch results of finished tasks")

    args = parser.parse_args()
    if args.status:
        show_status()
    elif args.fetch:
        fetch_results()

    # TODO update or remove:
    # if args.fetch_results:
    #     existing_result_files = find_existing_result_files()
    #     name_to_result = fetch_results(existing_result_files)
    #     for name, result in name_to_result.items():
    #         result = repair_result(name, result)
    #         out_file = f"results_{name}.json"
    #         if not exists(out_file):
    #             print(f"Write new result to file {out_file}")
    #             with open(out_file, "w") as f:
    #                 f.write(result)
    # elif args.sort_results:
    #     sort_results()
    # elif args.show_unfinished:
    #     show_unfinished_tasks()

    else:
        print("Nothing do to (use --fetch_results to fetch results)")
