# bot/db.py
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


def get_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Error as e:
        print(f"Error connecting to DB: {e}")
        return None


# ------------------ Software Catalog ------------------
def get_software_list():
    conn = get_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, winget_id, default_version FROM software_catalog")
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def populate_software_catalog():
    """Populate initial software catalog if empty"""
    initial_software = [
        {"name": "Google Chrome", "winget_id": "Google.Chrome", "default_version": "latest"},
        {"name": "Visual Studio Code", "winget_id": "Microsoft.VisualStudioCode", "default_version": "latest"},
        {"name": "Slack", "winget_id": "SlackTechnologies.Slack", "default_version": "latest"},
        {"name": "Zoom", "winget_id": "Zoom.Zoom", "default_version": "latest"},
        {"name": "AWS CLI", "winget_id": "Amazon.AWSCLI", "default_version": "latest"},
        {"name": "Azure CLI", "winget_id": "Microsoft.AzureCLI", "default_version": "latest"},
        {"name": "Mozilla Firefox", "winget_id": "Mozilla.Firefox", "default_version": "latest"},
        {"name": "Notepad++", "winget_id": "Notepad++.Notepad++", "default_version": "latest"},
        {"name": "VLC Media Player", "winget_id": "VideoLAN.VLC", "default_version": "latest"},
        {"name": "Postman", "winget_id": "Postman.Postman", "default_version": "latest"},
        {"name": "Python", "winget_id": "Python.Python.3", "default_version": "latest"},
        {"name": "Git", "winget_id": "Git.Git", "default_version": "latest"}
    ]

    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()

    for s in initial_software:
        cursor.execute("SELECT id FROM software_catalog WHERE winget_id=%s", (s["winget_id"],))
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO software_catalog (name, winget_id, default_version) VALUES (%s, %s, %s)",
            (s["name"], s["winget_id"], s["default_version"])
        )

    conn.commit()
    cursor.close()
    conn.close()
    return True


# ------------------ Requests ------------------
def log_request(user_name, software_name, winget_id):
    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    sql = "INSERT INTO requests (user_name, software_name, winget_id) VALUES (%s, %s, %s)"
    cursor.execute(sql, (user_name, software_name, winget_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True


def update_request_status(request_id, status):
    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    sql = "UPDATE requests SET status=%s WHERE id=%s"
    cursor.execute(sql, (status, request_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True


# ------------------ ServiceNow Sync ------------------
def update_request_servicenow(request_id, ticket_id):
    """Link request with its ServiceNow ticket (maps to servicenow_ticket_id column)."""
    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    sql = "UPDATE requests SET servicenow_ticket_id=%s WHERE id=%s"
    cursor.execute(sql, (ticket_id, request_id))
    conn.commit()
    cursor.close()
    conn.close()
    return True