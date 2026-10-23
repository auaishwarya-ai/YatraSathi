"""Delete the SQLite database so it is recreated (with fresh demo data) on the next start.

    python scripts/reset_db.py
"""
from pathlib import Path

db = Path(__file__).resolve().parent.parent / "instance" / "yatrasathi.db"
if db.exists():
    db.unlink()
    print("Deleted", db)
else:
    print("No database found - nothing to reset.")
print("Run  python app.py  to recreate it.")
