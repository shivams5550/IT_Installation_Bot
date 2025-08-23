# init_db.py
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

def create_database():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"Database '{DB_NAME}' ensured.")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error creating database: {e}")

def create_tables():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        # Software catalog table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS software_catalog (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            winget_id VARCHAR(255) NOT NULL,
            default_version VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Requests table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_name VARCHAR(255) DEFAULT 'User',
            software_name VARCHAR(255) NOT NULL,
            winget_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            servicenow_ticket_id VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        print("Tables 'software_catalog' and 'requests' ensured.")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_database()
    create_tables()

    # Now populate the software catalog using your existing db.py
    from bot import db
    if db.populate_software_catalog():
        print("Software catalog populated successfully.")
    else:
        print("Failed to populate software catalog.")
