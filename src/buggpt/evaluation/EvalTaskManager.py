import json
from typing import Dict
import mysql.connector

config = {
    "user": "buggpt_user_w",
    "host": "sql702.your-server.de",
    "database": "buggpt_db"
}
with open(".db_token", "r") as f:
    config["password"] = f.read().strip()


def write_tasks(name_to_task: Dict[str, str]):
    try:
        # Connect to the database
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        # Create a cursor object using the cursor() method
        cursor = conn.cursor()

        # Prepare SQL query to INSERT a new row into the table
        insert_query = "INSERT INTO experiments (name, task) VALUES (%s, %s)"
        for name, task in name_to_task.items():
            print(f"Inserting {name} with task {task}")
            # Execute the SQL command
            cursor.execute(insert_query, (name, task))

        # Commit your changes in the database
        conn.commit()
        print("Data inserted successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if conn.is_connected():
            conn.rollback()
            print("Transaction rolled back")

    finally:
        if conn.is_connected():
            # Close the cursor and connection
            cursor.close()
            conn.close()
            print("MySQL connection is closed")


def write_results(name_to_result: Dict[str, str]):
    try:
        # Connect to the database
        conn = mysql.connector.connect(**config)
        print("Database connection established!")

        # Create a cursor object using the cursor() method
        cursor = conn.cursor()

        # Prepare SQL query to INSERT a new row into the table
        insert_query = "UPDATE experiments SET result=%s WHERE name=%s"
        for name, result in name_to_result.items():
            print(f"Inserting {name} with result {result}")
            # Execute the SQL command
            cursor.execute(insert_query, (result, name))

        # Commit your changes in the database
        conn.commit()
        print("Data inserted successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if conn.is_connected():
            conn.rollback()
            print("Transaction rolled back")

    finally:
        if conn.is_connected():
            # Close the cursor and connection
            cursor.close()
            conn.close()
            print("MySQL connection is closed")


if __name__ == "__main__":
    # write_tasks({"test": '["task1", "task2"]'})
    result = {
        "bla": {"blubb": 23, "blubb2": 42}
    }
    json_result = json.dumps(result)
    write_results({"test": json_result})
