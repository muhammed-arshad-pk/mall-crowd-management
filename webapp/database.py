"""
SQLite storage for the web dashboard.

Two tables (see README): crowd_events logs one row per confirmed
stable-count change, never per frame. entry_exit_events logs a tracked
person appearing (ENTRY) or disappearing (EXIT).

Every write opens its own short-lived connection under a lock (WAL mode
lets that coexist with concurrent reads from HTTP request handlers).
"""
import datetime
import sqlite3
import threading
import time

import config

_write_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS crowd_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    date TEXT NOT NULL,
    previous_count INTEGER NOT NULL,
    new_count INTEGER NOT NULL,
    entered INTEGER NOT NULL,
    exited INTEGER NOT NULL,
    current_count INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('INITIAL','ENTRY','EXIT','COUNT_CHANGE')),
    camera_id TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_crowd_events_ts ON crowd_events(timestamp);

CREATE TABLE IF NOT EXISTS entry_exit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    person_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('ENTRY','EXIT')),
    camera_id TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entry_exit_ts ON entry_exit_events(timestamp);
"""


def get_connection():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA)
    conn.close()


def reset_all():
    """Wipes all stored history so a session can start completely fresh
    (e.g. before a live demo)."""
    conn = get_connection()
    with _write_lock, conn:
        conn.execute("DELETE FROM crowd_events")
        conn.execute("DELETE FROM entry_exit_events")
    conn.close()


def log_crowd_event(previous_count, new_count, event_type, camera_id=config.CAMERA_ID, ts=None):
    ts = time.time() if ts is None else ts
    entered = max(0, new_count - previous_count)
    exited = max(0, previous_count - new_count)
    date_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    conn = get_connection()
    with _write_lock, conn:
        conn.execute(
            "INSERT INTO crowd_events "
            "(timestamp, date, previous_count, new_count, entered, exited, current_count, event_type, camera_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, date_str, previous_count, new_count, entered, exited, new_count, event_type, camera_id),
        )
    conn.close()


def log_entry_exit(person_id, direction, camera_id=config.CAMERA_ID, ts=None):
    ts = time.time() if ts is None else ts
    conn = get_connection()
    with _write_lock, conn:
        conn.execute(
            "INSERT INTO entry_exit_events (timestamp, person_id, direction, camera_id) VALUES (?, ?, ?, ?)",
            (ts, person_id, direction, camera_id),
        )
    conn.close()


def recent_crowd_events(limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT timestamp AS ts, date, previous_count, new_count, entered, exited, current_count, "
        "event_type, camera_id FROM crowd_events ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def recent_entry_exit_events(limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT timestamp AS ts, person_id, direction, camera_id FROM entry_exit_events "
        "ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def summary_report():
    conn = get_connection()
    total_entered = conn.execute(
        "SELECT COUNT(*) c FROM entry_exit_events WHERE direction='ENTRY'"
    ).fetchone()["c"]
    total_exited = conn.execute(
        "SELECT COUNT(*) c FROM entry_exit_events WHERE direction='EXIT'"
    ).fetchone()["c"]
    occupancy_stats = conn.execute(
        "SELECT MAX(current_count) peak, MIN(current_count) minimum, AVG(current_count) average, "
        "COUNT(*) events FROM crowd_events"
    ).fetchone()
    conn.close()

    return {
        "total_entered": total_entered,
        "total_exited": total_exited,
        "currently_inside": max(0, total_entered - total_exited),
        "peak_occupancy": occupancy_stats["peak"] or 0,
        "min_occupancy": occupancy_stats["minimum"] or 0,
        "avg_occupancy": round(occupancy_stats["average"] or 0, 1),
        "crowd_change_events": occupancy_stats["events"] or 0,
    }
