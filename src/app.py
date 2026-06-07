"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3
from typing import Dict, Any

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# SQLite database file
DB_PATH = current_dir / "data.db"

# Seed data - used to initialize the database on first run
_SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed initial data if empty."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        name TEXT PRIMARY KEY,
        description TEXT,
        schedule TEXT,
        max_participants INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_name TEXT,
        email TEXT,
        FOREIGN KEY(activity_name) REFERENCES activities(name)
    )
    """)

    # Seed activities if table is empty
    cur.execute("SELECT COUNT(*) as cnt FROM activities")
    if cur.fetchone()[0] == 0:
        for name, info in _SEED_ACTIVITIES.items():
            cur.execute(
                "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                (name, info["description"], info["schedule"], info["max_participants"])
            )
            for email in info.get("participants", []):
                cur.execute(
                    "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
                    (name, email)
                )
    conn.commit()
    conn.close()


def activities_to_dict() -> Dict[str, Any]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM activities")
    activities = {}
    rows = cur.fetchall()
    for row in rows:
        name = row["name"]
        cur.execute("SELECT email FROM participants WHERE activity_name = ?", (name,))
        participants = [r["email"] for r in cur.fetchall()]
        activities[name] = {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": participants
        }
    conn.close()
    return activities


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities_to_dict()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM activities WHERE name = ?", (activity_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check if already signed up
    cur.execute("SELECT COUNT(*) FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
    if cur.fetchone()[0] > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Student is already signed up")

    # Check max participants
    cur.execute("SELECT COUNT(*) FROM participants WHERE activity_name = ?", (activity_name,))
    current_count = cur.fetchone()[0]
    max_participants = row["max_participants"]
    if max_participants is not None and current_count >= max_participants:
        conn.close()
        raise HTTPException(status_code=400, detail="Activity is full")

    # Insert participant
    cur.execute("INSERT INTO participants (activity_name, email) VALUES (?, ?)", (activity_name, email))
    conn.commit()
    conn.close()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM activities WHERE name = ?", (activity_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check if student is signed up
    cur.execute("SELECT id FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
    participant = cur.fetchone()
    if not participant:
        conn.close()
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    # Remove participant
    cur.execute("DELETE FROM participants WHERE id = ?", (participant["id"],))
    conn.commit()
    conn.close()
    return {"message": f"Unregistered {email} from {activity_name}"}


# Initialize DB at startup
init_db()
