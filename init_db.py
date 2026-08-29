import sqlite3
import os

DB_PATH = "rfp_evaluation.db"

def init_db():
    # Remove existing db if it exists for a fresh start
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create evaluation_criteria table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluation_criteria (
            criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            weight REAL NOT NULL,
            max_score INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
    ''')

    # Create rfp_runs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rfp_runs (
            rfp_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL
        )
    ''')

    # Create supplier_results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplier_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfp_run_id INTEGER NOT NULL,
            supplier_name TEXT NOT NULL,
            submission_date TEXT NOT NULL,
            experience_rating INTEGER NOT NULL,
            absolute_score REAL,
            ppi REAL,
            final_rank INTEGER,
            result_json TEXT,
            FOREIGN KEY(rfp_run_id) REFERENCES rfp_runs(rfp_run_id)
        )
    ''')

    # Seed the criteria
    criteria_data = [
        ("Technical Capability", "Architecture, integrations, scalability, technical fit", 0.30, 10, 1),
        ("Implementation Plan", "Timeline, milestones, staffing, risk plan", 0.20, 10, 1),
        ("Commercial Value", "Pricing clarity, total cost, assumptions", 0.20, 10, 1),
        ("Security & Compliance", "Controls, certifications, privacy, auditability", 0.20, 10, 1),
        ("Support & Experience", "Support model, similar projects, references", 0.10, 10, 1)
    ]

    cursor.executemany('''
        INSERT INTO evaluation_criteria (name, description, weight, max_score, is_active)
        VALUES (?, ?, ?, ?, ?)
    ''', criteria_data)

    conn.commit()
    conn.close()
    print("Database initialized and seeded successfully.")

if __name__ == "__main__":
    init_db()
