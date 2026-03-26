"""
db/client.py — Local SQLite database client.
Replaces Supabase with a local SQLite file for portability.
"""
import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from config import settings

logger = structlog.get_logger(__name__)

# --------------------------------------------------------------------------- #
#  Database Connection & Initialization
# --------------------------------------------------------------------------- #

def get_db():
    """Returns a sqlite3 connection with row factory enabled."""
    db_path = settings.SQLITE_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite schema."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create tables based on schema.sql but adapted for SQLite
    schema = [
        """
        CREATE TABLE IF NOT EXISTS businesses (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT,
            pdf_path    TEXT,
            description TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS customers (
            id           TEXT PRIMARY KEY,
            name         TEXT,
            phone        TEXT,
            email        TEXT,
            address      TEXT,
            business_id  TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id           TEXT PRIMARY KEY,
            business_id  TEXT,
            customer_id  TEXT,
            status       TEXT DEFAULT 'active',
            intent       TEXT,
            context      TEXT DEFAULT '{}',
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id            TEXT PRIMARY KEY,
            session_id    TEXT,
            business_id   TEXT,
            customer_id   TEXT,
            status        TEXT DEFAULT 'draft',
            items         TEXT DEFAULT '[]',
            subtotal      REAL DEFAULT 0,
            tax           REAL DEFAULT 0,
            total         REAL DEFAULT 0,
            delivery_type TEXT,
            address       TEXT,
            notes         TEXT,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (business_id) REFERENCES businesses(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id              TEXT PRIMARY KEY,
            session_id      TEXT,
            business_id     TEXT,
            customer_id     TEXT,
            status          TEXT DEFAULT 'scheduled',
            service         TEXT,
            provider        TEXT,
            scheduled_at    TEXT,
            duration_min    INTEGER DEFAULT 30,
            notes           TEXT,
            reminders       TEXT DEFAULT '[]',
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (business_id) REFERENCES businesses(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id           TEXT PRIMARY KEY,
            session_id   TEXT,
            business_id  TEXT,
            log_level    TEXT DEFAULT 'INFO',
            event_type   TEXT,
            tool_name    TEXT,
            input_data   TEXT,
            output_data  TEXT,
            rag_chunks   TEXT,
            duration_ms  INTEGER,
            error_msg    TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
            id           TEXT PRIMARY KEY,
            session_id   TEXT,
            role         TEXT NOT NULL,
            content      TEXT NOT NULL,
            tool_name    TEXT,
            tool_input   TEXT,
            tool_output  TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id                 TEXT PRIMARY KEY,
            business_id        TEXT,
            item_name          TEXT,
            stock_quantity     INTEGER DEFAULT 0,
            wait_time_minutes  INTEGER DEFAULT 0,
            updated_at         TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        )
        """
    ]
    
    for statement in schema:
        cursor.execute(statement)
    
    conn.commit()
    conn.close()
    logger.info("sqlite.init_done")

# Run init on import to ensure DB is ready
init_db()

# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def _row_to_dict(row):
    if not row: return None
    d = dict(row)
    # Parse JSON fields
    json_fields = ["context", "items", "reminders", "input_data", "output_data", "rag_chunks", "tool_input", "tool_output"]
    for field in json_fields:
        if field in d and d[field]:
            try:
                d[field] = json.loads(d[field])
            except:
                pass
    return d

# --------------------------------------------------------------------------- #
#  Sessions
# --------------------------------------------------------------------------- #

