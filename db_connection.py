import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='placement_project'
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to database: {e}")
        return None
