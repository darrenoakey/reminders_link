import pytest
from datetime import datetime
from . import eventkit
from .cache import RemindersCache


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
    test_list_name = f"RemindersLinkCacheTest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    list_id = eventkit.create_test_list(event_store, test_list_name)
    assert list_id is not None, "Failed to create test list"

    yield list_id

    eventkit.delete_test_list(event_store, list_id)


# ##################################################################
# fixture cache
# provides a reminders cache instance for testing
@pytest.fixture
def cache(event_store):
    return RemindersCache(event_store)


# ##################################################################
# test get reminders empty
# verifies that fetching from an empty list returns no reminders
def test_get_reminders_empty(cache, test_list):
    reminders = cache.get_reminders(test_list, include_completed=False)
    assert len(reminders) == 0


# ##################################################################
# test add and get reminder
# verifies adding a reminder and retrieving it through the cache
def test_add_and_get_reminder(cache, test_list):
    reminder_id = cache.add_reminder(test_list, "Cached Test Reminder", "Test notes")
    assert reminder_id is not None

    reminders = cache.get_reminders(test_list, include_completed=False)
    assert len(reminders) == 1
    assert reminders[0]["title"] == "Cached Test Reminder"
    assert reminders[0]["notes"] == "Test notes"


# ##################################################################
# test update reminder through cache
# verifies updating a reminder and seeing changes through the cache
def test_update_reminder_through_cache(cache, test_list):
    reminder_id = cache.add_reminder(test_list, "Original", "Original notes")
    assert reminder_id is not None

    success = cache.update_reminder(reminder_id, title="Modified", completed=True)
    assert success is True

    reminders_incomplete = cache.get_reminders(test_list, include_completed=False)
    assert len(reminders_incomplete) == 0

    reminders_all = cache.get_reminders(test_list, include_completed=True)
    assert len(reminders_all) == 1
    assert reminders_all[0]["title"] == "Modified"
    assert reminders_all[0]["completed"] is True


# ##################################################################
# test filter completed
# verifies that the cache correctly filters completed reminders
def test_filter_completed(cache, test_list):
    _id1 = cache.add_reminder(test_list, "Incomplete Task", "")
    id2 = cache.add_reminder(test_list, "Complete Task", "")

    cache.update_reminder(id2, completed=True)

    reminders_incomplete = cache.get_reminders(test_list, include_completed=False)
    assert len(reminders_incomplete) == 1
    assert reminders_incomplete[0]["title"] == "Incomplete Task"

    reminders_all = cache.get_reminders(test_list, include_completed=True)
    assert len(reminders_all) == 2


# ##################################################################
# test get lists
# verifies that the cache can retrieve all reminder lists
def test_get_lists(cache):
    lists = cache.get_lists()
    assert isinstance(lists, list)
    assert len(lists) > 0
    assert all(isinstance(item, tuple) and len(item) == 2 for item in lists)


# ##################################################################
# test invalidate list
# verifies that invalidating a list causes a fresh fetch on next access
def test_invalidate_list(cache, test_list):
    cache.add_reminder(test_list, "First Reminder", "")

    reminders = cache.get_reminders(test_list)
    assert len(reminders) == 1

    cache.invalidate_list(test_list)

    reminders = cache.get_reminders(test_list)
    assert len(reminders) == 1


# ##################################################################
# test clear cache
# verifies that clearing the cache removes all cached data
def test_clear_cache(cache, test_list):
    cache.add_reminder(test_list, "Test Reminder", "")

    reminders = cache.get_reminders(test_list)
    assert len(reminders) == 1

    cache.clear_cache()
    assert len(cache.cache) == 0
    assert len(cache.last_refresh) == 0

    reminders = cache.get_reminders(test_list)
    assert len(reminders) == 1
