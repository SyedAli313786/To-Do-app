
const input = document.querySelector("#tasks");
const btn = document.querySelector("#Add_button");
const unordered_list = document.querySelector("#list");

const API_URL = "https://to-do-app.ethiodeploy.app/tasks";

// Load all tasks from the backend
async function loadTasks() {
    try {
        const response = await fetch(API_URL);

        if (!response.ok) {
            throw new Error(`Failed to load tasks: ${response.status}`);
        }

        const tasks = await response.json();

        console.log("Tasks received:", tasks);

        // Make sure the API returned an array
        if (!Array.isArray(tasks)) {
            throw new Error("The API response is not an array.");
        }

        unordered_list.innerHTML = "";

        for (const task of tasks) {
            const li = document.createElement("li");

            // Create checkbox
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.checked = Boolean(task.completed);

            checkbox.addEventListener("change", async function () {
                try {
                    const response = await fetch(
                        `${API_URL}/${task.id}?completed=${checkbox.checked}`,
                        {
                            method: "PATCH"
                        }
                    );

                    if (!response.ok) {
                        throw new Error("Failed to update task.");
                    }

                    await loadTasks();
                } catch (error) {
                    console.error("Error updating task:", error);
                    alert("Could not update the task. Please try again.");
                    checkbox.checked = !checkbox.checked;
                }
            });

            // Create task title
            const title = document.createElement("span");
            title.textContent = task.title;

            if (task.completed) {
                title.classList.add("completed");
            }

            // Create delete button
            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Delete";

            deleteButton.addEventListener("click", async function () {
                try {
                    const response = await fetch(`${API_URL}/${task.id}`, {
                        method: "DELETE"
                    });

                    if (!response.ok) {
                        throw new Error("Failed to delete task.");
                    }

                    await loadTasks();
                } catch (error) {
                    console.error("Error deleting task:", error);
                    alert("Could not delete the task. Please try again.");
                }
            });

            // Add elements to the list item
            li.appendChild(checkbox);
            li.appendChild(title);
            li.appendChild(deleteButton);

            unordered_list.appendChild(li);
        }
    } catch (error) {
        console.error("Error loading tasks:", error);
        alert("Could not load tasks. Please check the backend connection.");
    }
}

// Add a new task
async function addtask() {
    const taskTitle = input.value.trim();

    if (taskTitle === "") {
        alert("Please enter a task.");
        return;
    }

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: taskTitle
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to save task: ${response.status}`);
        }

        input.value = "";
        await loadTasks();

    } catch (error) {
        console.error("Error adding task:", error);
        alert("Could not save the task. Please try again.");
    }
}

// Add task when the button is clicked
btn.addEventListener("click", addtask);

// Add task when Enter is pressed
input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        addtask();
    }
});

// Load existing tasks when the page opens
loadTasks();
