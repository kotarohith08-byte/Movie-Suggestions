"""
database.py - Persistent SQLite Storage for CineMatch AI
========================================================
Manages local persistent user ratings, favorite genre preferences,
and watch history using thread-safe, parameterized SQLite operations.
"""

import os
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")
DB_PATH = os.path.join(DB_DIR, "cinematch.db")


@contextmanager
def get_db_connection():
    """Context manager that yields a SQLite connection and guarantees closing it."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initializes SQLite schema if not already present."""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # User ratings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_ratings (
                user_id TEXT NOT NULL,
                movie_id INTEGER NOT NULL,
                rating REAL NOT NULL CHECK(rating >= 0.5 AND rating <= 5.0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, movie_id)
            );
        """)

        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                preferred_genres TEXT NOT NULL, -- JSON string array
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Watch history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watch_history (
                user_id TEXT NOT NULL,
                movie_id INTEGER NOT NULL,
                watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, movie_id)
            );
        """)

        conn.commit()
    print(f"[OK] Database initialized at: {DB_PATH}")


def save_rating(user_id: str, movie_id: int, rating: float) -> Dict:
    """
    Inserts or updates a 0.5-5.0 star movie rating for the given user.
    Uses parameterized query to prevent SQL injection.
    """
    rating = round(float(rating), 1)
    if rating < 0.5 or rating > 5.0:
        raise ValueError("Rating must be between 0.5 and 5.0 stars.")

    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_ratings (user_id, movie_id, rating, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, movie_id) DO UPDATE SET
                rating = excluded.rating,
                updated_at = excluded.updated_at
        """, (str(user_id), int(movie_id), rating, now, now))
        conn.commit()

    return {"user_id": str(user_id), "movie_id": int(movie_id), "rating": rating, "updated_at": now}


def get_user_ratings(user_id: str) -> List[Dict]:
    """Retrieves all ratings submitted by a specific user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT movie_id, rating, updated_at
            FROM user_ratings
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (str(user_id),))
        rows = cursor.fetchall()
        return [{"movie_id": row["movie_id"], "rating": row["rating"], "updated_at": row["updated_at"]} for row in rows]


def get_user_rating_for_movie(user_id: str, movie_id: int) -> Optional[float]:
    """Retrieves a single rating by a user for a specific movie if present."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rating FROM user_ratings WHERE user_id = ? AND movie_id = ?
        """, (str(user_id), int(movie_id)))
        row = cursor.fetchone()
        return float(row["rating"]) if row else None


def delete_rating(user_id: str, movie_id: int) -> bool:
    """Deletes a rating record."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_ratings WHERE user_id = ? AND movie_id = ?", (str(user_id), int(movie_id)))
        conn.commit()
        return cursor.rowcount > 0


def save_user_preferences(user_id: str, genres: List[str]):
    """Stores user selected preferred genres."""
    json_str = json.dumps(genres)
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_preferences (user_id, preferred_genres, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                preferred_genres = excluded.preferred_genres,
                updated_at = excluded.updated_at
        """, (str(user_id), json_str, now))
        conn.commit()


def get_user_preferences(user_id: str) -> List[str]:
    """Returns preferred genres list for the user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT preferred_genres FROM user_preferences WHERE user_id = ?", (str(user_id),))
        row = cursor.fetchone()
        if row and row["preferred_genres"]:
            try:
                return json.loads(row["preferred_genres"])
            except Exception:
                return []
        return []


def mark_movie_watched(user_id: str, movie_id: int) -> bool:
    """Marks movie as watched so hybrid engine knows to filter it."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO watch_history (user_id, movie_id)
            VALUES (?, ?)
        """, (str(user_id), int(movie_id)))
        conn.commit()
        return True


def get_watched_movie_ids(user_id: str) -> List[int]:
    """Returns set of movie IDs already watched by the user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT movie_id FROM watch_history WHERE user_id = ?", (str(user_id),))
        rows = cursor.fetchall()
        return [row["movie_id"] for row in rows]


if __name__ == "__main__":
    init_db()
