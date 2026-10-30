import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# MySQL connection settings
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

# SSL certificate downloaded from Aiven
CA_CERT_PATH = Path("/etc/secrets/ca.pem")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Taskcreate(BaseModel):
    title: str


def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=MYSQL_DATABASE,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        ssl_ca=str(CA_CERT_PATH),
        ssl_verify_cert=True,
        ssl_verify_identity=True,
    )


def create_table():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                completed TINYINT(1) NOT NULL DEFAULT 0
            )
            """
        )

        conn.commit()
        cursor.close()

    finally:
        conn.close()


@app.on_event("startup")
def startup():
    create_table()


@app.get("/")
def home():
    return {
        "message": "Todo app is running"
    }


@app.get("/about")
def about():
    return {
        "project": "to do app",
        "status": "learning api"
    }


@app.post("/tasks")
def create_task(task: Taskcreate):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO tasks (title) VALUES (%s)",
            (task.title,)
        )

        conn.commit()

        return {
            "message": "Task received successfully",
            "task_title": task.title
        }

    finally:
        conn.close()


@app.get("/tasks")
def get_tasks():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, title, completed FROM tasks ORDER BY id"
        )

        rows = cursor.fetchall()

        return rows

    finally:
        conn.close()


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, completed: bool):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE tasks
            SET completed = %s
            WHERE id = %s
            """,
            (int(completed), task_id)
        )

        conn.commit()

        return {
            "message": "Task updated successfully",
            "task_id": task_id,
            "completed": completed
        }

    finally:
        conn.close()


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM tasks WHERE id = %s",
            (task_id,)
        )

        conn.commit()

        return {
            "message": "Task deleted successfully",
            "deleted_task": task_id
        }

    finally:
        conn.close()