def create_session(business_id: str, intent: str = "unknown") -> Dict:
    conn = get_db()
    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (id, business_id, status, intent, context) VALUES (?, ?, 'active', ?, '{}')",
        (sid, business_id, intent)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def update_session_context(session_id: str, context: Dict) -> Dict:
    conn = get_db()
    conn.execute("UPDATE sessions SET context = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(context, cls=CustomEncoder), session_id))
    conn.commit()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def get_session(session_id: str) -> Optional[Dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def close_session(session_id: str) -> None:
    conn = get_db()
    conn.execute("UPDATE sessions SET status = 'closed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------- #
#  Customers
# --------------------------------------------------------------------------- #

def upsert_customer(business_id: str, name: str = None, phone: str = None,
                    email: str = None, address: str = None) -> Dict:
    conn = get_db()
    existing = None
    if phone:
        existing = conn.execute("SELECT * FROM customers WHERE phone = ? AND business_id = ?", (phone, business_id)).fetchone()
    if not existing and email:
        existing = conn.execute("SELECT * FROM customers WHERE email = ? AND business_id = ?", (email, business_id)).fetchone()
    
    if existing:
        cid = existing["id"]
        updates = []
        params = []
        if name: updates.append("name = ?"); params.append(name)
        if phone: updates.append("phone = ?"); params.append(phone)
        if email: updates.append("email = ?"); params.append(email)
        if address: updates.append("address = ?"); params.append(address)
        if updates:
            params.append(cid)
            conn.execute(f"UPDATE customers SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
    else:
        cid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO customers (id, business_id, name, phone, email, address) VALUES (?, ?, ?, ?, ?, ?)",
            (cid, business_id, name, phone, email, address)
        )
        conn.commit()
    
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    conn.close()
    return _row_to_dict(row)

# --------------------------------------------------------------------------- #
#  Inventory
# --------------------------------------------------------------------------- #

def upsert_inventory(business_id: str, item_name: str, quantity: int, wait_time_minutes: int = 0) -> Dict:
    conn = get_db()
    existing = conn.execute("SELECT * FROM inventory WHERE item_name = ? AND business_id = ?", (item_name, business_id)).fetchone()
    
    if existing:
        iid = existing["id"]
        conn.execute("UPDATE inventory SET stock_quantity = ?, wait_time_minutes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (quantity, wait_time_minutes, iid))
    else:
        iid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO inventory (id, business_id, item_name, stock_quantity, wait_time_minutes) VALUES (?, ?, ?, ?, ?)",
            (iid, business_id, item_name, quantity, wait_time_minutes)
        )
    conn.commit()
    row = conn.execute("SELECT * FROM inventory WHERE id = ?", (iid,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def check_inventory(business_id: str, item_name: str) -> Optional[Dict]:
    conn = get_db()
    # Case-insensitive partial match
    row = conn.execute("SELECT * FROM inventory WHERE business_id = ? AND item_name LIKE ?", (business_id, f"%{item_name}%")).fetchone()
    conn.close()
    return _row_to_dict(row)

def update_inventory_stock(business_id: str, item_name: str, delta: int) -> bool:
    conn = get_db()
    row = conn.execute("SELECT id, stock_quantity FROM inventory WHERE business_id = ? AND item_name LIKE ?", (business_id, f"%{item_name}%")).fetchone()
    if not row:
        conn.close()
        return False
    
    new_quantity = max(0, row["stock_quantity"] + delta)
    conn.execute("UPDATE inventory SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_quantity, row["id"]))
    conn.commit()
    conn.close()
    return True

# --------------------------------------------------------------------------- #
#  Orders
# --------------------------------------------------------------------------- #

def create_order(session_id: str, business_id: str, customer_id: str = None) -> Dict:
    conn = get_db()
    oid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO orders (id, session_id, business_id, customer_id, status, items) VALUES (?, ?, ?, ?, 'draft', '[]')",
        (oid, session_id, business_id, customer_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def update_order(order_id: str, **fields) -> Dict:
    conn = get_db()
    updates = []
    params = []
    for k, v in fields.items():
        updates.append(f"{k} = ?")
        if isinstance(v, (dict, list)):
            params.append(json.dumps(v, cls=CustomEncoder))
        else:
            params.append(v)
    params.append(order_id)
    conn.execute(f"UPDATE orders SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", params)
    conn.commit()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def get_order(order_id: str) -> Optional[Dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def get_orders_by_session(session_id: str) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders WHERE session_id = ?", (session_id,)).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def confirm_order(order_id: str) -> Dict:
    return update_order(order_id, status="confirmed")

def cancel_order(order_id: str) -> Dict:
    return update_order(order_id, status="cancelled")

# --------------------------------------------------------------------------- #
#  Appointments
# --------------------------------------------------------------------------- #

def create_appointment(session_id: str, business_id: str, service: str,
                       scheduled_at: str, duration_min: int = 30,
                       provider: str = None, customer_id: str = None,
                       notes: str = None) -> Dict:
    conn = get_db()
    aid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO appointments (id, session_id, business_id, customer_id, status, service, provider, scheduled_at, duration_min, notes) VALUES (?, ?, ?, ?, 'scheduled', ?, ?, ?, ?, ?)",
        (aid, session_id, business_id, customer_id, service, provider, scheduled_at, duration_min, notes)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM appointments WHERE id = ?", (aid,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def update_appointment(appt_id: str, **fields) -> Dict:
    conn = get_db()
    updates = []
    params = []
    for k, v in fields.items():
        updates.append(f"{k} = ?")
        if isinstance(v, (dict, list)):
            params.append(json.dumps(v, cls=CustomEncoder))
        else:
            params.append(v)
    params.append(appt_id)
    conn.execute(f"UPDATE appointments SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", params)
    conn.commit()
    row = conn.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def cancel_appointment(appt_id: str) -> Dict:
    return update_appointment(appt_id, status="cancelled")

def get_appointments_by_session(session_id: str) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM appointments WHERE session_id = ?", (session_id,)).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def check_slot_conflict(business_id: str, scheduled_at: str, duration_min: int = 30,
                         provider: str = None) -> bool:
    conn = get_db()
    query = "SELECT scheduled_at, duration_min FROM appointments WHERE business_id = ? AND status = 'scheduled'"
    params = [business_id]
    if provider:
        query += " AND provider = ?"
        params.append(provider)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    from datetime import datetime, timedelta
    try:
        new_start = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except:
        new_start = datetime.fromisoformat(scheduled_at)
    new_end = new_start + timedelta(minutes=duration_min)

    for row in rows:
        try:
            ex_start = datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
        except:
            ex_start = datetime.fromisoformat(row["scheduled_at"])
        ex_end = ex_start + timedelta(minutes=row["duration_min"] or 30)
        if new_start < ex_end and new_end > ex_start:
            return True
    return False

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        # Handle numpy types if they exist
        if hasattr(obj, "item"):
            return obj.item()
        # Handle datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Fallback to string
        return str(obj)

def write_audit_log(
    event_type: str,
    session_id: str = None,
    business_id: str = None,
    tool_name: str = None,
    input_data: Any = None,
    output_data: Any = None,
    rag_chunks: Any = None,
    duration_ms: int = None,
    error_msg: str = None,
    log_level: str = "INFO",
) -> None:
    conn = get_db()
    uid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO audit_logs (id, session_id, business_id, log_level, event_type, tool_name, input_data, output_data, rag_chunks, duration_ms, error_msg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, session_id, business_id, log_level, event_type, tool_name, 
         json.dumps(input_data, cls=CustomEncoder) if isinstance(input_data, (dict, list)) else json.dumps({"raw": str(input_data)}, cls=CustomEncoder),
         json.dumps(output_data, cls=CustomEncoder) if isinstance(output_data, (dict, list)) else json.dumps({"raw": str(output_data)}, cls=CustomEncoder),
         json.dumps(rag_chunks, cls=CustomEncoder) if isinstance(rag_chunks, list) else None,
         duration_ms, error_msg)
    )
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------- #
#  Messages
# --------------------------------------------------------------------------- #

def save_message(session_id: str, role: str, content: str,
                 tool_name: str = None, tool_input: Dict = None,
                 tool_output: Dict = None) -> Dict:
    conn = get_db()
    mid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content, tool_name, tool_input, tool_output) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (mid, session_id, role, content, tool_name, json.dumps(tool_input, cls=CustomEncoder) if tool_input else None, json.dumps(tool_output, cls=CustomEncoder) if tool_output else None)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (mid,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def get_messages(session_id: str, limit: int = 50) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at LIMIT ?", (session_id, limit)).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

# --------------------------------------------------------------------------- #
#  Business
# --------------------------------------------------------------------------- #

def get_business_by_id(business_id: str) -> Optional[Dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def update_business(business_id: str, **fields) -> Dict:
    conn = get_db()
    updates = []
    params = []
    for k, v in fields.items():
        updates.append(f"{k} = ?")
        params.append(v)
    params.append(business_id)
    conn.execute(f"UPDATE businesses SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", params)
    conn.commit()
    row = conn.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def upsert_business(name: str, business_type: str, pdf_path: str,
                    description: str = None) -> Dict:
    conn = get_db()
    existing = conn.execute("SELECT id FROM businesses WHERE name = ?", (name,)).fetchone()
    if existing:
        bid = existing["id"]
        conn.execute("UPDATE businesses SET type = ?, pdf_path = ?, description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (business_type, pdf_path, description, bid))
    else:
        bid = str(uuid.uuid4())
        conn.execute("INSERT INTO businesses (id, name, type, pdf_path, description) VALUES (?, ?, ?, ?, ?)", (bid, name, business_type, pdf_path, description))
    conn.commit()
    row = conn.execute("SELECT * FROM businesses WHERE id = ?", (bid,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def get_business_by_name(name: str) -> Optional[Dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM businesses WHERE name = ?", (name,)).fetchone()
    conn.close()
    return _row_to_dict(row)

def list_businesses() -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM businesses").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def delete_business(business_id: str) -> bool:
    """Deletes a business and all its related records (sessions, orders, etc.)"""
    conn = get_db()
    try:
        # Delete in order to satisfy FK constraints if any are enforced
        conn.execute("DELETE FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE business_id = ?)", (business_id,))
        conn.execute("DELETE FROM audit_logs WHERE business_id = ?", (business_id,))
        conn.execute("DELETE FROM appointments WHERE business_id = ?", (business_id,))
        conn.execute("DELETE FROM orders WHERE business_id = ?", (business_id,))
        conn.execute("DELETE FROM sessions WHERE business_id = ?", (business_id,))
        conn.execute("DELETE FROM customers WHERE business_id = ?", (business_id,))
        conn.execute("DELETE FROM businesses WHERE id = ?", (business_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error("db.delete_business_failed", error=str(e), business_id=business_id)
        conn.rollback()
        return False
    finally:
        conn.close()
