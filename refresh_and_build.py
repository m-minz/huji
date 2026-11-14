"""
refresh_and_build.py - HUJI Course Catalog Database Refresh & GitHub Pages Builder

Usage:
    python refresh_and_build.py --mode exams          # Update exam dates & locations (~2 mins)
    python refresh_and_build.py --mode full           # Full catalog & syllabus scrape
    python refresh_and_build.py --mode compress-only  # Re-compress DB & update version.json
"""

import sys
import os
import time
import gzip
import shutil
import sqlite3
import json
import argparse
from datetime import datetime

# Windows console encoding fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DB_PATH = "shnaton.db"
GZ_PATH = "shnaton.db.gz"
VERSION_PATH = "version.json"

def vacuum_and_optimize(db_path: str = DB_PATH):
    print(f"[*] Optimizing and vacuuming {db_path}...")
    t0 = time.time()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA page_size = 4096")
    conn.execute("VACUUM")
    conn.execute("ANALYZE")
    conn.close()
    mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"[+] SQLite database optimized in {time.time()-t0:.2f}s (Size: {mb:.2f} MB)")

def compress_database(db_path: str = DB_PATH, gz_path: str = GZ_PATH):
    print(f"[*] Compressing {db_path} -> {gz_path}...")
    t0 = time.time()
    with open(db_path, "rb") as f_in:
        with gzip.open(gz_path, "wb", compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    orig_mb = os.path.getsize(db_path) / (1024 * 1024)
    gz_mb = os.path.getsize(gz_path) / (1024 * 1024)
    print(f"[+] Compression completed in {time.time()-t0:.2f}s: {orig_mb:.2f} MB -> {gz_mb:.2f} MB ({gz_mb/orig_mb*100:.1f}%)")

def update_version_metadata(db_path: str = DB_PATH, gz_path: str = GZ_PATH, ver_path: str = VERSION_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    courses_count = cur.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    exams_count = cur.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
    teachers_count = cur.execute("SELECT COUNT(DISTINCT name_he) FROM session_teachers").fetchone()[0]
    conn.close()

    gz_mb = round(os.path.getsize(gz_path) / (1024 * 1024), 2)
    now_ts = int(time.time())
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    metadata = {
        "version": now_ts,
        "updated_at": now_iso,
        "courses_count": courses_count,
        "exams_count": exams_count,
        "teachers_count": teachers_count,
        "db_size_mb": gz_mb,
        "description": "HUJI Course Catalog Database - 2026/2027"
    }

    with open(ver_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"[+] Updated {ver_path}: version={now_ts}, courses={courses_count}, exams={exams_count}, size={gz_mb}MB")

def main():
    parser = argparse.ArgumentParser(description="Refresh Shnaton Database and Build for GitHub Pages")
    parser.add_argument("--mode", choices=["exams", "full", "compress-only"], default="compress-only",
                        help="Refresh mode: 'exams' (fast), 'full' (complete scrape), 'compress-only' (repackage existing db)")
    parser.add_argument("--workers", type=int, default=8, help="Number of concurrent scraper workers")
    parser.add_argument("--year", type=int, default=2027, help="Academic year (default: 2027)")
    args = parser.parse_args()

    print("=" * 60)
    print(f" HUJI Shnaton DB Refresh & GitHub Pages Build [Mode: {args.mode}]")
    print("=" * 60)

    if args.mode == "exams":
        import scraper
        print(f"[*] Starting exams scrape for Academic Year {args.year}...")
        scraper.run_exams_only(year=args.year, db_path=DB_PATH, max_workers=args.workers)

    elif args.mode == "full":
        import scraper
        print(f"[*] Starting full catalog & deep scrape for Academic Year {args.year}...")
        client = scraper.ShnatonClient()
        scraper.scrape(year=args.year, faculty_codes=None, deep=True, with_exams=True,
                       db_path=DB_PATH, max_workers=args.workers)

    # Always optimize, compress and update version metadata
    vacuum_and_optimize(DB_PATH)
    compress_database(DB_PATH, GZ_PATH)
    update_version_metadata(DB_PATH, GZ_PATH, VERSION_PATH)

    print("\n" + "=" * 60)
    print(" SUCCESS: Database refreshed & GitHub Pages files ready to publish!")
    print("=" * 60)

if __name__ == "__main__":
    main()
