from datetime import datetime
from typing import Optional
import EventKit
from . import eventkit


# ##################################################################
# reminders cache
# in memory cache for reminders organized by list with refresh capability
class RemindersCache:
    # ##################################################################
    # init
    # initializes empty cache with event store reference
    def __init__(self, store: EventKit.EKEventStore):
        self.store = store
        self.cache: dict[str, dict[str, dict]] = {}
        self.last_refresh: dict[str, datetime] = {}

    # ##################################################################
    # get reminders
    # retrieves reminders from cache or fetches if not cached and filters by completion
    def get_reminders(self, list_id: str, include_completed: bool = False) -> list[dict]:
        if list_id not in self.cache:
            self._refresh_list(list_id)

        reminders = list(self.cache.get(list_id, {}).values())

        if not include_completed:
            reminders = [r for r in reminders if not r.get("completed", False)]

        return reminders

    # ##################################################################
    # refresh list
    # fetches all reminders for a list from eventkit and updates the cache
    def _refresh_list(self, list_id: str) -> None:
        reminders = eventkit.fetch_reminders_from_list(self.store, list_id, include_completed=True)

        self.cache[list_id] = {r["id"]: r for r in reminders}
        self.last_refresh[list_id] = datetime.now()

    # ##################################################################
    # add reminder
    # creates a reminder via eventkit and adds it to the cache
    def add_reminder(
        self,
        list_id: str,
        title: str,
        notes: str = "",
        due_date: Optional[datetime] = None,
        priority: int = 0
    ) -> Optional[str]:
        reminder_id = eventkit.create_reminder(self.store, list_id, title, notes, due_date, priority)

        if reminder_id:
            self._refresh_list(list_id)

        return reminder_id

    # ##################################################################
    # update reminder
    # updates a reminder via eventkit and refreshes affected lists in the cache
    def update_reminder(
        self,
        reminder_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        completed: Optional[bool] = None,
        due_date: Optional[datetime] = None,
        priority: Optional[int] = None,
        list_id: Optional[str] = None
    ) -> bool:
        old_list_id = None
        if list_id is not None:
            for current_list_id in self.cache.keys():
                if reminder_id in self.cache[current_list_id]:
                    old_list_id = current_list_id
                    break

        success = eventkit.update_reminder(
            self.store,
            reminder_id,
            title,
            notes,
            completed,
            due_date,
            priority,
            list_id
        )

        if success:
            if list_id is not None and old_list_id is not None:
                self._refresh_list(old_list_id)
                self._refresh_list(list_id)
            else:
                for current_list_id in self.cache.keys():
                    if reminder_id in self.cache[current_list_id]:
                        self._refresh_list(current_list_id)
                        break

        return success

    # ##################################################################
    # get lists
    # retrieves all reminder lists from eventkit without caching
    def get_lists(self) -> list[tuple[str, str]]:
        return eventkit.list_reminder_lists(self.store)

    # ##################################################################
    # invalidate list
    # removes a list from the cache forcing next access to fetch fresh data
    def invalidate_list(self, list_id: str) -> None:
        if list_id in self.cache:
            del self.cache[list_id]
        if list_id in self.last_refresh:
            del self.last_refresh[list_id]

    # ##################################################################
    # get reminder by id
    # retrieves a single reminder by its id from eventkit
    def get_reminder_by_id(self, reminder_id: str) -> Optional[dict]:
        return eventkit.get_reminder_by_id(self.store, reminder_id)

    # ##################################################################
    # delete reminder
    # removes a reminder via eventkit and clears it from cache
    def delete_reminder(self, reminder_id: str) -> bool:
        success = eventkit.delete_reminder(self.store, reminder_id)

        if success:
            for list_id in self.cache.keys():
                if reminder_id in self.cache[list_id]:
                    self._refresh_list(list_id)
                    break

        return success

    # ##################################################################
    # clear cache
    # removes all cached data forcing fresh fetches on next access
    def clear_cache(self) -> None:
        self.cache.clear()
        self.last_refresh.clear()
