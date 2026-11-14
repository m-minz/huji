"""
Scraper for Hebrew University Course Catalog (שנתון האוניברסיטה העברית | Shnaton).
Fetches faculties, departments, courses, schedules, locations, and teachers from https://shnaton.huji.ac.il/
"""

import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

import database

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "https://shnaton.huji.ac.il/api"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class ShnatonClient:
    def __init__(self, base_url: str = BASE_URL, user_agent: str = DEFAULT_USER_AGENT, max_retries: int = 4):
        self.base_url = base_url
        self.user_agent = user_agent
        self.max_retries = max_retries

    def _request(self, endpoint: str, method: str = "GET", body: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        data_bytes = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
        }
        if data_bytes:
            headers["Content-Type"] = "application/json"

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
            except (urllib.error.HTTPError, urllib.error.URLError, ConnectionResetError, TimeoutError, Exception) as e:
                last_err = e
                # Don't retry 404
                if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                    return None
                wait_time = attempt * 1.5
                time.sleep(wait_time)

        print(f"\n[Warning] Failed request to {endpoint} after {self.max_retries} attempts: {last_err}")
        return None

    def get_active_years(self) -> List[Dict[str, Any]]:
        return self._request("/reference-data/active-years") or []

    def get_faculties(self) -> List[Dict[str, Any]]:
        return self._request("/faculties") or []

    def get_departments(self, faculty_code: str, year: int) -> List[Dict[str, Any]]:
        return self._request(f"/faculties/{faculty_code}/departments?year={year}") or []

    def search_courses(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        res = self._request("/courses/search-advanced", method="POST", body=query_params)
        return res if isinstance(res, list) else []

    def get_groups_with_sessions_batch(self, course_ids: List[int], year: int) -> Dict[str, List[Dict[str, Any]]]:
        if not course_ids:
            return {}
        res = self._request(f"/courses/groups-with-sessions?year={year}", method="POST", body={"courseIds": course_ids})
        return res if isinstance(res, dict) else {}

    def get_assignments(self, course_id: int, year: int) -> List[Dict[str, Any]]:
        res = self._request(f"/assignments?year={year}&courseId={course_id}")
        return res if isinstance(res, list) else []

    def get_syllabus(self, course_code: str, year: int) -> Optional[Dict[str, Any]]:
        return self._request(f"/syllabus?courseCode={course_code}&year={year}")

    def get_roadmaps_by_course(self, course_code: str, year: int) -> List[Dict[str, Any]]:
        res = self._request(f"/yearly-roadmaps/search-by-course?courseCode={course_code}&thresholdYear={year}")
        return res if isinstance(res, list) else []

    def get_requirements(self, course_code: str, year: int) -> Optional[Dict[str, Any]]:
        return self._request(f"/courses/code/{course_code}/requirements?year={year}")


def scrape(
    year: Optional[int] = None,
    test_mode: bool = False,
    all_catalog: bool = False,
    deep_enrichment: bool = True,
    with_exams: bool = False,
    db_path: str = database.DEFAULT_DB_PATH,
    export_json_path: Optional[str] = "shnaton_courses.json",
    export_csv_path: Optional[str] = "shnaton_sessions.csv",
    batch_size: int = 100,
    max_workers: int = 4
) -> None:
    client = ShnatonClient()
    database.init_db(db_path)

    print("=" * 60)
    print("  Hebrew University Course Catalog Scraper (שנתון העברית)")
    print("=" * 60)

    # 1. Determine target academic year
    active_years = client.get_active_years()
    current_year_info = next((y for y in active_years if y.get("current")), None)

    if year is None:
        if current_year_info:
            year = current_year_info.get("year", 2026)
        else:
            year = 2026

    hebrew_year = next((y.get("hebrewYear", "") for y in active_years if y.get("year") == year), "")
    print(f"[*] Target Academic Year: {year} ({hebrew_year})")

    # 2. Fetch faculties
    print("[*] Fetching faculties...")
    faculties = client.get_faculties()
    database.save_faculties(faculties, db_path)
    print(f"    Saved {len(faculties)} faculties to database.")

    if test_mode:
        # In test mode, only scrape Computer Science & Engineering (Faculty code '012')
        faculties = [f for f in faculties if f.get("code") == "012"]
        print(f"[*] [TEST MODE] Scraping single faculty: 012 (Computer Science & Engineering)")

    # 3. Fetch courses
    print(f"\n[*] Fetching courses across {len(faculties)} faculties...")
    all_courses: Dict[int, Dict[str, Any]] = {}
    total_depts = 0

    for idx, f in enumerate(faculties, start=1):
        fcode = f.get("code")
        fname = f.get("name", {}).get("he", fcode) if isinstance(f.get("name"), dict) else fcode
        print(f"    [{idx}/{len(faculties)}] Faculty {fcode} - {fname}...", end="", flush=True)

        # First save departments for this faculty
        depts = client.get_departments(fcode, year)
        for d in depts:
            d["facultyCode"] = fcode
        database.save_departments(depts, db_path)
        total_depts += len(depts)

        # Split largest faculties across departments to prevent oversized chunked HTTP payloads
        if fcode in ("001", "007", "002", "021") and depts:
            print(f" (large faculty: splitting across {len(depts)} departments)...", end="", flush=True)
            fac_courses_count = 0
            for d in depts:
                dcode = str(d.get("code"))
                dept_courses = client.search_courses({"year": year, "departmentCodes": [dcode]})
                for c in dept_courses:
                    c["facultyCode"] = fcode
                    all_courses[c["id"]] = c
                    fac_courses_count += 1
            print(f" done ({fac_courses_count} courses).")
        else:
            courses = client.search_courses({"year": year, "facultyCodes": [fcode]})
            if not courses and depts:
                # Fallback to department queries if faculty query returned nothing
                for d in depts:
                    dcode = str(d.get("code"))
                    d_courses = client.search_courses({"year": year, "departmentCodes": [dcode]})
                    for c in d_courses:
                        c["facultyCode"] = fcode
                        all_courses[c["id"]] = c
            else:
                for c in courses:
                    c["facultyCode"] = fcode
                    all_courses[c["id"]] = c
            print(f" done ({len(courses)} courses).")

    print(f"[*] Total unique courses discovered: {len(all_courses)}")
    database.save_courses(list(all_courses.values()), db_path)
    print(f"    Saved {len(all_courses)} courses to database.")

    # 4. Filter courses to fetch schedules for
    # By default, fetch schedules for active courses offered this year (isLearning == 1)
    if all_catalog:
        target_courses = list(all_courses.values())
        print(f"\n[*] Fetching schedules for ALL {len(target_courses)} courses in catalog...")
    else:
        target_courses = [c for c in all_courses.values() if c.get("isLearning") == 1]
        print(f"\n[*] Fetching schedules for {len(target_courses)} ACTIVE courses offered this year (isLearning=1)...")

    target_ids = [c["id"] for c in target_courses]
    total_batches = (len(target_ids) + batch_size - 1) // batch_size
    batches = [target_ids[i:i + batch_size] for i in range(0, len(target_ids), batch_size)]

    print(f"[*] Downloading groups, class times, locations, and teachers ({total_batches} batches of {batch_size})...")

    completed_batches = 0
    total_groups_found = 0
    start_time = time.time()

    def process_batch(b_ids: List[int]) -> int:
        groups_data = client.get_groups_with_sessions_batch(b_ids, year)
        if groups_data:
            database.save_groups_and_sessions(groups_data, db_path)
            return sum(len(grps) for grps in groups_data.values())
        return 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {executor.submit(process_batch, b): b for b in batches}
        for future in as_completed(future_to_batch):
            try:
                groups_count = future.result()
                total_groups_found += groups_count
                completed_batches += 1
                percent = (completed_batches / total_batches) * 100
                print(f"\r    Progress: [{completed_batches}/{total_batches}] {percent:.1f}% (Groups found: {total_groups_found})", end="", flush=True)
            except Exception as e:
                print(f"\n[Warning] Batch processing error: {e}")

    elapsed = time.time() - start_time
    print(f"\n    Schedule scraping finished in {elapsed:.1f}s.")

    # 5. Deep Academic Enrichment (Syllabus, Roadmaps, Target Study Years, Prerequisites)
    if deep_enrichment:
        enrich_courses(client, target_courses, year, db_path, max_workers=max_workers * 2)

    # 6. Fetch exams if requested
    if with_exams:
        print(f"\n[*] Fetching exam dates and rooms for {len(target_courses)} active courses...")
        exam_courses_done = 0

        def process_exam(cid: int):
            data = client.get_assignments(cid, year)
            if data:
                database.save_exams(cid, data, db_path)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_cid = {executor.submit(process_exam, c["id"]): c["id"] for c in target_courses}
            for future in as_completed(future_to_cid):
                try:
                    future.result()
                    exam_courses_done += 1
                    if exam_courses_done % 50 == 0 or exam_courses_done == len(target_courses):
                        p = (exam_courses_done / len(target_courses)) * 100
                        print(f"\r    Exams progress: [{exam_courses_done}/{len(target_courses)}] {p:.1f}%", end="", flush=True)
                except Exception as e:
                    pass
        print("\n    Exam dates fetching complete.")

    # 7. Database Stats & Export
    stats = database.get_stats(db_path)
    print("\n" + "=" * 60)
    print("  Database Summary (shnaton.db)")
    print("=" * 60)
    print(f"  Faculties:         {stats.get('faculties', 0)}")
    print(f"  Departments:       {stats.get('departments', 0)}")
    print(f"  Catalog Courses:   {stats.get('courses', 0)}")
    print(f"  Active Courses:    {stats.get('active_courses', 0)}")
    print(f"  Teaching Groups:   {stats.get('groups', 0)}")
    print(f"  Scheduled Classes: {stats.get('sessions', 0)}")
    print(f"  Teachers Linked:   {stats.get('session_teachers', 0)}")
    if with_exams:
        print(f"  Exams Scheduled:   {stats.get('exams', 0)}")
    print("=" * 60)

    # 8. Exports
    if export_json_path:
        print(f"\n[*] Exporting JSON to {export_json_path}...")
        num_exported = database.export_json(export_json_path, db_path, active_only=not all_catalog)
        print(f"    Exported {num_exported} courses with schedules to {export_json_path}.")

    if export_csv_path:
        print(f"[*] Exporting CSV to {export_csv_path}...")
        num_csv = database.export_csv(export_csv_path, db_path)
        print(f"    Exported {num_csv} class session rows to {export_csv_path}.")

    print("\n[✔] Scraping and database generation completed successfully!")


def enrich_courses(client: ShnatonClient, courses: List[Dict[str, Any]], year: int, db_path: str, max_workers: int = 8):
    total = len(courses)
    print(f"\n[*] Enriching {total} courses with full syllabus, target study years, tracks, and prerequisites...")
    completed = 0
    t0 = time.time()

    def process_course(c):
        cid = c.get("id")
        code = str(c.get("code") or "")
        if not code or not cid:
            return
        base_code = code.split("-")[0]
        syl = client.get_syllabus(base_code, year)
        roadmaps = client.get_roadmaps_by_course(base_code, year)
        reqs = client.get_requirements(base_code, year)
        database.save_course_enrichment(cid, syl, roadmaps, reqs, db_path)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_c = {executor.submit(process_course, c): c for c in courses}
        for future in as_completed(future_to_c):
            try:
                future.result()
            except Exception:
                pass
            completed += 1
            if completed % 25 == 0 or completed == total:
                pct = (completed / total) * 100
                print(f"\r    Enrichment progress: [{completed}/{total}] {pct:.1f}%", end="", flush=True)

    elapsed = time.time() - t0
    print(f"\n    Enrichment completed in {elapsed:.1f}s.")


def run_enrichment_only(year: Optional[int] = None, db_path: str = database.DEFAULT_DB_PATH, max_workers: int = 8):
    """Enrich already-scraped courses in the database without re-downloading catalogs."""
    client = ShnatonClient()
    database.init_db(db_path)
    if year is None:
        active_years = client.get_active_years()
        curr = next((y for y in active_years if y.get("current")), None)
        year = curr.get("year", 2027) if curr else 2027

    conn = database.get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, code, name_he FROM courses WHERE is_learning = 1")
    courses = [dict(r) for r in cur.fetchall()]
    conn.close()

    print(f"[*] Found {len(courses)} active courses in database to enrich (Year {year}).")
    enrich_courses(client, courses, year, db_path, max_workers=max_workers)


def run_exams_only(year: Optional[int] = None, db_path: str = database.DEFAULT_DB_PATH, max_workers: int = 8):
    """Scrape exam schedules for all active courses in database."""
    client = ShnatonClient()
    database.init_db(db_path)
    if year is None:
        active_years = client.get_active_years()
        curr = next((y for y in active_years if y.get("current")), None)
        year = curr.get("year", 2027) if curr else 2027

    conn = database.get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, code, name_he FROM courses WHERE is_learning = 1")
    courses = [dict(r) for r in cur.fetchall()]
    conn.close()

    total = len(courses)
    print(f"[*] Scraping exam dates and rooms for {total} active courses (Academic Year {year})...")
    done = 0
    t0 = time.time()

    def process_exam(cid: int):
        data = client.get_assignments(cid, year)
        if data:
            database.save_exams(cid, data, db_path)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_cid = {executor.submit(process_exam, c["id"]): c["id"] for c in courses}
        for future in as_completed(future_to_cid):
            try:
                future.result()
            except Exception:
                pass
            done += 1
            if done % 50 == 0 or done == total:
                pct = (done / total) * 100
                print(f"\r    Progress: [{done}/{total}] {pct:.1f}%", end="", flush=True)

    elapsed = time.time() - t0
    print(f"\n[✔] Exam dates scraping finished in {elapsed:.1f}s.")


def main():
    parser = argparse.ArgumentParser(description="Hebrew University Course Catalog (Shnaton) Scraper")
    parser.add_argument("--year", type=int, default=None, help="Academic year (e.g. 2026, 2027). Defaults to current year.")
    parser.add_argument("--test", action="store_true", help="Test mode: scrapes only Computer Science faculty to verify pipeline.")
    parser.add_argument("--all-catalog", action="store_true", help="Fetch schedules for entire catalog instead of active courses.")
    parser.add_argument("--deep", action="store_true", default=True, help="Fetch syllabus, roadmaps, study years and prerequisites (default: True).")
    parser.add_argument("--enrich-only", action="store_true", help="Only enrich existing active courses in database without re-scraping.")
    parser.add_argument("--scrape-exams", action="store_true", help="Scrape exam dates and rooms for active courses.")
    parser.add_argument("--with-exams", action="store_true", help="Also fetch exam dates and rooms.")
    parser.add_argument("--db-path", default=database.DEFAULT_DB_PATH, help="SQLite database output file path.")
    parser.add_argument("--export-json", default="shnaton_courses.json", help="Path to export full courses JSON file (set empty to skip).")
    parser.add_argument("--export-csv", default="shnaton_sessions.csv", help="Path to export scheduled sessions CSV file (set empty to skip).")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent worker threads.")

    args = parser.parse_args()

    if args.scrape_exams:
        run_exams_only(year=args.year, db_path=args.db_path, max_workers=args.workers * 2)
        return

    if args.enrich_only:
        run_enrichment_only(year=args.year, db_path=args.db_path, max_workers=args.workers * 2)
        return

    export_json_path = args.export_json if args.export_json.strip() else None
    export_csv_path = args.export_csv if args.export_csv.strip() else None

    scrape(
        year=args.year,
        test_mode=args.test,
        all_catalog=args.all_catalog,
        deep_enrichment=args.deep,
        with_exams=args.with_exams,
        db_path=args.db_path,
        export_json_path=export_json_path,
        export_csv_path=export_csv_path,
        max_workers=args.workers
    )

if __name__ == "__main__":
    main()
