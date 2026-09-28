import sqlite3
import json
import os
from . import data

DB_PATH = os.environ.get("TODARMAL_DB", os.path.join(os.path.dirname(__file__), "..", "todarmal.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    access_code TEXT UNIQUE NOT NULL,
    treasury REAL NOT NULL DEFAULT 1000,
    crisis_id TEXT NOT NULL,
    production_used REAL NOT NULL DEFAULT 0,
    trade_units_used REAL NOT NULL DEFAULT 0,
    trade_tier INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    created_at REAL NOT NULL,
    last_seen REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS team_resources (
    team_id INTEGER NOT NULL REFERENCES teams(id),
    resource_id TEXT NOT NULL,
    PRIMARY KEY (team_id, resource_id)
);

CREATE TABLE IF NOT EXISTS factories (
    id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    level INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inventory (
    team_id INTEGER NOT NULL REFERENCES teams(id),
    item_id TEXT NOT NULL,          -- "res:<id>" or "prod:<id>"
    qty REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (team_id, item_id)
);

CREATE TABLE IF NOT EXISTS market_listings (
    id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    item_id TEXT NOT NULL,
    qty REAL NOT NULL,
    ask_price REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES market_listings(id),
    buyer_team_id INTEGER NOT NULL REFERENCES teams(id),
    seller_team_id INTEGER NOT NULL REFERENCES teams(id),
    item_id TEXT NOT NULL,
    qty REAL NOT NULL,
    price_total REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY,
    team_id INTEGER,
    kind TEXT NOT NULL,             -- extract / produce / factory / trade_upgrade / trade
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS game_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_db():
    fresh = not os.path.exists(DB_PATH)
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    if fresh:
        seed(conn)
    else:
        # make sure game_state defaults exist even on an existing db
        ensure_state_defaults(conn)
    conn.close()


def ensure_state_defaults(conn):
    defaults = {"round": "1", "frozen": "0"}
    for k, v in defaults.items():
        row = conn.execute("SELECT 1 FROM game_state WHERE key=?", (k,)).fetchone()
        if not row:
            conn.execute("INSERT INTO game_state (key, value) VALUES (?, ?)", (k, v))
    conn.commit()


def seed(conn):
    ensure_state_defaults(conn)
    for c in data.COUNTRIES:
        cur = conn.execute(
            "INSERT INTO teams (name, access_code, treasury, crisis_id) VALUES (?, ?, ?, ?)",
            (c["name"], c["access_code"], data.STARTING_TREASURY, c["crisis"]),
        )
        team_id = cur.lastrowid
        for r in c["resources"]:
            conn.execute("INSERT INTO team_resources (team_id, resource_id) VALUES (?, ?)", (team_id, r))
        conn.execute("INSERT INTO factories (team_id, level) VALUES (?, 0)", (team_id,))
    conn.commit()
