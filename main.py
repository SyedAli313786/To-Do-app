from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from pathlib import Path

DB_path = Path(__file__).parent / "database" / "todo.db"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Taskcreate(BaseModel):
    title: str


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
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tasks (title) VALUES (?)",
        (task.title,)
    )

    conn.commit()
    conn.close()

    return {
        "message": "Task received successfully",
        "task_title": task.title
    }


@app.get("/tasks")
def get_tasks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()

    conn.close()

    return rows


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, completed: bool):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tasks SET completed = ? WHERE id = ?",
        (int(completed), task_id)
    )

    conn.commit()
    conn.close()

    return {
        "message": "Task updated successfully",
        "task_id": task_id,
        "completed": completed
    }


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    conn.commit()
    conn.close()

    return {
        "message": "Task deleted successfully",
        "deleted_task": task_id
    }


def get_connection():
    conn = sqlite3.connect(DB_path)
    return conn