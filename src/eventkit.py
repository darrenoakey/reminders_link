import EventKit
from datetime import datetime
from typing import Optional


# ##################################################################
# request access
# requests permission from the user to access reminders and blocks until granted or denied
def request_access() -> bool:
    import Foundation
    store = EventKit.EKEventStore.alloc().init()

    auth_status = EventKit.EKEventStore.authorizationStatusForEntityType_(EventKit.EKEntityTypeReminder)
    if auth_status == EventKit.EKAuthorizationStatusAuthorized:
        return True
    elif auth_status == EventKit.EKAuthorizationStatusDenied or auth_status == EventKit.EKAuthorizationStatusRestricted:
        return False

    result = {"granted": False, "done": False}

    def completion_handler(access_granted, error):
        result["granted"] = access_granted
        result["done"] = True

    store.requestAccessToEntityType_completion_(
        EventKit.EKEntityTypeReminder,
        completion_handler
    )

    timeout = 10.0
    start = Foundation.NSDate.date()
    while not result["done"]:
        elapsed = -start.timeIntervalSinceNow()
        if elapsed > timeout:
            break
        Foundation.NSRunLoop.currentRunLoop().runMode_beforeDate_(
            Foundation.NSDefaultRunLoopMode,
            Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )

    return result["granted"]


# ##################################################################
# get event store
# creates and returns an EventKit event store instance for accessing reminders
def get_event_store() -> EventKit.EKEventStore:
    return EventKit.EKEventStore.alloc().init()


# ##################################################################
# list reminder lists
# returns all reminder lists as tuples of id and title
def list_reminder_lists(store: EventKit.EKEventStore) -> list[tuple[str, str]]:
    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
    return [(cal.calendarIdentifier(), cal.title()) for cal in calendars]


# ##################################################################
# get reminder list by id
# finds and returns a specific reminder list calendar by its identifier
def get_reminder_list_by_id(store: EventKit.EKEventStore, list_id: str) -> Optional[EventKit.EKCalendar]:
    return store.calendarWithIdentifier_(list_id)


# ##################################################################
# is valid component
# checks if a date component value is valid and not NSNotFound
def is_valid_component(value: int) -> bool:
    import Foundation
    return value != Foundation.NSNotFound and 0 < value < 999999


# ##################################################################
# convert reminder to dict
# transforms an EventKit reminder into a dictionary representation
def convert_reminder_to_dict(reminder: EventKit.EKReminder) -> dict:
    due_date = None
    if reminder.dueDateComponents():
        components = reminder.dueDateComponents()
        year = components.year()
        month = components.month()
        day = components.day()
        hour = components.hour()
        minute = components.minute()

        if is_valid_component(year) and is_valid_component(month) and is_valid_component(day):
            due_date = datetime(
                year,
                month,
                day,
                hour if is_valid_component(hour) else 0,
                minute if is_valid_component(minute) else 0
            ).isoformat()

    priority = reminder.priority()
    if priority < 0 or priority > 10:
        priority = 0

    return {
        "id": reminder.calendarItemIdentifier(),
        "title": reminder.title() or "",
        "notes": reminder.notes() or "",
        "completed": reminder.isCompleted(),
        "due_date": due_date,
        "priority": priority,
        "list_id": reminder.calendar().calendarIdentifier() if reminder.calendar() else None,
        "list_name": reminder.calendar().title() if reminder.calendar() else None
    }


# ##################################################################
# fetch reminders from list
# retrieves all reminders from a specific list with optional completion filter
def fetch_reminders_from_list(
    store: EventKit.EKEventStore,
    list_id: str,
    include_completed: bool = False
) -> list[dict]:
    calendar = get_reminder_list_by_id(store, list_id)
    if not calendar:
        return []

    predicate = store.predicateForRemindersInCalendars_([calendar])
    reminders = []
    fetched = [False]

    def completion_handler(reminder_list):
        if reminder_list:
            for reminder in reminder_list:
                if include_completed or not reminder.isCompleted():
                    reminders.append(convert_reminder_to_dict(reminder))
        fetched[0] = True

    store.fetchRemindersMatchingPredicate_completion_(predicate, completion_handler)

    import Foundation
    timeout = 5.0
    start = Foundation.NSDate.date()
    while not fetched[0]:
        elapsed = -start.timeIntervalSinceNow()
        if elapsed > timeout:
            break
        Foundation.NSRunLoop.currentRunLoop().runMode_beforeDate_(
            Foundation.NSDefaultRunLoopMode,
            Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )

    return reminders


