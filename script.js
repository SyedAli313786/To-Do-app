let input = document.querySelector("#tasks");
let btn = document.querySelector("#Add_button");
let unordered_list = document.querySelector("#list");

const API_URL = "http://127.0.0.1:8000/tasks";


async function loadTasks() {
    let response = await fetch(API_URL);
    let tasks = await response.json();

    unordered_list.innerHTML = "";

    for (let task of tasks) {
        let li = document.createElement("li");

        // Checkbox
        let checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = task[2] === 1;

        checkbox.addEventListener("change", async function () {
            try {
                let updateResponse = await fetch(
                    `${API_URL}/${task[0]}?completed=${checkbox.checked}`,
                    {
                        method: "PATCH"
                    }
                );

                if (!updateResponse.ok) {
                    throw new Error("Could not update task");
                }

                await loadTasks();

            } catch (error) {
                alert("Could not update the task. Please try again.");
                checkbox.checked = !checkbox.checked;
            }
        });

        // Task title
        let title = document.createElement("span");
        title.textContent = task[1];

        if (task[2] === 1) {
            title.classList.add("completed");
        }

        // Delete button
        let delete_button = document.createElement("button");
        delete_button.textContent = "Delete";

        delete_button.addEventListener("click", async function () {
            try {
                let deleteResponse = await fetch(
                    `${API_URL}/${task[0]}`,
                    {
                        method: "DELETE"
                    }
                );

                if (!deleteResponse.ok) {
                    throw new Error("Could not delete task");
                }

                await loadTasks();

            } catch (error) {
                alert("Could not delete the task. Please try again.");
            }
        });

        li.appendChild(checkbox);
        li.appendChild(title);
        li.appendChild(delete_button);

        unordered_list.appendChild(li);
    }
}


// Add a new task
async function addtask() {
    let taskTitle = input.value.trim();

    if (taskTitle === "") {
        alert("Please enter a task");
        return;
    }

    try {
        let response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: taskTitle
            })
        });

        if (!response.ok) {
            throw new Error("Could not save task");
        }

        input.value = "";

        await loadTasks();

    } catch (error) {
        alert("Could not save the task. Make sure FastAPI is running.");
    }
}


// Add button
btn.addEventListener("click", addtask);


// Add a task by pressing Enter
input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        addtask();
    }
});


// Load saved tasks when the page opens
loadTasks();