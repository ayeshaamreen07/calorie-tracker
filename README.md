# Calorie Tracker

A simple command-line calorie tracking app written in Python, using SQLite for storage.

## Features
- Log food you've eaten, with quantity and automatic timestamp
- Built-in starter food database (editable/extensible)
- Daily calorie summary, with optional daily goal tracking
- 14-day history view
- Undo last log entry

## Requirements
- Python 3.7+ (no external packages needed — uses the built-in `sqlite3` module)

## Usage
```bash
python3 calorie_tracker.py
```

A `calorie_tracker.db` file will be created automatically in the same folder the first time you run it. This file is git-ignored so your personal food log never gets committed.

## Menu options
1. Log food eaten
2. View today's summary
3. View a past date's summary
4. Add a new food to the database
5. List all foods
6. Set daily calorie goal
7. View last 14 days history
8. Delete last log entry
9. Exit
