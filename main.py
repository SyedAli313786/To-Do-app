import os
import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse, unquote

import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ==========================================
# CONFIGURATION
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_connection():
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable is missing.")
        raise HTTPException(
            status_code=503,
            detail="Database configuration is missing."
        )

    try:
        parsed = urlparse(DATABASE_URL)

        if parsed.scheme not in ("mysql", "mysql+pymysql"):
            logger.error("Unsupported database URL scheme.")
            raise HTTPException(
                status_code=503,
                detail="Invalid database configuration."
            )

        host = parsed.hostname
        port = parsed.port or 3306
        database = parsed.path.lstrip("/")
        user = unquote(parsed.username or "")
        password = unquote(parsed.password or "")

        if not all([host, database, user, password]):
            logger.error("Database URL is missing required components.")
            raise HTTPException(
                status_code=503,
                detail="Database configuration is incomplete."
            )

        connection = mysql.connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connection_timeout=10
        )

        return connection

    except HTTPException:
        raise

    except (mysql.connector.Error, ValueError) as error:
        logger.error("Database connection failed: %s", error)

        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable."
        )


# ==========================================
# CREATE DATABASE TABLE
# ==========================================

def create_table():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    completed TINYINT(1) NOT NULL DEFAULT 0
                )
            """)

            conn.commit()
            logger.info("Tasks table is ready.")

        finally:
            cursor.close()

    finally:
        conn.close()


# ==========================================
# APPLICATION STARTUP
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Todo API...")

    try:
        create_table()
        logger.info("Database initialized successfully.")

    except Exception:
        logger.exception("Database initialization failed.")

    yield

    logger.info("Todo API shutting down.")


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(lifespan=lifespan)


# ==========================================
# CORS CONFIGURATION
# ==========================================

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


# ==========================================
# PYDANTIC MODEL
# ==========================================

class TaskCreate(BaseModel):
    title: str


# ==========================================
# HOME ENDPOINT
# ==========================================

@app.get("/")
def home():
    return {
        "message": "Todo app is running"
    }


# ==========================================
# ABOUT ENDPOINT
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

    try:
        cursor = conn.cursor()

        try:
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

        finally:
            cursor.close()

    except mysql.connector.Error:
        logger.exception("Error creating task.")

        raise HTTPException(
            status_code=500,
            detail="Failed to create task."
        )

    finally:
        conn.close()


# ==========================================
# GET ALL TASKS
# ==========================================

@app.get("/tasks")
def get_tasks():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        try:
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

        finally:
            cursor.close()

    except mysql.connector.Error:
        logger.exception("Error loading tasks.")

        raise HTTPException(
            status_code=500,
            detail="Failed to load tasks."
        )

    finally:
        conn.close()


# ==========================================
# UPDATE TASK
# ==========================================

@app.patch("/tasks/{task_id}")
def update_task(task_id: int, completed: bool):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        try:
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

        finally:
            cursor.close()

    except mysql.connector.Error:
        logger.exception("Error updating task.")

        raise HTTPException(
            status_code=500,
            detail="Failed to update task."
        )

    finally:
        conn.close()


# ==========================================
# DELETE TASK
# ==========================================

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        try:
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

        finally:
            cursor.close()

    except mysql.connector.Error:
        logger.exception("Error deleting task.")

        raise HTTPException(
            status_code=500,
            detail="Failed to delete task."
        )

    finally:
        conn.close()