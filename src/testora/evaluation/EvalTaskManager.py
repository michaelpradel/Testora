from collections import Counter
from typing import Dict, List
import mysql.connector
import argparse
from pathlib import Path
from testora.evaluation.ResultsManager import current_results, add_result
from testora.evaluation.TargetPRs import project_to_target_prs

classification_pr_nb = -23


def initialize():
    global config, my_worker_id

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


def write_tasks(project_name, pr_nbs: List[int], table_name):
    def inner(connection, cursor):
        insert_query = (
            f"INSERT INTO {table_name} (project, pr) "
            f"VALUES (%s, %s)"
        )
        for pr_nb in pr_nbs:
            print(f"Inserting task for PR {pr_nb} of {project_name}")
            cursor.execute(insert_query, (project_name, pr_nb))

    connect_and_do(inner)


def fetch_task(table_name="tasks"):
    def inner(connection, cursor):
        connection.start_transaction()

        # check if there's already an unfinished task assigned to this container; if yes, work on it
        select_query = (
            f"SELECT project, pr FROM {table_name} "
            f"WHERE worker=%s AND result IS NULL"
        )
        cursor.execute(select_query, (my_worker_id,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

        # otherwise, fetch a new task and mark it as assigned to this container
        target_project_file = Path(".target_project")
        with open(target_project_file, "r") as f:
            target_project = f.read().strip()
        select_query = (
            f"SELECT project, pr FROM {table_name} "
            f"WHERE worker IS NULL AND project=%s LIMIT 1"
        )
        cursor.execute(select_query, (target_project,))

        row = cursor.fetchone()

        if row:
            project, pr = row[0], row[1]
            update_query = (
                f"UPDATE {table_name} SET worker = %s "
                f"WHERE project = %s AND pr = %s AND worker IS NULL"
            )
            cursor.execute(update_query, (my_worker_id, project, pr))
            connection.commit()
            return project, pr
        else:
            print("No task found.")
            return None, None

    return connect_and_do(inner)


def write_results(project, pr, result, table_name="tasks"):
    def inner(connection, cursor):
        insert_query = f"UPDATE {table_name} SET result=%s WHERE project=%s AND pr=%s"
        cursor.execute(insert_query, (result, project, pr))

    connect_and_do(inner)


def show_status():
    def inner(connection, cursor):
        def count_per_project(query):
            project_to_count = Counter()
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                project_to_count[row[0]] = row[1]
            return project_to_count

        count_all = f"""
            SELECT project, COUNT(*) AS total_count
            FROM {table_name}
            GROUP BY project;"""
        project_to_count_all = count_per_project(count_all)

        count_assigned = f"""
            SELECT project, COUNT(*) AS assigned_count
            FROM {table_name}
            WHERE worker IS NOT NULL AND result IS NULL
            GROUP BY project;"""
        project_to_count_assigned = count_per_project(count_assigned)

        count_unassigned = f"""
            SELECT project, COUNT(*) AS unassigned_count
            FROM {table_name}
            WHERE result IS NULL AND worker IS NULL
            GROUP BY project;"""
        project_to_count_unassigned = count_per_project(count_unassigned)

        count_done = f"""
            SELECT project, COUNT(*) AS done_count
            FROM {table_name}
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


def fetch_results(is_classification):
    def inner(connection, cursor):
        projects_query = f"SELECT DISTINCT project FROM {table_name}"
        cursor.execute(projects_query)
        projects = [row[0] for row in cursor.fetchall()]

        project_to_prs_and_timestamps = current_results()
        nb_results = sum([len(rs)
                         for _, rs in project_to_prs_and_timestamps.items()])
        print(f"Found {nb_results} existing results")

        for project in projects:
            prs_and_timestamps = project_to_prs_and_timestamps[project]

            print(f"Fetching results for {project}")
            done_prs_and_timestamps_query = (
                f"SELECT pr, timestamp FROM {table_name} "
                f"WHERE project = %s AND result IS NOT NULL"
            )
            cursor.execute(done_prs_and_timestamps_query, (project,))
            done_prs_and_timestamps = [[str(row[0]), str(row[1])]
                                       for row in cursor.fetchall()]

            nb_new_results = 0
            for pr, timestamp in done_prs_and_timestamps:
                if [pr, timestamp] not in prs_and_timestamps:
                    select_query = (
                        f"SELECT result FROM {table_name} "
                        f"WHERE project = %s AND pr = %s AND timestamp = %s"
                    )
                    cursor.execute(
                        select_query, (project, pr, timestamp))
                    result = cursor.fetchone()[0]
                    add_result(
                        project, pr, timestamp, result, is_classification)
                    nb_new_results += 1

            print(f"Added {nb_new_results} new results for {project}")

    connect_and_do(inner)


def schedule_target_prs(project):
    if project == "all":
        for project in project_to_target_prs().keys():
            schedule_target_prs_for_project(project)
    else:
        schedule_target_prs_for_project(project)


def schedule_target_prs_for_project(project):
    target_pr_nbs = project_to_target_prs()[project]
    write_tasks(project, target_pr_nbs, table_name)


def schedule_classification_tasks():
    for project in project_to_target_prs().keys():
        write_tasks(project, [classification_pr_nb], table_name)


def remove_unfinished(project):
    if project == "all":
        for project in project_to_target_prs().keys():
            remove_unfinished_for_project(project)
    else:
        remove_unfinished_for_project(project)


def remove_unfinished_for_project(project):
    def inner(connection, cursor):
        delete_query = (
            f"DELETE FROM {table_name} "
            f"WHERE project = %s AND result IS NULL"
        )
        cursor.execute(delete_query, (project,))

    connect_and_do(inner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage experiments/tasks via MySQL database")
    parser.add_argument("--status", action="store_true",
                        help="Show status of tasks")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch results of finished tasks")
    parser.add_argument("--schedule", type=str,
                        help="Schedule target PRs of a specific project for another round of evaluation")
    parser.add_argument("--remove_unfinished", type=str,
                        help="Remove all unfinished tasks for a specific project")
    parser.add_argument("--classification", action="store_true",
                        help="Apply to classification tasks")

    args = parser.parse_args()

    initialize()

    table_name = "classification_tasks" if args.classification else "tasks"
    if args.status:
        show_status()
    elif args.fetch:
        fetch_results(args.classification)
    elif args.schedule:
        if args.classification:
            schedule_classification_tasks()
        else:
            schedule_target_prs(args.schedule)
    elif args.remove_unfinished:
        remove_unfinished(args.remove_unfinished)
    else:
        print("Must pass an argument.")
