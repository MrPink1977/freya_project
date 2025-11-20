# test_memory.py
import sqlite3
from pathlib import Path

# Go up one level from tests/ to project root
db_path = Path(__file__).parent.parent / "data" / "freya_memory.db"

print(f"Looking for database at: {db_path}")

if not db_path.exists():
    print(f"ERROR: Database not found at {db_path}")
    print("Has Freya created the database yet?")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.execute(
    "SELECT role, content, importance, created_at FROM memories ORDER BY created_at DESC LIMIT 20"
)

print("\n=== RECENT MEMORIES ===")
count = 0
for row in cursor:
    count += 1
    print(f"\n[{row[0]}] importance={row[2]}")
    print(f"  {row[1]}")
    print(f"  (stored: {row[3]})")

if count == 0:
    print("\n(No memories stored yet)")

conn.close()
