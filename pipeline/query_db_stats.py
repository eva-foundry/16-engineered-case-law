"""Query database to understand available data domain for filtering."""
import sqlite3
from pathlib import Path
from collections import Counter

db_path = Path(__file__).parent / ".." / ".." / "05-Extract-Cases" / "data" / "SPO-Data-Analysis" / "juris_inventory.sqlite"
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=" * 80)
print("DATABASE STATISTICS - Understanding Available Data Domain")
print("=" * 80)

# Get years distribution for EN
print("\n📅 ENGLISH CASES BY YEAR:")
c.execute("""
    SELECT 
        SUBSTR(publication_date, 1, 4) as year,
        COUNT(DISTINCT SUBSTR(id, 1, INSTR(id || '_pages_', '_pages_') - 1)) as unique_cases,
        COUNT(*) as total_pages
    FROM pages_en
    WHERE publication_date IS NOT NULL AND publication_date != ''
    GROUP BY year
    ORDER BY year DESC
    LIMIT 30
""")
en_years = c.fetchall()
for year, cases, pages in en_years:
    print(f"  {year}: {cases:>5} cases ({pages:>6} pages)")

# Get years distribution for FR
print("\n📅 FRENCH CASES BY YEAR:")
c.execute("""
    SELECT 
        SUBSTR(publication_date, 1, 4) as year,
        COUNT(DISTINCT SUBSTR(id, 1, INSTR(id || '_pages_', '_pages_') - 1)) as unique_cases,
        COUNT(*) as total_pages
    FROM pages_fr
    WHERE publication_date IS NOT NULL AND publication_date != ''
    GROUP BY year
    ORDER BY year DESC
    LIMIT 30
""")
fr_years = c.fetchall()
for year, cases, pages in fr_years:
    print(f"  {year}: {cases:>5} cases ({pages:>6} pages)")

# Get tribunal distribution
print("\n🏛️  TRIBUNAL DISTRIBUTION (EN):")
c.execute("""
    SELECT 
        source_name,
        COUNT(DISTINCT SUBSTR(id, 1, INSTR(id || '_pages_', '_pages_') - 1)) as unique_cases,
        COUNT(*) as total_pages
    FROM pages_en
    WHERE source_name IS NOT NULL
    GROUP BY source_name
    ORDER BY unique_cases DESC
""")
for tribunal, cases, pages in c.fetchall():
    print(f"  {tribunal}: {cases:>6} cases ({pages:>7} pages)")

print("\n🏛️  TRIBUNAL DISTRIBUTION (FR):")
c.execute("""
    SELECT 
        source_name,
        COUNT(DISTINCT SUBSTR(id, 1, INSTR(id || '_pages_', '_pages_') - 1)) as unique_cases,
        COUNT(*) as total_pages
    FROM pages_fr
    WHERE source_name IS NOT NULL
    GROUP BY source_name
    ORDER BY unique_cases DESC
""")
for tribunal, cases, pages in c.fetchall():
    print(f"  {tribunal}: {cases:>6} cases ({pages:>7} pages)")

# Check 2025 specifically
print("\n🔍 2025 CASES DETAILED:")
print("\nENGLISH 2025:")
c.execute("""
    SELECT 
        source_name,
        COUNT(DISTINCT SUBSTR(id, 1, INSTR(id || '_pages_', '_pages_') - 1)) as unique_cases
    FROM pages_en
    WHERE publication_date LIKE '2025%'
    GROUP BY source_name
    ORDER BY source_name
""")
en_2025 = c.fetchall()
total_en_2025 = sum(cases for _, cases in en_2025)
for tribunal, cases in en_2025:
    print(f"  {tribunal}: {cases} cases")
print(f"  TOTAL EN 2025: {total_en_2025} cases")

print("\nFRENCH 2025:")
c.execute("""
    SELECT 
        source_name,
        COUNT(DISTINCT SUBSTR(id, 1, INSTR(id || '_pages_', '_pages_') - 1)) as unique_cases
    FROM pages_fr
    WHERE publication_date LIKE '2025%'
    GROUP BY source_name
    ORDER BY source_name
""")
fr_2025 = c.fetchall()
total_fr_2025 = sum(cases for _, cases in fr_2025)
for tribunal, cases in fr_2025:
    print(f"  {tribunal}: {cases} cases")
print(f"  TOTAL FR 2025: {total_fr_2025} cases")

print(f"\n✅ TOTAL 2025 CASES AVAILABLE: {total_en_2025 + total_fr_2025} ({total_en_2025} EN + {total_fr_2025} FR)")

# Date range
print("\n📆 DATE RANGE:")
c.execute("SELECT MIN(publication_date), MAX(publication_date) FROM pages_en WHERE publication_date IS NOT NULL")
en_range = c.fetchone()
c.execute("SELECT MIN(publication_date), MAX(publication_date) FROM pages_fr WHERE publication_date IS NOT NULL")
fr_range = c.fetchone()
print(f"  EN: {en_range[0]} to {en_range[1]}")
print(f"  FR: {fr_range[0]} to {fr_range[1]}")

print("\n" + "=" * 80)
print("RECOMMENDATION: Use --stratify-by year --per-group X to get X cases per year")
print("                or implement year filter in db_loader.py for specific year")
print("=" * 80)

conn.close()
