from collections import Counter
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
            assigned = project_to_count_assigned.get(project, 0)
            unassigned = project_to_count_unassigned.get(project, 0)
            done = project_to_count_done.get(project, 0)

            print(f"""{project}:
  {done}/{total_count} done,
  {assigned} assigned,
  {unassigned} unassigned""")
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
    parser.add_argument("--status", action="store_true",
                        help="Show status of tasks")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch results of finished tasks")

    args = parser.parse_args()
    if args.status:
        show_status()
    elif args.fetch:
        fetch_results()

    else:
        print("Nothing do to (use --fetch_results to fetch results)")
