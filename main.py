import os
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# -----------------------------------
# 1. Environment variables
# -----------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------
# 2. Database connection with retries
# -----------------------------------

def get_connection(max_retries=3, retry_delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                database=MYSQL_DATABASE,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                connection_timeout=5
            )

            return connection

        except mysql.connector.Error as error:
            logger.warning(
                f"Database connection failed "
                f"(attempt {attempt}/{max_retries}): {error}"
            )

            if attempt == max_retries:
                logger.error("Database unavailable after all retries.")

                raise HTTPException(
                    status_code=503,
                    detail="Database temporarily unavailable. Please try again shortly."
                )

            time.sleep(retry_delay)


# -----------------------------------
# 3. Create database table
# -----------------------------------

def create_table():
    conn = get_connection()
    cursor = None

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
        logger.info("Database table is ready.")

    except mysql.connector.Error as error:
        logger.error(f"Database initialization failed: {error}")

    finally:
        if cursor is not None:
            cursor.close()

        conn.close()


# -----------------------------------
# 4. FastAPI lifespan
# -----------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Todo API...")

    try:
        create_table()
    except Exception as error:
        logger.warning(
            f"Database unavailable during startup: {error}"
        )

    logger.info("Todo API startup completed.")

    yield

    logger.info("Todo API shutting down.")


app = FastAPI(lifespan=lifespan)


# -----------------------------------
# 5. CORS configuration
# -----------------------------------

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


# -----------------------------------
# 6. Pydantic model
# -----------------------------------

class Taskcreate(BaseModel):
    title: str


# -----------------------------------
# 7. Home endpoint
# -----------------------------------

@app.get("/")
def home():
    return {
        "message": "Todo app is running"
    }


# -----------------------------------
# 8. About endpoint
# -----------------------------------

@app.get("/about")
def about():
    return {
        "project": "to do app",
        "status": "learning api"
    }


# -----------------------------------
# 9. Create task
# -----------------------------------

@app.post("/tasks")
def create_task(task: Taskcreate):
    conn = get_connection()
    cursor = None

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

    except mysql.connector.Error as error:
        logger.error(f"Error creating task: {error}")

        raise HTTPException(
            status_code=500,
            detail="Failed to create task."
        )

    finally:
        if cursor is not None:
            cursor.close()

        conn.close()


# -----------------------------------
# 10. Get all tasks
# -----------------------------------

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

        return rows

    except mysql.connector.Error as error:
        logger.error(f"Error loading tasks: {error}")

        raise HTTPException(
            status_code=500,
            detail="Failed to load tasks."
        )

    finally:
        if cursor is not None:
            cursor.close()

        conn.close()


# -----------------------------------
# 11. Update task
# -----------------------------------

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, completed: bool):
    conn = get_connection()
    cursor = None

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

    except mysql.connector.Error as error:
        logger.error(f"Error updating task: {error}")

        raise HTTPException(
            status_code=500,
            detail="Failed to update task."
        )

    finally:
        if cursor is not None:
            cursor.close()

        conn.close()


# -----------------------------------
# 12. Delete task
# -----------------------------------

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

        return {
            "message": "Task deleted successfully",
            "deleted_task": task_id
        }

    except mysql.connector.Error as error:
        logger.error(f"Error deleting task: {error}")

        raise HTTPException(
            status_code=500,
            detail="Failed to delete task."
        )

    finally:
        if cursor is not None:
            cursor.close()

        conn.close()