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
            print(f"Inserting {name} with result {result}")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage experiments/tasks via MySQL database")
    parser.add_argument("--fetch_results", action="store_true",
                        help="Fetch results for all finished tasks")

    args = parser.parse_args()
    if args.fetch_results:
        name_to_result = fetch_results()
        for name, result in name_to_result.items():
            with open(f"results_{name}.json", "w") as f:
                f.write(result)

    else:
        print("Nothing do to (use --fetch_results to fetch results)")
