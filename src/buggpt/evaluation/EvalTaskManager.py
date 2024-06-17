import fnmatch
from os.path import exists
from os import listdir, getcwd
import json
from typing import Dict
import mysql.connector
import argparse

config = {
    "user": "buggpt_user_w",
    "host": "sql702.your-server.de",
    "database": "buggpt_db"
}
with open(".db_token", "r") as f:
    config["password"] = f.read().strip()

with open(".worker_id", "r") as f:
    my_worker_id = f.read().strip()


def write_tasks(name_to_task: Dict[str, str]):
    try:
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        cursor = conn.cursor()

        insert_query = "INSERT INTO experiments (name, task) VALUES (%s, %s)"
        for name, task in name_to_task.items():
            print(f"Inserting {name} with task {task}")
            cursor.execute(insert_query, (name, task))

        conn.commit()
        print("Data inserted successfully!")

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


def fetch_task():
    task_filter = "scikit-learn%"  # note: SQL wildcard syntax

    try:
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        cursor = conn.cursor()
        conn.start_transaction()

        # check if there's already a task assigned to this container; if yes, resume it
        select_query = "SELECT name, task FROM experiments WHERE worker=%s AND result IS NULL"
        cursor.execute(select_query, (my_worker_id,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]

        # otherwise, fetch a new task and mark it as assigned to this container
        select_query = "SELECT name, task FROM experiments WHERE worker IS NULL AND name LIKE %s LIMIT 1"
        cursor.execute(select_query, (task_filter,))
        row = cursor.fetchone()

        if row:
            name, task = row[0], row[1]
            update_query = "UPDATE experiments SET worker=%s WHERE name=%s"
            cursor.execute(update_query, (my_worker_id, name))
            conn.commit()
            return name, task
        else:
            print("No task found.")
            return None, None

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

    return None, None


def write_results(name_to_result: Dict[str, str]):
    try:
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        cursor = conn.cursor()

        insert_query = "UPDATE experiments SET result=%s WHERE name=%s"
        for name, result in name_to_result.items():
            print(f"Inserting {name} with result of length {len(result)}")
            cursor.execute(insert_query, (result, name))

        conn.commit()
        print("Data inserted successfully!")

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


def fetch_results() -> Dict[str, str]:
    try:
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        cursor = conn.cursor()
        conn.start_transaction()

        # check if there's already a task assigned to this container; if yes, resume it
        select_query = "SELECT name, result FROM experiments WHERE result is not NULL"
        cursor.execute(select_query)
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}
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

    return {}


def repair_result(name, result_as_str):
    # past bug has added one level too much of nested lists
    result = json.loads(result_as_str)
    if len(result) > 1 and type(result[0]) == list:
        # the result entry needs fixing
        print(f"Fixing format of result for {name}")
        fixed_result = []
        for entry in result:
            for evt in entry:
                fixed_result.append(evt)
        return json.dumps(fixed_result)
    else:
        return result_as_str


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage experiments/tasks via MySQL database")
    parser.add_argument("--fetch_results", action="store_true",
                        help="Fetch results for all finished tasks")
    parser.add_argument("--sort_results", action="store_true",
                        help="Sort result files by last timestamp in log")

    args = parser.parse_args()
    if args.fetch_results:
        name_to_result = fetch_results()
        for name, result in name_to_result.items():
            result = repair_result(name, result)
            out_file = f"results_{name}.json"
            if exists(out_file):
                print(f"Result for {name} already exists, skipping")
            else:
                with open(out_file, "w") as f:
                    f.write(result)
    elif args.sort_results:
        sort_results()

    else:
        print("Nothing do to (use --fetch_results to fetch results)")
