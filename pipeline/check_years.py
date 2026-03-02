import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / ".." / ".." / "05-Extract-Cases" / "data" / "SPO-Data-Analysis" / "juris_inventory.sqlite"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check available years
print("Checking available years in database...\n")

c.execute("""
    SELECT DISTINCT substr(decision_date, 1, 4) as year, COUNT(*) as count 
    FROM pages_en 
    WHERE decision_date IS NOT NULL AND decision_date != ''
    GROUP BY year 
    ORDER BY year DESC 
    LIMIT 10
""")
print("EN - Top 10 most recent years:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} pages")

c.execute("""
    SELECT DISTINCT substr(decision_date, 1, 4) as year, COUNT(*) as count 
    FROM pages_fr 
    WHERE decision_date IS NOT NULL AND decision_date != ''
    GROUP BY year 
    ORDER BY year DESC 
    LIMIT 10
""")
print("\nFR - Top 10 most recent years:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} pages")

# Check for 2025 specifically
c.execute("SELECT COUNT(*) FROM pages_en WHERE decision_date LIKE '2025%'")
en_2025 = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM pages_fr WHERE decision_date LIKE '2025%'")
fr_2025 = c.fetchone()[0]

print(f"\n2025 cases: EN={en_2025}, FR={fr_2025}")

conn.close()
