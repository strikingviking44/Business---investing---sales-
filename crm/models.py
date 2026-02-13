"""
CRM Database Models & Schema
Uses SQLite for zero-config portable storage.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "crm.db")


def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            company TEXT,
            title TEXT,
            status TEXT DEFAULT 'lead' CHECK(status IN ('lead', 'prospect', 'customer', 'churned', 'inactive')),
            source TEXT,
            tags TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            value REAL DEFAULT 0,
            stage TEXT DEFAULT 'lead' CHECK(stage IN ('lead', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost')),
            probability INTEGER DEFAULT 10,
            expected_close TEXT,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            closed_at TEXT,
            FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            deal_id INTEGER,
            type TEXT NOT NULL CHECK(type IN ('call', 'email', 'meeting', 'note', 'task', 'follow_up')),
            subject TEXT NOT NULL,
            description TEXT DEFAULT '',
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
            FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);
        CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company);
        CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage);
        CREATE INDEX IF NOT EXISTS idx_deals_contact ON deals(contact_id);
        CREATE INDEX IF NOT EXISTS idx_activities_contact ON activities(contact_id);
        CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(type);
    """)

    conn.commit()
    conn.close()


# --- Contact Operations ---

def create_contact(data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contacts (first_name, last_name, email, phone, company, title, status, source, tags, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["first_name"], data["last_name"],
        data.get("email", ""), data.get("phone", ""),
        data.get("company", ""), data.get("title", ""),
        data.get("status", "lead"), data.get("source", ""),
        data.get("tags", ""), data.get("notes", "")
    ))
    conn.commit()
    contact_id = cursor.lastrowid
    conn.close()
    return contact_id


