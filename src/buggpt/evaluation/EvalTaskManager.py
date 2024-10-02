import fnmatch
from os.path import exists
from os import listdir, getcwd
import json
from typing import Dict, List
import mysql.connector
import argparse
from pathlib import Path

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


def write_results(project, pr, result):
    def inner(connection, cursor):
        insert_query = "UPDATE tasks SET result=%s WHERE project=%s AND pr=%s"
        cursor.execute(insert_query, (result, project, pr))

    connect_and_do(inner)


def fetch_results(existing_result_files: List[str]) -> Dict[str, str]:
    existing_results = [f.replace("results_", "").replace(
        ".json", "") for f in existing_result_files]
    
    # TODO: update

    # 1) find results we have not yet downloaded
    try:
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        cursor = conn.cursor()
        conn.start_transaction()

        select_query = "SELECT name FROM experiments WHERE result is not NULL"
        cursor.execute(select_query)
        rows = cursor.fetchall()
        names_to_download: List[str] = [row[0]
                                        for row in rows if row[0] not in existing_results]
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

    # 2) download new results
    name_to_result = {}
    for name_to_download in names_to_download:
        print(f"Downloading result for {name_to_download}")
        try:
            conn = mysql.connector.connect(**config)
            print("Database connection established!")

            cursor = conn.cursor()
            conn.start_transaction()

            select_query = "SELECT result FROM experiments WHERE name=%s"
            cursor.execute(select_query, (name_to_download,))
            rows = cursor.fetchall()
            name_to_result[name_to_download] = rows[0][0]
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

    return name_to_result


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage experiments/tasks via MySQL database")
    parser.add_argument("--fetch_results", action="store_true",
                        help="Fetch results for all finished tasks")
    parser.add_argument("--sort_results", action="store_true",
                        help="Sort result files by last timestamp in log")
    parser.add_argument("--show_unfinished", action="store_true",
                        help="Show tasks that are not assigned or finished yet")

    args = parser.parse_args()
    if args.fetch_results:
        existing_result_files = find_existing_result_files()
        name_to_result = fetch_results(existing_result_files)
        for name, result in name_to_result.items():
            result = repair_result(name, result)
            out_file = f"results_{name}.json"
            if not exists(out_file):
                print(f"Write new result to file {out_file}")
                with open(out_file, "w") as f:
                    f.write(result)
    elif args.sort_results:
        sort_results()
    elif args.show_unfinished:
        show_unfinished_tasks()

    else:
        print("Nothing do to (use --fetch_results to fetch results)")
