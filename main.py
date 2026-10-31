import os
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

# CA certificate should be alongside main.py
SSL_CA_PATH = BASE_DIR / "ca.pem"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Application directory: %s", BASE_DIR)
logger.info("Expected CA certificate: %s", SSL_CA_PATH)
logger.info("CA certificate exists: %s", SSL_CA_PATH.is_file())


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_connection(max_retries=3, retry_delay=2):

    if not all([
        MYSQL_HOST,
        MYSQL_DATABASE,
        MYSQL_USER,
        MYSQL_PASSWORD
    ]):
        logger.error("Missing MySQL environment variables.")
        raise HTTPException(
            status_code=503,
            detail="Database configuration is incomplete."
        )

    if not SSL_CA_PATH.is_file():
        logger.error("CA certificate not found at: %s", SSL_CA_PATH)
        raise HTTPException(
            status_code=503,
            detail="Database SSL certificate is missing."
        )

    connection_options = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "database": MYSQL_DATABASE,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "connection_timeout": 10,
        "ssl_disabled": False,
        "ssl_ca": str(SSL_CA_PATH),
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
        "use_pure": True,
    }

    for attempt in range(1, max_retries + 1):
        try:
            connection = mysql.connector.connect(**connection_options)
            logger.info("Successfully connected to MySQL.")
            return connection

        except mysql.connector.Error as error:
            logger.warning(
                "Database connection failed (attempt %s/%s): %s",
                attempt,
                max_retries,
                error
            )

            if attempt == max_retries:
                logger.error("Database unavailable after all retries.")
                raise HTTPException(
                    status_code=503,
                    detail="Database temporarily unavailable. Please try again shortly."
                )

            time.sleep(retry_delay)


# ==========================================
# CREATE DATABASE TABLE
# ==========================================

def create_table():
    conn = get_connection()
    cursor = None

    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                completed TINYINT(1) NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
        logger.info("Database table is ready.")

    except mysql.connector.Error as error:
        logger.error("Database initialization failed: %s", error)
        raise

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


# ==========================================
# APPLICATION STARTUP
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Todo API...")

    try:
        create_table()
    except Exception as error:
        logger.warning("Database initialization unavailable: %s", error)

    logger.info("Todo API startup completed.")
    yield
    logger.info("Todo API shutting down.")


app = FastAPI(lifespan=lifespan)


# ==========================================
# CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://syedali313786.github.io"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# TASK MODEL
# ==========================================

class TaskCreate(BaseModel):
    title: str


# ==========================================
# HOME
# ==========================================

@app.get("/")
def home():
    return {"message": "Todo app is running"}


# ==========================================
# ABOUT
# ==========================================

@app.get("/about")
def about():
    return {
        "project": "Todo app",
        "status": "learning api"
    }


# ==========================================
# CREATE TASK
# ==========================================

@app.post("/tasks")
def create_task(task: TaskCreate):
    title = task.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Task title cannot be empty."
        )

    conn = get_connection()
    cursor = None

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title) VALUES (%s)",
            (title,)
        )
        conn.commit()

        return {
            "message": "Task created successfully",
            "task_id": cursor.lastrowid,
            "task_title": title,
            "completed": False
        }

    except mysql.connector.Error as error:
        logger.error("Error creating task: %s", error)
        raise HTTPException(
            status_code=500,
            detail="Failed to create task."
        )

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


# ==========================================
# GET ALL TASKS
# ==========================================

@app.get("/tasks")
def get_tasks():
    conn = get_connection()
    cursor = None

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, completed FROM tasks ORDER BY id"
        )
        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "completed": bool(row[2])
            }
            for row in rows
        ]

    except mysql.connector.Error as error:
        logger.error("Error loading tasks: %s", error)
        raise HTTPException(
            status_code=500,
            detail="Failed to load tasks."
        )

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


# ==========================================
# UPDATE TASK
# ==========================================

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, completed: bool):
    conn = get_connection()
    cursor = None

    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET completed = %s WHERE id = %s",
            (int(completed), task_id)
        )
        conn.commit()

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id FROM tasks WHERE id = %s",
                (task_id,)
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Task not found."
                )

        return {
            "message": "Task updated successfully",
            "task_id": task_id,
            "completed": completed
        }

    except mysql.connector.Error as error:
        logger.error("Error updating task: %s", error)
        raise HTTPException(
            status_code=500,
            detail="Failed to update task."
        )

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


# ==========================================
# DELETE TASK
# ==========================================

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_connection()
    cursor = None

    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM tasks WHERE id = %s",
            (task_id,)
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Task not found."
            )

        return {
            "message": "Task deleted successfully",
            "deleted_task": task_id
        }

    except mysql.connector.Error as error:
        logger.error("Error deleting task: %s", error)
        raise HTTPException(
            status_code=500,
            detail="Failed to delete task."
        )

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()