def get_contacts(search=None, status=None, tag=None):
    conn = get_db()
    query = "SELECT * FROM contacts WHERE 1=1"
    params = []

    if search:
        query += " AND (first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR company LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    if status:
        query += " AND status = ?"
        params.append(status)
    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")

    query += " ORDER BY updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_contact(contact_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_contact(contact_id, data):
    conn = get_db()
    fields = []
    params = []
    for key in ["first_name", "last_name", "email", "phone", "company", "title", "status", "source", "tags", "notes"]:
        if key in data:
            fields.append(f"{key} = ?")
            params.append(data[key])
    if not fields:
        conn.close()
        return False
    fields.append("updated_at = datetime('now')")
    params.append(contact_id)
    conn.execute(f"UPDATE contacts SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return True


def delete_contact(contact_id):
    conn = get_db()
    conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()
    return True


# --- Deal Operations ---

def create_deal(data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO deals (contact_id, title, value, stage, probability, expected_close, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["contact_id"], data["title"],
        data.get("value", 0), data.get("stage", "lead"),
        data.get("probability", 10), data.get("expected_close", ""),
        data.get("notes", "")
    ))
    conn.commit()
    deal_id = cursor.lastrowid
    conn.close()
    return deal_id


def get_deals(stage=None, contact_id=None):
    conn = get_db()
    query = """
        SELECT d.*, c.first_name || ' ' || c.last_name AS contact_name, c.company
        FROM deals d
        JOIN contacts c ON d.contact_id = c.id
        WHERE 1=1
    """
    params = []
    if stage:
        query += " AND d.stage = ?"
        params.append(stage)
    if contact_id:
        query += " AND d.contact_id = ?"
        params.append(contact_id)
    query += " ORDER BY d.updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_deal(deal_id):
    conn = get_db()
    row = conn.execute("""
        SELECT d.*, c.first_name || ' ' || c.last_name AS contact_name, c.company
        FROM deals d
        JOIN contacts c ON d.contact_id = c.id
        WHERE d.id = ?
    """, (deal_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_deal(deal_id, data):
    conn = get_db()
    fields = []
    params = []
    for key in ["contact_id", "title", "value", "stage", "probability", "expected_close", "notes"]:
        if key in data:
            fields.append(f"{key} = ?")
            params.append(data[key])
    if not fields:
        conn.close()
        return False
    fields.append("updated_at = datetime('now')")
    if data.get("stage") in ("closed_won", "closed_lost"):
        fields.append("closed_at = datetime('now')")
    params.append(deal_id)
    conn.execute(f"UPDATE deals SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return True


def delete_deal(deal_id):
    conn = get_db()
    conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
    conn.commit()
    conn.close()
    return True


# --- Activity Operations ---

def create_activity(data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activities (contact_id, deal_id, type, subject, description, due_date, completed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["contact_id"], data.get("deal_id"),
        data["type"], data["subject"],
        data.get("description", ""), data.get("due_date", ""),
        data.get("completed", 0)
    ))
    conn.commit()
    activity_id = cursor.lastrowid
    conn.close()
    return activity_id


def get_activities(contact_id=None, deal_id=None, activity_type=None, pending_only=False):
    conn = get_db()
    query = """
        SELECT a.*, c.first_name || ' ' || c.last_name AS contact_name
        FROM activities a
        JOIN contacts c ON a.contact_id = c.id
        WHERE 1=1
    """
    params = []
    if contact_id:
        query += " AND a.contact_id = ?"
        params.append(contact_id)
    if deal_id:
        query += " AND a.deal_id = ?"
        params.append(deal_id)
    if activity_type:
        query += " AND a.type = ?"
        params.append(activity_type)
    if pending_only:
        query += " AND a.completed = 0"
    query += " ORDER BY a.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def complete_activity(activity_id):
    conn = get_db()
    conn.execute("UPDATE activities SET completed = 1 WHERE id = ?", (activity_id,))
    conn.commit()
    conn.close()
    return True


# --- Dashboard Metrics ---

def get_dashboard_metrics():
    conn = get_db()
    metrics = {}

    # Contact counts by status
    rows = conn.execute("SELECT status, COUNT(*) as count FROM contacts GROUP BY status").fetchall()
    metrics["contacts_by_status"] = {r["status"]: r["count"] for r in rows}
    metrics["total_contacts"] = sum(metrics["contacts_by_status"].values())

    # Deal pipeline
    rows = conn.execute("""
        SELECT stage, COUNT(*) as count, COALESCE(SUM(value), 0) as total_value
        FROM deals GROUP BY stage
    """).fetchall()
    metrics["pipeline"] = {r["stage"]: {"count": r["count"], "value": r["total_value"]} for r in rows}

    # Revenue (closed won)
    row = conn.execute("SELECT COALESCE(SUM(value), 0) as revenue FROM deals WHERE stage = 'closed_won'").fetchone()
    metrics["total_revenue"] = row["revenue"]

    # Open pipeline value
    row = conn.execute("""
        SELECT COALESCE(SUM(value), 0) as pipeline_value
        FROM deals WHERE stage NOT IN ('closed_won', 'closed_lost')
    """).fetchone()
    metrics["open_pipeline_value"] = row["pipeline_value"]

    # Weighted pipeline
    row = conn.execute("""
        SELECT COALESCE(SUM(value * probability / 100.0), 0) as weighted
        FROM deals WHERE stage NOT IN ('closed_won', 'closed_lost')
    """).fetchone()
    metrics["weighted_pipeline"] = round(row["weighted"], 2)

    # Win rate
    total_closed = conn.execute("SELECT COUNT(*) as c FROM deals WHERE stage IN ('closed_won', 'closed_lost')").fetchone()["c"]
    won = conn.execute("SELECT COUNT(*) as c FROM deals WHERE stage = 'closed_won'").fetchone()["c"]
    metrics["win_rate"] = round((won / total_closed * 100), 1) if total_closed > 0 else 0

    # Pending activities
    row = conn.execute("SELECT COUNT(*) as c FROM activities WHERE completed = 0").fetchone()
    metrics["pending_activities"] = row["c"]

    # Recent activities
    rows = conn.execute("""
        SELECT a.*, c.first_name || ' ' || c.last_name AS contact_name
        FROM activities a
        JOIN contacts c ON a.contact_id = c.id
        ORDER BY a.created_at DESC LIMIT 10
    """).fetchall()
    metrics["recent_activities"] = [dict(r) for r in rows]

    conn.close()
    return metrics
