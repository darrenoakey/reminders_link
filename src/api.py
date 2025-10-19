from flask import Flask, request, jsonify, abort
from datetime import datetime
from . import eventkit
from .cache import RemindersCache

app = Flask(__name__)

store = None
cache = None


# ##################################################################
# initialize
# sets up eventkit access and cache when first needed
def initialize():
    global store, cache

    if store is not None:
        return

    if not eventkit.request_access():
        raise RuntimeError("Failed to get access to Reminders")

    store = eventkit.get_event_store()
    cache = RemindersCache(store)


# ##################################################################
# root endpoint
# returns all available reminder lists with their ids and names
@app.route("/")
def root():
    initialize()
    lists = cache.get_lists()
    return jsonify({
        "lists": [
            {"id": list_id, "name": name}
            for list_id, name in lists
        ]
    })


# ##################################################################
# get lists
# returns all available reminder lists with their ids and names
@app.route("/lists")
def get_lists():
    initialize()
    lists = cache.get_lists()
    return jsonify({
        "lists": [
            {"id": list_id, "name": name}
            for list_id, name in lists
        ]
    })


# ##################################################################
# get reminders from list
# retrieves reminders from a specific list with optional completion filter
@app.route("/lists/<list_id>/reminders")
def get_reminders(list_id: str):
    initialize()
    include_completed = request.args.get("include_completed", "false").lower() == "true"
    reminders = cache.get_reminders(list_id, include_completed)
    return jsonify({
        "list_id": list_id,
        "count": len(reminders),
        "reminders": reminders
    })


# ##################################################################
# create reminder
# adds a new reminder to the specified list
@app.route("/lists/<list_id>/reminders", methods=["POST"])
def create_reminder(list_id: str):
    initialize()
    data = request.get_json()
    if not data:
        abort(400, description="Request body must be JSON")

    title = data.get("title")
    if not title:
        abort(400, description="title is required")

    notes = data.get("notes", "")
    priority = data.get("priority", 0)

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.fromisoformat(data["due_date"])
        except ValueError:
            abort(400, description="Invalid due_date format. Use ISO format.")

    reminder_id = cache.add_reminder(
        list_id,
        title,
        notes,
        due_date,
        priority
    )

    if not reminder_id:
        abort(404, description="List not found or failed to create reminder")

    return jsonify({
        "id": reminder_id,
        "list_id": list_id,
        "message": "Reminder created successfully"
    })


# ##################################################################
# update reminder
# modifies an existing reminder with the provided fields including list
@app.route("/reminders/<reminder_id>", methods=["PUT"])
def update_reminder(reminder_id: str):
    initialize()
    data = request.get_json()
    if not data:
        abort(400, description="Request body must be JSON")

    title = data.get("title")
    notes = data.get("notes")
    completed = data.get("completed")
    priority = data.get("priority")
    list_id = data.get("list_id")

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.fromisoformat(data["due_date"])
        except ValueError:
            abort(400, description="Invalid due_date format. Use ISO format.")

    success = cache.update_reminder(
        reminder_id,
        title,
        notes,
        completed,
        due_date,
        priority,
        list_id
    )

    if not success:
        abort(404, description="Reminder not found or failed to update")

    return jsonify({
        "id": reminder_id,
        "message": "Reminder updated successfully"
    })


# ##################################################################
# invalidate list cache
# forces a refresh of cached data for a specific list
@app.route("/lists/<list_id>/refresh", methods=["POST"])
def refresh_list(list_id: str):
    initialize()
    cache.invalidate_list(list_id)
    return jsonify({
        "list_id": list_id,
        "message": "Cache invalidated for list"
    })


# ##################################################################
# set reminder due today
# sets a reminder's due date to end of today and moves it to next actions list
@app.route("/reminders/<reminder_id>/due-today", methods=["POST"])
def set_due_today(reminder_id: str):
    initialize()
    from datetime import date
    today = date.today()
    due_date = datetime(today.year, today.month, today.day, 23, 59)

    success = cache.update_reminder(
        reminder_id,
        due_date=due_date,
        list_id="18A8C778-4FE9-40B6-A798-EA02070DC037"
    )

    if not success:
        abort(404, description="Reminder not found or failed to update")

    return jsonify({
        "id": reminder_id,
        "due_date": due_date.isoformat(),
        "list_id": "18A8C778-4FE9-40B6-A798-EA02070DC037",
        "list_name": "next actions",
        "message": "Reminder due date set to end of today and moved to next actions"
    })


# ##################################################################
# move reminder to shopping
# moves a reminder to the shopping list
@app.route("/reminders/<reminder_id>/move-to-shopping", methods=["POST"])
def move_to_shopping(reminder_id: str):
    initialize()

    success = cache.update_reminder(
        reminder_id,
        list_id="F3BD7D1E-47D8-4156-8AB9-1579D2F65E60"
    )

    if not success:
        abort(404, description="Reminder not found or failed to update")

    return jsonify({
        "id": reminder_id,
        "list_id": "F3BD7D1E-47D8-4156-8AB9-1579D2F65E60",
        "list_name": "Shopping",
        "message": "Reminder moved to Shopping"
    })


# ##################################################################
# convert task to project note
# adds a task as a bullet point note to a project reminder then deletes the task
@app.route("/reminders/<task_id>/convert-to-project-note/<project_id>", methods=["POST"])
def convert_task_to_project_note(task_id: str, project_id: str):
    initialize()

    task = cache.get_reminder_by_id(task_id)
    if not task:
        abort(404, description="Task not found")

    project = cache.get_reminder_by_id(project_id)
    if not project:
        abort(404, description="Project not found")

    current_notes = project.get("notes", "")
    task_title = task.get("title", "")

    if current_notes:
        new_notes = f"{current_notes}\n- {task_title}"
    else:
        new_notes = f"- {task_title}"

    update_success = cache.update_reminder(
        project_id,
        notes=new_notes
    )

    if not update_success:
        abort(500, description="Failed to update project notes")

    delete_success = cache.delete_reminder(task_id)

    if not delete_success:
        abort(500, description="Failed to delete task")

    return jsonify({
        "task_id": task_id,
        "project_id": project_id,
        "task_title": task_title,
        "message": "Task converted to project note and deleted"
    })


# ##################################################################
# clear all cache
# removes all cached reminder data forcing fresh fetches
@app.route("/cache/clear", methods=["POST"])
def clear_cache():
    initialize()
    cache.clear_cache()
    return jsonify({
        "message": "All cache cleared"
    })
