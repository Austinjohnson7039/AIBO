import sqlite3
import os

db_path = "ai-cafe-manager/cafe.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("SALES SCHEMA:")
    print("\nINDEXES FOR SALES:")
    for row in cursor.execute("PRAGMA index_list('sales')"):
        print(row)
    print("\nINDEXES FOR INGREDIENTS:")
    for row in cursor.execute("PRAGMA index_list('ingredients')"):
        print(row)
    conn.close()