# ##################################################################
# create reminder
# creates a new reminder in the specified list with title notes and optional due date
def create_reminder(
    store: EventKit.EKEventStore,
    list_id: str,
    title: str,
    notes: str = "",
    due_date: Optional[datetime] = None,
    priority: int = 0
) -> Optional[str]:
    calendar = get_reminder_list_by_id(store, list_id)
    if not calendar:
        return None

    reminder = EventKit.EKReminder.reminderWithEventStore_(store)
    reminder.setTitle_(title)
    reminder.setNotes_(notes)
    reminder.setCalendar_(calendar)
    reminder.setPriority_(priority)

    if due_date:
        components = EventKit.NSDateComponents.alloc().init()
        components.setYear_(due_date.year)
        components.setMonth_(due_date.month)
        components.setDay_(due_date.day)
        components.setHour_(due_date.hour)
        components.setMinute_(due_date.minute)
        reminder.setDueDateComponents_(components)

    success, error = store.saveReminder_commit_error_(reminder, True, None)
    if not success:
        return None

    return reminder.calendarItemIdentifier()


# ##################################################################
# update reminder
# modifies an existing reminder with new values including list calendar title notes completion and due date
def update_reminder(
    store: EventKit.EKEventStore,
    reminder_id: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    completed: Optional[bool] = None,
    due_date: Optional[datetime] = None,
    priority: Optional[int] = None,
    list_id: Optional[str] = None
) -> bool:
    reminder = store.calendarItemWithIdentifier_(reminder_id)
    if not reminder or not isinstance(reminder, EventKit.EKReminder):
        return False

    if title is not None:
        reminder.setTitle_(title)
    if notes is not None:
        reminder.setNotes_(notes)
    if completed is not None:
        reminder.setCompleted_(completed)
    if priority is not None:
        reminder.setPriority_(priority)
    if due_date is not None:
        components = EventKit.NSDateComponents.alloc().init()
        components.setYear_(due_date.year)
        components.setMonth_(due_date.month)
        components.setDay_(due_date.day)
        components.setHour_(due_date.hour)
        components.setMinute_(due_date.minute)
        reminder.setDueDateComponents_(components)
    if list_id is not None:
        calendar = get_reminder_list_by_id(store, list_id)
        if not calendar:
            return False
        reminder.setCalendar_(calendar)

    success, error = store.saveReminder_commit_error_(reminder, True, None)
    return success


# ##################################################################
# get reminder by id
# retrieves a reminder by its identifier and returns it as a dict or None
def get_reminder_by_id(store: EventKit.EKEventStore, reminder_id: str) -> Optional[dict]:
    reminder = store.calendarItemWithIdentifier_(reminder_id)
    if not reminder or not isinstance(reminder, EventKit.EKReminder):
        return None
    return convert_reminder_to_dict(reminder)


# ##################################################################
# delete reminder
# removes a reminder by its identifier
def delete_reminder(store: EventKit.EKEventStore, reminder_id: str) -> bool:
    reminder = store.calendarItemWithIdentifier_(reminder_id)
    if not reminder or not isinstance(reminder, EventKit.EKReminder):
        return False

    success, error = store.removeReminder_commit_error_(reminder, True, None)
    return success


# ##################################################################
# create test list
# creates a new reminder list calendar for testing purposes
def create_test_list(store: EventKit.EKEventStore, title: str) -> Optional[str]:
    calendar = EventKit.EKCalendar.calendarForEntityType_eventStore_(
        EventKit.EKEntityTypeReminder,
        store
    )
    calendar.setTitle_(title)

    sources = store.sources()
    if sources and len(sources) > 0:
        calendar.setSource_(sources[0])
    else:
        return None

    success, error = store.saveCalendar_commit_error_(calendar, True, None)
    if not success:
        return None

    return calendar.calendarIdentifier()


# ##################################################################
# delete test list
# removes a reminder list calendar by identifier
def delete_test_list(store: EventKit.EKEventStore, list_id: str) -> bool:
    calendar = get_reminder_list_by_id(store, list_id)
    if not calendar:
        return False

    success, error = store.removeCalendar_commit_error_(calendar, True, None)
    return success
