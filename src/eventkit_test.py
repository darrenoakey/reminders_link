import pytest
from datetime import datetime
from . import eventkit


# ##################################################################
# fixture event store
# provides an eventkit event store for tests ensuring access is granted
@pytest.fixture
def event_store():
    access = eventkit.request_access()
    assert access, "Failed to get Reminders access"
    return eventkit.get_event_store()


# ##################################################################
# fixture test list
# creates a temporary test list for testing and cleans it up after
@pytest.fixture
def test_list(event_store):
    test_list_name = f"RemindersLinkTest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    list_id = eventkit.create_test_list(event_store, test_list_name)
    assert list_id is not None, "Failed to create test list"

    yield list_id

    eventkit.delete_test_list(event_store, list_id)


# ##################################################################
# test request access
# verifies that requesting access to reminders succeeds
def test_request_access():
    access = eventkit.request_access()
    assert access is True


# ##################################################################
# test list reminder lists
# verifies that we can retrieve all reminder lists
def test_list_reminder_lists(event_store):
    lists = eventkit.list_reminder_lists(event_store)
    assert isinstance(lists, list)
    assert len(lists) > 0
    assert all(isinstance(item, tuple) and len(item) == 2 for item in lists)


# ##################################################################
# test create and fetch reminder
# verifies creating a reminder and retrieving it from the list
def test_create_and_fetch_reminder(event_store, test_list):
    reminder_id = eventkit.create_reminder(
        event_store,
        test_list,
        "Test Reminder",
        "This is a test note",
        None,
        0
    )
    assert reminder_id is not None

    reminders = eventkit.fetch_reminders_from_list(event_store, test_list, include_completed=False)
    assert len(reminders) == 1
    assert reminders[0]["title"] == "Test Reminder"
    assert reminders[0]["notes"] == "This is a test note"
    assert reminders[0]["completed"] is False


# ##################################################################
# test create reminder with due date
# verifies creating a reminder with a due date
def test_create_reminder_with_due_date(event_store, test_list):
    due_date = datetime(2025, 12, 31, 15, 30)
    reminder_id = eventkit.create_reminder(
        event_store,
        test_list,
        "Test Reminder with Due Date",
        "Test note",
        due_date,
        1
    )
    assert reminder_id is not None

    reminders = eventkit.fetch_reminders_from_list(event_store, test_list, include_completed=False)
    assert len(reminders) == 1
    assert reminders[0]["due_date"] is not None
    assert "2025-12-31" in reminders[0]["due_date"]


# ##################################################################
# test update reminder
# verifies updating a reminder title and completion status
def test_update_reminder(event_store, test_list):
    reminder_id = eventkit.create_reminder(
        event_store,
        test_list,
        "Original Title",
        "Original notes",
        None,
        0
    )
    assert reminder_id is not None

    success = eventkit.update_reminder(
        event_store,
        reminder_id,
        title="Updated Title",
        notes="Updated notes",
        completed=True
    )
    assert success is True

    reminders = eventkit.fetch_reminders_from_list(event_store, test_list, include_completed=True)
    assert len(reminders) == 1
    assert reminders[0]["title"] == "Updated Title"
    assert reminders[0]["notes"] == "Updated notes"
    assert reminders[0]["completed"] is True


# ##################################################################
# test fetch incomplete only
# verifies that completed reminders are filtered when include completed is false
def test_fetch_incomplete_only(event_store, test_list):
    _reminder1_id = eventkit.create_reminder(event_store, test_list, "Incomplete Reminder", "", None, 0)
    reminder2_id = eventkit.create_reminder(event_store, test_list, "Complete Reminder", "", None, 0)

    eventkit.update_reminder(event_store, reminder2_id, completed=True)

    reminders_all = eventkit.fetch_reminders_from_list(event_store, test_list, include_completed=True)
    assert len(reminders_all) == 2

    reminders_incomplete = eventkit.fetch_reminders_from_list(event_store, test_list, include_completed=False)
    assert len(reminders_incomplete) == 1
    assert reminders_incomplete[0]["title"] == "Incomplete Reminder"
    assert reminders_incomplete[0]["completed"] is False


# ##################################################################
# test get reminder list by id
# verifies retrieving a specific reminder list by its identifier
def test_get_reminder_list_by_id(event_store, test_list):
    calendar = eventkit.get_reminder_list_by_id(event_store, test_list)
    assert calendar is not None
    assert calendar.calendarIdentifier() == test_list
