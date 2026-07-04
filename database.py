import sqlite3

conn = sqlite3.connect("levelgroup.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT,
    efc_balance INTEGER DEFAULT 0,
    uzs_balance INTEGER DEFAULT 0
)
""")

conn.commit()
