import os
import time
import logging
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load local .env file when running locally
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Database environment variables
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_SSL_CA = os.getenv("MYSQL_SSL_CA")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store the CA certificate in a temporary file if provided as environment text
_ssl_ca_file = None

if MYSQL_SSL_CA:
    try:
        certificate_text = MYSQL_SSL_CA.replace("\\n", "\n").strip()

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".pem",
            delete=False,
            encoding="utf-8"
        ) as cert_file:
            cert_file.write(certificate_text + "\n")
            _ssl_ca_file = cert_file.name

        logger.info("MySQL SSL CA certificate loaded.")
    except OSError as error:
        logger.error("Could not prepare MySQL SSL certificate: %s", error)


def get_connection(max_retries=3, retry_delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            connection_options = {
                "host": MYSQL_HOST,
                "port": MYSQL_PORT,
                "database": MYSQL_DATABASE,
                "user": MYSQL_USER,
                "password": MYSQL_PASSWORD,
                "connection_timeout": 10,
                "ssl_disabled": False,
            }

            if _ssl_ca_file:
                connection_options["ssl_ca"] = _ssl_ca_file
                connection_options["ssl_verify_cert"] = True
                connection_options["ssl_verify_identity"] = True

            connection = mysql.connector.connect(**connection_options)

            return connection

        except mysql.connector.Error as error:
            logger.warning(
                "Database connection failed (attempt %s/%s): %s",
                attempt,
                max_retries,
                error,
            )

            if attempt == max_retries:
                logger.error("Database unavailable after all retries.")
                raise HTTPException(
                    status_code=503,
                    detail="Database temporarily unavailable. Please try again shortly.",
                )

            time.sleep(retry_delay)


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

    if _ssl_ca_file and os.path.exists(_ssl_ca_file):
        try:
            os.remove(_ssl_ca_file)
        except OSError:
            logger.warning("Could not remove temporary SSL certificate file.")


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://syedali313786.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskCreate(BaseModel):
    title: str


@app.get("/")
def home():
    return {"message": "Todo app is running"}


@app.get("/about")
def about():
    return {
        "project": "Todo app",
        "status": "learning api"
    }


@app.post("/tasks")
def create_task(task: TaskCreate):
    conn = get_connection()
    cursor = None

    try:
        title = task.title.strip()

        if not title:
            raise HTTPException(
                status_code=400,
                detail="Task title cannot be empty."
            )

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