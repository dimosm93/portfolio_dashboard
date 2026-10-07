import sqlite3
import libsql_client

# 1. Stoixeia syndesis Turso
# Prosoxi: Sto libsql-client xrisimopoiei https:// anti gia libsql://
TURSO_URL = "https://portfoliodb-dimosm93.aws-eu-west-1.turso.io"  # Vale to URL sou allagmeno se https://
TURSO_TOKEN ="eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTEzODQ3MjgsImlkIjoiMDFhMTE2ZDktMDIwMS03MDI4LTk5NDMtZjhiMzkwZjkyYWJjIiwia2lkIjoiMW4wSUxDbVpKbDBIb3JJd2tqeE5EbmhST3dIdW1pZnZZUnRsR0IzMUZHWSIsInJpZCI6IjFmNzAyZTY3LThiNGYtNDAwMC1iMWJiLTQ1ZjE3MmRjMDY4YSJ9.RbAciAz2-txlJLtZgB5oUspxlmGDKBi8yO7IXU7ki-SRzAghNVolU9RwLp0VLwNhIoSqj6vfjjVhHhr65w4WBQ"

# 2. Anagnosi apo tin topiki SQLite
local_conn = sqlite3.connect('portfolio.db')
local_cursor = local_conn.cursor()

local_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
if not local_cursor.fetchone():
    print("H topiki vasi einai adeia i den vretheike o pinakas transactions.")
    local_conn.close()
    exit()

local_cursor.execute("SELECT date, ticker, category, exchange, action, quantity, price, fee, foreign_tax FROM transactions")
rows = local_cursor.fetchall()
local_conn.close()

print(f"Vretheikan {len(rows)} synallages stin topiki vasi.")

# 3. Syndesi me Turso Cloud (Pure Python Sync Client)
client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

# Dimiourgia pinaka
client.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        ticker TEXT,
        category TEXT,
        exchange TEXT,
        action TEXT,
        quantity REAL,
        price REAL,
        fee REAL DEFAULT 0.0,
        foreign_tax REAL DEFAULT 0.0
    )
''')

# Eisagogi εγγραφων
for row in rows:
    client.execute(
        "INSERT INTO transactions (date, ticker, category, exchange, action, quantity, price, fee, foreign_tax) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        list(row)
    )

print("H metafora oloklirotheke me epitychia sto Turso Cloud!")
client.close()