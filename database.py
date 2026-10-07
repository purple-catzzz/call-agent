import sqlite3

DB_FILE = "restaurant.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Tables tracking 20 instances
    c.execute('''
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'Available'
        )
    ''')
    
    # Orders tracking extracted food items
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            item_name TEXT,
            quantity INTEGER,
            price INTEGER,
            FOREIGN KEY (table_id) REFERENCES tables(id)
        )
    ''')
    
    # Transcripts for viewing the raw call log
    c.execute('''
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            text TEXT,
            FOREIGN KEY (table_id) REFERENCES tables(id)
        )
    ''')
    
    # Initialize exactly 20 tables if the database is fresh
    c.execute("SELECT COUNT(*) FROM tables")
    count = c.fetchone()[0]
    if count < 20:
        for i in range(1, 21):
            c.execute("INSERT OR IGNORE INTO tables (id, status) VALUES (?, ?)", (i, "Available"))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
