![](banner.jpg)

# Reminders Link

Fast REST API for accessing and managing Apple Reminders on macOS.

## Purpose

Reminders Link provides a simple HTTP interface to interact with Apple's Reminders app on macOS. Query reminder lists, view reminders, create new ones, and update existing reminders through standard REST endpoints.

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

```bash
./run server
```

The API runs at `http://localhost:18888`

### API Endpoints

#### List All Reminder Lists

```bash
GET /lists
```

Returns all available reminder lists with their IDs and titles.

**Example:**

```bash
curl http://localhost:18888/lists
```

**Response:**

```json
[
  {"id": "ABC123", "title": "Personal"},
  {"id": "DEF456", "title": "Work"}
]
```

#### Get Reminders from a List

```bash
GET /lists/{list_id}/reminders
GET /lists/{list_id}/reminders?include_completed=true
```

Retrieves reminders from a specific list. By default, returns incomplete reminders only. Add `include_completed=true` to include completed reminders.

**Example:**

```bash
curl http://localhost:18888/lists/ABC123/reminders
curl "http://localhost:18888/lists/ABC123/reminders?include_completed=true"
```

**Response:**

```json
[
  {
    "id": "REM001",
    "title": "Buy groceries",
    "completed": false,
    "notes": "Milk, eggs, bread"
  }
]
```

#### Create a New Reminder

```bash
POST /lists/{list_id}/reminders
```

Creates a reminder in the specified list.

**Example:**

```bash
curl -X POST http://localhost:18888/lists/ABC123/reminders \
  -H "Content-Type: application/json" \
  -d '{"title": "Call dentist", "notes": "Schedule checkup"}'
```

**Response:**

```json
{
  "id": "REM002",
  "title": "Call dentist",
  "completed": false,
  "notes": "Schedule checkup"
}
```

#### Update a Reminder

```bash
PUT /reminders/{reminder_id}
```

Updates an existing reminder. Can modify title, notes, or completion status.

**Example:**

```bash
curl -X PUT http://localhost:18888/reminders/REM001 \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'
```

**Response:**

```json
{
  "id": "REM001",
  "title": "Buy groceries",
  "completed": true,
  "notes": "Milk, eggs, bread"
}
```

## Testing

Run individual test file:

```bash
./run test src/eventkit_test.py
```

Run linter:

```bash
./run lint
```

Run full validation suite:

```bash
./run check
```

## Requirements

- macOS (uses Apple EventKit framework)
- Python 3.8 or later
- Permission to access Reminders (macOS will prompt on first use)