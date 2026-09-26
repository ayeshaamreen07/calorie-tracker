#!/usr/bin/env python3
"""
Calorie Tracker
A simple command-line app to track daily food intake and calories.

Data is stored locally in a SQLite database (calorie_tracker.db),
created automatically next to this script the first time you run it.
"""

import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calorie_tracker.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            calories_per_unit REAL NOT NULL,
            unit TEXT NOT NULL DEFAULT 'serving'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            log_date TEXT NOT NULL,
            log_time TEXT NOT NULL,
            FOREIGN KEY (food_id) REFERENCES foods(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


def seed_default_foods():
    """Add a small starter set of common foods if the table is empty."""
    defaults = [
        ("Egg (1 large)", 78, "unit"),
        ("White rice (100g cooked)", 130, "100g"),
        ("Chicken breast (100g cooked)", 165, "100g"),
        ("Banana (1 medium)", 105, "unit"),
        ("Bread slice (whole wheat)", 80, "slice"),
        ("Milk (100ml, whole)", 61, "100ml"),
        ("Apple (1 medium)", 95, "unit"),
        ("Peanut butter (1 tbsp)", 94, "tbsp"),
        ("Olive oil (1 tbsp)", 119, "tbsp"),
        ("Oats (100g dry)", 389, "100g"),
    ]
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM foods")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO foods (name, calories_per_unit, unit) VALUES (?, ?, ?)",
            defaults,
        )
        conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


# ---------- Food management ----------

def add_food():
    print("\n--- Add a new food ---")
    name = input("Food name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return
    try:
        cals = float(input("Calories per unit (e.g. per 100g, per slice, per item): ").strip())
    except ValueError:
        print("Invalid number.")
        return
    unit = input("Unit label (e.g. '100g', 'slice', 'unit') [default: serving]: ").strip() or "serving"

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO foods (name, calories_per_unit, unit) VALUES (?, ?, ?)",
            (name, cals, unit),
        )
        conn.commit()
        print(f"Added '{name}' ({cals} kcal per {unit}).")
    except sqlite3.IntegrityError:
        print(f"A food named '{name}' already exists.")
    conn.close()


def list_foods():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, calories_per_unit, unit FROM foods ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("\nNo foods in the database yet. Add one first.")
        return []
    print("\n--- Food database ---")
    for fid, name, cals, unit in rows:
        print(f"  [{fid}] {name} — {cals} kcal / {unit}")
    return rows


# ---------- Logging ----------

def log_entry():
    rows = list_foods()
    if not rows:
        return
    try:
        food_id = int(input("\nEnter the ID of the food you ate: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, calories_per_unit, unit FROM foods WHERE id = ?", (food_id,))
    food = cur.fetchone()
    if not food:
        print("No food with that ID.")
        conn.close()
        return
    name, cals_per_unit, unit = food

    try:
        qty = float(input(f"How many '{unit}' units of {name}? ").strip())
    except ValueError:
        print("Invalid quantity.")
        conn.close()
        return

    now = datetime.now()
    log_date = now.strftime("%Y-%m-%d")
    log_time = now.strftime("%H:%M")

    cur.execute(
        "INSERT INTO log (food_id, quantity, log_date, log_time) VALUES (?, ?, ?, ?)",
        (food_id, qty, log_date, log_time),
    )
    conn.commit()
    conn.close()

    total = qty * cals_per_unit
    print(f"Logged {qty} x {name} = {total:.0f} kcal, at {log_time} today.")


def daily_summary(target_date=None):
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT foods.name, log.quantity, foods.unit, foods.calories_per_unit, log.log_time
        FROM log
        JOIN foods ON log.food_id = foods.id
        WHERE log.log_date = ?
        ORDER BY log.log_time
    """, (target_date,))
    rows = cur.fetchall()
    conn.close()

    print(f"\n--- Summary for {target_date} ---")
    if not rows:
        print("No entries logged for this date.")
        return

    total = 0.0
    for name, qty, unit, cals_per_unit, log_time in rows:
        subtotal = qty * cals_per_unit
        total += subtotal
        print(f"  {log_time}  {qty:g} {unit} of {name:<30} {subtotal:6.0f} kcal")

    print(f"\nTotal: {total:.0f} kcal")

    goal = get_setting("daily_goal")
    if goal:
        goal = float(goal)
        diff = goal - total
        if diff >= 0:
            print(f"Goal: {goal:.0f} kcal — you have {diff:.0f} kcal remaining.")
        else:
            print(f"Goal: {goal:.0f} kcal — you are {abs(diff):.0f} kcal over.")


def set_goal():
    try:
        goal = float(input("Enter your daily calorie goal (kcal): ").strip())
        set_setting("daily_goal", goal)
        print(f"Daily goal set to {goal:.0f} kcal.")
    except ValueError:
        print("Invalid number.")


def view_history():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT log.log_date, SUM(log.quantity * foods.calories_per_unit) as total
        FROM log
        JOIN foods ON log.food_id = foods.id
        GROUP BY log.log_date
        ORDER BY log.log_date DESC
        LIMIT 14
    """)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("\nNo history yet.")
        return
    print("\n--- Last 14 days ---")
    for d, total in rows:
        print(f"  {d}: {total:.0f} kcal")


def delete_last_entry():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT log.id, foods.name, log.quantity, log.log_date, log.log_time
        FROM log JOIN foods ON log.food_id = foods.id
        ORDER BY log.id DESC LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        print("\nNo entries to delete.")
        conn.close()
        return
    log_id, name, qty, log_date, log_time = row
    confirm = input(f"Delete last entry: {qty:g} x {name} on {log_date} {log_time}? (y/n): ").strip().lower()
    if confirm == "y":
        cur.execute("DELETE FROM log WHERE id = ?", (log_id,))
        conn.commit()
        print("Deleted.")
    conn.close()


# ---------- Menu ----------

def main_menu():
    init_db()
    seed_default_foods()

    menu = """
========================================
   CALORIE TRACKER
========================================
1. Log food eaten
2. View today's summary
3. View a past date's summary
4. Add a new food to the database
5. List all foods
6. Set daily calorie goal
7. View last 14 days history
8. Delete last log entry
9. Exit
"""
    while True:
        print(menu)
        choice = input("Choose an option (1-9): ").strip()

        if choice == "1":
            log_entry()
        elif choice == "2":
            daily_summary()
        elif choice == "3":
            d = input("Enter date (YYYY-MM-DD): ").strip()
            daily_summary(d)
        elif choice == "4":
            add_food()
        elif choice == "5":
            list_foods()
        elif choice == "6":
            set_goal()
        elif choice == "7":
            view_history()
        elif choice == "8":
            delete_last_entry()
        elif choice == "9":
            print("Goodbye! Stay healthy.")
            break
        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main_menu()
