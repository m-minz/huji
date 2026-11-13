"""
Database module for HUJI Shnaton (Hebrew University Course Catalog).
Manages SQLite database schema, batch upserts, indexing, and JSON/CSV export.
"""

import sqlite3
import json
import csv
import os
import re
import threading
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "shnaton.db")
_db_lock = threading.Lock()

def get_connection(db_path: str = DEFAULT_DB_PATH, timeout: float = 30.0) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=timeout)
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("PRAGMA synchronous = NORMAL;")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
    except sqlite3.OperationalError:
        pass
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize database tables and indexes."""
    with _db_lock:
        conn = get_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS faculties (
            code TEXT PRIMARY KEY,
            name_he TEXT,
            name_en TEXT
        );

        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY,
            code TEXT,
            faculty_code TEXT,
            name_he TEXT,
            name_en TEXT,
            FOREIGN KEY (faculty_code) REFERENCES faculties(code)
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL,
            year INTEGER NOT NULL,
            name_he TEXT,
            name_en TEXT,
            faculty_code TEXT,
            faculty_name_he TEXT,
            faculty_name_en TEXT,
            department_id INTEGER,
            department_name_he TEXT,
            department_name_en TEXT,
            academic_points REAL,
            degree_level TEXT,
            semester INTEGER,
            semester_name_he TEXT,
            semester_name_en TEXT,
            course_structure_type TEXT,
            total_hours INTEGER,
            is_learning INTEGER DEFAULT 0,
            status_course_code INTEGER,
            study_years TEXT,
            target_degrees TEXT,
            description TEXT,
            aims TEXT,
            learning_outcomes TEXT,
            content TEXT,
            teaching_method TEXT,
            prerequisites TEXT,
            evaluation_breakdown TEXT,
            course_coordinator TEXT,
            coordinator_email TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            group_code TEXT,
            study_session_type_id INTEGER,
            study_session_type_code TEXT,
            session_type_name_he TEXT,
            session_type_name_en TEXT,
            period INTEGER,
            period_name_he TEXT,
            period_name_en TEXT,
            language_code TEXT,
            language_name_he TEXT,
            language_name_en TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            group_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            period INTEGER,
            day_of_week INTEGER,
            day_name_he TEXT,
            day_name_en TEXT,
            start_time TEXT,
            end_time TEXT,
            start_time_ms INTEGER,
            end_time_ms INTEGER,
            campus_id INTEGER,
            campus_name_he TEXT,
            campus_name_en TEXT,
            building_id INTEGER,
            building_code TEXT,
            building_name_he TEXT,
            building_name_en TEXT,
            room_id INTEGER,
            room_user_code TEXT,
            room_name_he TEXT,
            room_name_en TEXT,
            is_recorded INTEGER DEFAULT 0,
            is_live_broadcast INTEGER DEFAULT 0,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS session_teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            teacher_id INTEGER,
            name_he TEXT,
            name_en TEXT,
            email TEXT,
            title_he TEXT,
            title_en TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY,
            course_id INTEGER NOT NULL,
            assignment_id INTEGER,
            moed INTEGER,
            period INTEGER,
            period_name_he TEXT,
            period_name_en TEXT,
            start_time TEXT,
            end_time TEXT,
            rooms_summary TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS course_roadmaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            roadmap_code TEXT,
            roadmap_name_he TEXT,
            roadmap_name_en TEXT,
            department_id INTEGER,
            department_name_he TEXT,
            department_name_en TEXT,
            degree_name_he TEXT,
            scope_name_he TEXT,
            study_years TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );

        -- Indexes for high-performance querying
        CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(code);
        CREATE INDEX IF NOT EXISTS idx_courses_year ON courses(year);
        CREATE INDEX IF NOT EXISTS idx_courses_faculty ON courses(faculty_code);
        CREATE INDEX IF NOT EXISTS idx_courses_dept ON courses(department_id);
        CREATE INDEX IF NOT EXISTS idx_courses_is_learning ON courses(is_learning);
        CREATE INDEX IF NOT EXISTS idx_courses_name_he ON courses(name_he);
        CREATE INDEX IF NOT EXISTS idx_courses_name_en ON courses(name_en);
        CREATE INDEX IF NOT EXISTS idx_groups_course ON groups(course_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_group ON sessions(group_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_course ON sessions(course_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_day ON sessions(day_of_week);
        CREATE INDEX IF NOT EXISTS idx_sessions_campus ON sessions(campus_name_he);
        CREATE INDEX IF NOT EXISTS idx_sessions_building ON sessions(building_name_he);
        CREATE INDEX IF NOT EXISTS idx_sessions_room ON sessions(room_name_he);
        CREATE INDEX IF NOT EXISTS idx_teachers_session ON session_teachers(session_id);
        CREATE INDEX IF NOT EXISTS idx_teachers_name_he ON session_teachers(name_he);
        CREATE INDEX IF NOT EXISTS idx_teachers_name_en ON session_teachers(name_en);
        CREATE INDEX IF NOT EXISTS idx_exams_course ON exams(course_id);
        CREATE INDEX IF NOT EXISTS idx_roadmaps_course ON course_roadmaps(course_id);
        CREATE INDEX IF NOT EXISTS idx_roadmaps_name ON course_roadmaps(roadmap_name_he);
        CREATE INDEX IF NOT EXISTS idx_roadmaps_dept ON course_roadmaps(department_name_he);
        """)

        # Migration check: if table already exists, add missing columns
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(courses)")
        cols = {row["name"] for row in cur.fetchall()}
        new_cols = [
            ("study_years", "TEXT"),
            ("target_degrees", "TEXT"),
            ("description", "TEXT"),
            ("aims", "TEXT"),
            ("learning_outcomes", "TEXT"),
            ("content", "TEXT"),
            ("teaching_method", "TEXT"),
            ("prerequisites", "TEXT"),
            ("evaluation_breakdown", "TEXT"),
            ("course_coordinator", "TEXT"),
            ("coordinator_email", "TEXT"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in cols:
                conn.execute(f"ALTER TABLE courses ADD COLUMN {col_name} {col_type};")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_courses_study_years ON courses(study_years);")

        # Roadmap curricula cache table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS roadmap_curricula (
            roadmap_code TEXT PRIMARY KEY,
            title_he TEXT,
            title_en TEXT,
            data_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_roadmap_curricula_code ON roadmap_curricula(roadmap_code);")

        # Migration check: exams table columns
        cur.execute("PRAGMA table_info(exams)")
        exam_cols = {row["name"] for row in cur.fetchall()}
        new_exam_cols = [
            ("assignment_name_he", "TEXT"),
            ("assignment_name_en", "TEXT"),
            ("weight", "INTEGER"),
            ("campus_name_he", "TEXT"),
            ("building_name_he", "TEXT"),
            ("exam_date", "TEXT"),
        ]
        for col_name, col_type in new_exam_cols:
            if col_name not in exam_cols:
                conn.execute(f"ALTER TABLE exams ADD COLUMN {col_name} {col_type};")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_exams_date ON exams(exam_date);")

    conn.close()

DAY_MAP = {
    0: ("יום ראשון", "Sunday"),
    1: ("יום שני", "Monday"),
    2: ("יום שלישי", "Tuesday"),
    3: ("יום רביעי", "Wednesday"),
    4: ("יום חמישי", "Thursday"),
    5: ("יום שישי", "Friday"),
    6: ("יום שבת", "Saturday"),
}

def ms_to_time(ms: Optional[int]) -> Optional[str]:
    """Convert milliseconds from midnight to HH:MM string."""
    if ms is None:
        return None
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

def save_faculties(faculties: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> None:
    with _db_lock:
        conn = get_connection(db_path)
        with conn:
            conn.executemany("""
                INSERT INTO faculties (code, name_he, name_en)
                VALUES (?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name_he = excluded.name_he,
                    name_en = excluded.name_en;
            """, [
                (
                    f.get('code'),
                    f.get('name', {}).get('he') if isinstance(f.get('name'), dict) else str(f.get('name', '')),
                    f.get('name', {}).get('en') if isinstance(f.get('name'), dict) else None
                )
                for f in faculties if f.get('code')
            ])
        conn.close()

def save_departments(departments: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> None:
    with _db_lock:
        conn = get_connection(db_path)
        with conn:
            conn.executemany("""
                INSERT INTO departments (id, code, faculty_code, name_he, name_en)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    code = excluded.code,
                    faculty_code = excluded.faculty_code,
                    name_he = excluded.name_he,
                    name_en = excluded.name_en;
            """, [
                (
                    d.get('id'),
                    str(d.get('code', '')),
                    d.get('facultyCode'),
                    d.get('name', {}).get('he') if isinstance(d.get('name'), dict) else str(d.get('name', '')),
                    d.get('name', {}).get('en') if isinstance(d.get('name'), dict) else None
                )
                for d in departments if d.get('id') is not None
            ])
        conn.close()

def save_courses(courses: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> None:
    records = []
    for c in courses:
        cid = c.get('id')
        if cid is None:
            continue
        code = str(c.get('code', ''))
        year = c.get('year') or 0
        name = c.get('name') if isinstance(c.get('name'), dict) else {}
        dept_name = c.get('departmentName') if isinstance(c.get('departmentName'), dict) else {}
        fac_name = c.get('facultyName') if isinstance(c.get('facultyName'), dict) else {}
        period_name = c.get('coursePeriodName') if isinstance(c.get('coursePeriodName'), dict) else {}
        
        name_he = (name.get('he') or '').strip()
        name_en = (name.get('en') or '').strip() or None
        faculty_code = str(c.get('facultyCode') or '') or None
        faculty_name_he = (fac_name.get('he') or '').strip() or None
        faculty_name_en = (fac_name.get('en') or '').strip() or None
        department_id = c.get('departmentId')
        dept_name_he = (dept_name.get('he') or '').strip() or None
        dept_name_en = (dept_name.get('en') or '').strip() or None
        academic_points = c.get('academicPoints')
        degree_level = str(c.get('sugToar') or '') or None
        semester = c.get('coursePeriod')
        semester_name_he = (period_name.get('he') or '').strip() or None
        semester_name_en = (period_name.get('en') or '').strip() or None
        course_structure_type = c.get('courseStructureType')
        total_hours = c.get('totalHours')
        is_learning = 1 if c.get('isLearning') == 1 else 0
        status_course_code = c.get('statusCourseCode')

        records.append((
            cid, code, year, name_he, name_en,
            faculty_code, faculty_name_he, faculty_name_en,
            department_id, dept_name_he, dept_name_en,
            academic_points, degree_level,
            semester, semester_name_he, semester_name_en,
            course_structure_type, total_hours,
            is_learning, status_course_code
        ))

    with _db_lock:
        conn = get_connection(db_path)
        with conn:
            conn.executemany("""
                INSERT INTO courses (
                    id, code, year, name_he, name_en,
                    faculty_code, faculty_name_he, faculty_name_en,
                    department_id, department_name_he, department_name_en,
                    academic_points, degree_level,
                    semester, semester_name_he, semester_name_en,
                    course_structure_type, total_hours,
                    is_learning, status_course_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    code = excluded.code,
                    year = excluded.year,
                    name_he = excluded.name_he,
                    name_en = excluded.name_en,
                    faculty_code = COALESCE(excluded.faculty_code, courses.faculty_code),
                    faculty_name_he = COALESCE(excluded.faculty_name_he, courses.faculty_name_he),
                    faculty_name_en = COALESCE(excluded.faculty_name_en, courses.faculty_name_en),
                    department_id = COALESCE(excluded.department_id, courses.department_id),
                    department_name_he = COALESCE(excluded.department_name_he, courses.department_name_he),
                    department_name_en = COALESCE(excluded.department_name_en, courses.department_name_en),
                    academic_points = excluded.academic_points,
                    degree_level = excluded.degree_level,
                    semester = excluded.semester,
                    semester_name_he = excluded.semester_name_he,
                    semester_name_en = excluded.semester_name_en,
                    course_structure_type = excluded.course_structure_type,
                    total_hours = excluded.total_hours,
                    is_learning = excluded.is_learning,
                    status_course_code = excluded.status_course_code;
            """, records)
        conn.close()

def save_groups_and_sessions(groups_by_course: Dict[str, List[Dict[str, Any]]], db_path: str = DEFAULT_DB_PATH) -> None:
    """Save groups, study sessions, and teachers from /courses/groups-with-sessions API response."""
    group_records = []
    session_records = []
    teacher_records = []

    for course_id_str, groups in groups_by_course.items():
        try:
            course_id = int(course_id_str)
        except (ValueError, TypeError):
            continue

        for g in groups:
            gid = g.get('id')
            if gid is None:
                continue
            gcode = g.get('code')
            session_type = g.get('studySessionTypeName') if isinstance(g.get('studySessionTypeName'), dict) else {}
            st_name_he = (session_type.get('he') or '').strip() or None
            st_name_en = (session_type.get('en') or '').strip() or None
            period_name = g.get('periodName') if isinstance(g.get('periodName'), dict) else {}
            lang_name = g.get('languageName') if isinstance(g.get('languageName'), dict) else {}

            group_records.append((
                gid,
                course_id,
                gcode,
                g.get('studySessionTypeId'),
                str(g.get('studySessionTypeCode', '')),
                st_name_he,
                st_name_en,
                g.get('period'),
                (period_name.get('he') or '').strip() or None,
                (period_name.get('en') or '').strip() or None,
                str(g.get('languageCode', '')),
                (lang_name.get('he') or '').strip() or None,
                (lang_name.get('en') or '').strip() or None,
            ))

            for s in g.get('studySessions', []):
                sid = s.get('id')
                if sid is None:
                    continue
                dow = s.get('dayOfWeek')
                day_he, day_en = DAY_MAP.get(dow, (None, None))
                start_ms = s.get('startTime')
                end_ms = s.get('endTime')
                start_str = ms_to_time(start_ms)
                end_str = ms_to_time(end_ms)

                room = s.get('room') if isinstance(s.get('room'), dict) else {}
                building = room.get('building') if isinstance(room.get('building'), dict) else {}
                campus = building.get('campus') if isinstance(building.get('campus'), dict) else {}

                room_name = room.get('name') if isinstance(room.get('name'), dict) else {}
                building_name = building.get('name') if isinstance(building.get('name'), dict) else {}
                campus_name = campus.get('name') if isinstance(campus.get('name'), dict) else {}

                session_records.append((
                    sid,
                    gid,
                    course_id,
                    s.get('period'),
                    dow,
                    day_he,
                    day_en,
                    start_str,
                    end_str,
                    start_ms,
                    end_ms,
                    campus.get('id'),
                    (campus_name.get('he') or '').strip() or None,
                    (campus_name.get('en') or '').strip() or None,
                    building.get('id'),
                    str(building.get('code', '')),
                    (building_name.get('he') or '').strip() or None,
                    (building_name.get('en') or '').strip() or None,
                    room.get('id'),
                    str(room.get('userCode', '')),
                    (room_name.get('he') or '').strip() or None,
                    (room_name.get('en') or '').strip() or None,
                    1 if s.get('isRecorded') else 0,
                    1 if s.get('isLiveBroadcast') else 0,
                ))

                for t in s.get('teachers', []):
                    tid = t.get('id')
                    tname = t.get('name') if isinstance(t.get('name'), dict) else {}
                    title = t.get('title') if isinstance(t.get('title'), dict) else {}
                    name_he = (tname.get('he') or '').strip() or None
                    name_en = (tname.get('en') or '').strip() or None
                    title_he = (title.get('he') or '').strip() or None
                    title_en = (title.get('en') or '').strip() or None
                    email = (t.get('hujiEmail') or '').strip() or None

                    teacher_records.append((
                        sid,
                        tid,
                        name_he,
                        name_en,
                        email,
                        title_he,
                        title_en
                    ))

    with _db_lock:
        conn = get_connection(db_path)
        with conn:
            if group_records:
                conn.executemany("""
                    INSERT INTO groups (
                        id, course_id, group_code, study_session_type_id,
                        study_session_type_code, session_type_name_he, session_type_name_en,
                        period, period_name_he, period_name_en,
                        language_code, language_name_he, language_name_en
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        group_code = excluded.group_code,
                        study_session_type_id = excluded.study_session_type_id,
                        study_session_type_code = excluded.study_session_type_code,
                        session_type_name_he = excluded.session_type_name_he,
                        session_type_name_en = excluded.session_type_name_en,
                        period = excluded.period,
                        period_name_he = excluded.period_name_he,
                        period_name_en = excluded.period_name_en,
                        language_code = excluded.language_code,
                        language_name_he = excluded.language_name_he,
                        language_name_en = excluded.language_name_en;
                """, group_records)

            if session_records:
                conn.executemany("""
                    INSERT INTO sessions (
                        id, group_id, course_id, period, day_of_week,
                        day_name_he, day_name_en, start_time, end_time,
                        start_time_ms, end_time_ms,
                        campus_id, campus_name_he, campus_name_en,
                        building_id, building_code, building_name_he, building_name_en,
                        room_id, room_user_code, room_name_he, room_name_en,
                        is_recorded, is_live_broadcast
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        group_id = excluded.group_id,
                        course_id = excluded.course_id,
                        period = excluded.period,
                        day_of_week = excluded.day_of_week,
                        day_name_he = excluded.day_name_he,
                        day_name_en = excluded.day_name_en,
                        start_time = excluded.start_time,
                        end_time = excluded.end_time,
                        start_time_ms = excluded.start_time_ms,
                        end_time_ms = excluded.end_time_ms,
                        campus_id = excluded.campus_id,
                        campus_name_he = excluded.campus_name_he,
                        campus_name_en = excluded.campus_name_en,
                        building_id = excluded.building_id,
                        building_code = excluded.building_code,
                        building_name_he = excluded.building_name_he,
                        building_name_en = excluded.building_name_en,
                        room_id = excluded.room_id,
                        room_user_code = excluded.room_user_code,
                        room_name_he = excluded.room_name_he,
                        room_name_en = excluded.room_name_en,
                        is_recorded = excluded.is_recorded,
                        is_live_broadcast = excluded.is_live_broadcast;
                """, session_records)

            if teacher_records:
                sids = list({r[0] for r in teacher_records})
                conn.executemany("DELETE FROM session_teachers WHERE session_id = ?", [(s,) for s in sids])
                conn.executemany("""
                    INSERT INTO session_teachers (
                        session_id, teacher_id, name_he, name_en, email, title_he, title_en
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, teacher_records)

        conn.close()

def parse_assignment_items(course_id: int, assignments_data: List[Dict[str, Any]]) -> List[tuple]:
    """Parse raw assignments and schedules into a list of exam record tuples."""
    exam_records = []
    for item in assignments_data:
        aid = item.get('id') or item.get('assignmentId')
        weight = item.get('weight')
        def_obj = item.get('assignmentDefinition') or {}
        name_obj = def_obj.get('name') if isinstance(def_obj, dict) else {}
        assign_name_he = name_obj.get('he') if isinstance(name_obj, dict) else str(name_obj or '')
        assign_name_en = name_obj.get('en') if isinstance(name_obj, dict) else str(name_obj or '')

        # Check both schedules and exams keys from Shnaton API
        schedules = item.get('schedules') or item.get('exams') or []
        if not schedules and aid:
            # Unscheduled assignment/exam record
            eid = -int(aid)
            period = item.get('period')
            p_obj = item.get('periodName') or {}
            period_name_he = p_obj.get('he') if isinstance(p_obj, dict) else str(p_obj or '')
            period_name_en = p_obj.get('en') if isinstance(p_obj, dict) else str(p_obj or '')
            exam_records.append((
                eid, course_id, aid, None, period, period_name_he, period_name_en,
                None, None, None, assign_name_he, assign_name_en,
                weight, None, None, None
            ))
            continue

        for ex in schedules:
            eid = ex.get('id')
            if not eid:
                continue
            moed = ex.get('moed')
            period = ex.get('period') or item.get('period')
            p_obj = ex.get('periodName') or item.get('periodName') or {}
            period_name_he = p_obj.get('he') if isinstance(p_obj, dict) else str(p_obj or '')
            period_name_en = p_obj.get('en') if isinstance(p_obj, dict) else str(p_obj or '')
            start_time = ex.get('startTime')
            end_time = ex.get('endTime')
            exam_date = start_time[:10] if (start_time and len(start_time) >= 10) else None

            rooms = []
            campus_names = []
            building_names = []
            for r in ex.get('rooms', []):
                rname = r.get('name', {}).get('he') if isinstance(r.get('name'), dict) else str(r.get('name', ''))
                b_obj = r.get('building', {}) if isinstance(r.get('building'), dict) else {}
                bname = b_obj.get('name', {}).get('he') if isinstance(b_obj.get('name'), dict) else str(b_obj.get('name', ''))
                c_obj = b_obj.get('campus', {}) if isinstance(b_obj.get('campus'), dict) else {}
                cname = c_obj.get('name', {}).get('he') if isinstance(c_obj.get('name'), dict) else str(c_obj.get('name', ''))

                if bname and bname not in building_names:
                    building_names.append(bname)
                if cname and cname not in campus_names:
                    campus_names.append(cname)

                if bname and rname:
                    rooms.append(f"{bname} {rname}")
                elif rname:
                    rooms.append(rname)

            rooms_summary = ", ".join(rooms) if rooms else None
            campus_summary = ", ".join(campus_names) if campus_names else None
            building_summary = ", ".join(building_names) if building_names else None

            exam_records.append((
                eid, course_id, aid, moed, period, period_name_he, period_name_en,
                start_time, end_time, rooms_summary, assign_name_he, assign_name_en,
                weight, campus_summary, building_summary, exam_date
            ))

    return exam_records

def save_exams(course_id: int, assignments_data: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> None:
    """Save exam dates, assignments, and classrooms into exams table."""
    records = parse_assignment_items(course_id, assignments_data)
    if records:
        save_exams_batch(records, db_path)

def save_exams_batch(exam_records: List[tuple], db_path: str = DEFAULT_DB_PATH) -> None:
    """Insert or update a batch of exam records."""
    if not exam_records:
        return
    with _db_lock:
        conn = get_connection(db_path)
        with conn:
            conn.executemany("""
                INSERT INTO exams (
                    id, course_id, assignment_id, moed, period, period_name_he, period_name_en,
                    start_time, end_time, rooms_summary, assignment_name_he, assignment_name_en,
                    weight, campus_name_he, building_name_he, exam_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    rooms_summary = excluded.rooms_summary,
                    assignment_name_he = excluded.assignment_name_he,
                    assignment_name_en = excluded.assignment_name_en,
                    weight = excluded.weight,
                    campus_name_he = excluded.campus_name_he,
                    building_name_he = excluded.building_name_he,
                    exam_date = excluded.exam_date;
            """, exam_records)
        conn.close()

def get_stats(db_path: str = DEFAULT_DB_PATH) -> Dict[str, int]:
    """Return counts of rows in each table."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    stats = {}
    tables = ['faculties', 'departments', 'courses', 'groups', 'sessions', 'session_teachers', 'exams']
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        stats[t] = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM courses WHERE is_learning = 1")
    stats['active_courses'] = cursor.fetchone()[0]
    conn.close()
    return stats

def export_json(output_file: str = "shnaton_courses.json", db_path: str = DEFAULT_DB_PATH, active_only: bool = True) -> int:
    """Export all courses with nested groups, sessions, and lecturers to a JSON file."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    query = "SELECT * FROM courses"
    if active_only:
        query += " WHERE is_learning = 1"
    query += " ORDER BY code ASC"

    cur.execute(query)
    courses = [dict(row) for row in cur.fetchall()]

    for c in courses:
        cid = c['id']
        cur.execute("SELECT * FROM groups WHERE course_id = ?", (cid,))
        groups = [dict(g) for g in cur.fetchall()]
        for g in groups:
            gid = g['id']
            cur.execute("SELECT * FROM sessions WHERE group_id = ?", (gid,))
            sessions = [dict(s) for s in cur.fetchall()]
            for s in sessions:
                sid = s['id']
                cur.execute("SELECT name_he, name_en, email, title_he FROM session_teachers WHERE session_id = ?", (sid,))
                s['teachers'] = [dict(t) for t in cur.fetchall()]
            g['sessions'] = sessions
        c['groups'] = groups

        cur.execute("SELECT * FROM exams WHERE course_id = ?", (cid,))
        c['exams'] = [dict(e) for e in cur.fetchall()]

        cur.execute("""
            SELECT roadmap_name_he, department_name_he, degree_name_he, scope_name_he, study_years
            FROM course_roadmaps WHERE course_id = ?
        """, (cid,))
        c['roadmaps'] = [dict(r) for r in cur.fetchall()]

    conn.close()

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)

    return len(courses)

def export_csv(output_file: str = "shnaton_sessions.csv", db_path: str = DEFAULT_DB_PATH) -> int:
    """Export a flattened tabular CSV containing every scheduled class session with location and time."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    sql = """
    SELECT
        c.code AS course_code,
        c.name_he AS course_name_he,
        c.name_en AS course_name_en,
        c.academic_points,
        c.study_years,
        c.semester_name_he AS semester,
        c.faculty_name_he AS faculty,
        c.department_name_he AS department,
        g.group_code,
        g.session_type_name_he AS session_type,
        s.day_name_he AS day_of_week,
        s.start_time,
        s.end_time,
        s.campus_name_he AS campus,
        s.building_name_he AS building,
        s.room_name_he AS room,
        (
            SELECT GROUP_CONCAT(COALESCE(st.name_he, st.name_en), '; ')
            FROM session_teachers st
            WHERE st.session_id = s.id
        ) AS lecturers
    FROM sessions s
    JOIN groups g ON s.group_id = g.id
    JOIN courses c ON s.course_id = c.id
    ORDER BY c.code, g.group_code, s.day_of_week, s.start_time;
    """

    cur.execute(sql)
    rows = cur.fetchall()
    if rows:
        headers = rows[0].keys()
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(list(row))

    conn.close()
    return len(rows)

def _extract_text(obj: Any) -> Optional[str]:
    """Helper to extract text from a string or dict {he: ..., en: ...}."""
    if obj is None:
        return None
    if isinstance(obj, str):
        val = obj.strip()
        return val if val else None
    if isinstance(obj, dict):
        he = (obj.get("he") or "").strip()
        en = (obj.get("en") or "").strip()
        if he and en and he != en:
            return f"{he} ({en})"
        return he or en or None
    return str(obj).strip() or None

def _extract_req_courses(node: Any) -> List[str]:
    """Recursively extract courses from requirements tree."""
    res = []
    if isinstance(node, str):
        try:
            node = json.loads(node)
        except Exception:
            return [node] if node.strip() else []
    if not isinstance(node, dict):
        return res

    if node.get("type") == "COURSE":
        code = node.get("courseCode") or ""
        name = node.get("courseName")
        name_str = _extract_text(name) or ""
        res.append(f"{code} {name_str}".strip())
    elif "children" in node and isinstance(node["children"], list):
        for ch in node["children"]:
            res.extend(_extract_req_courses(ch))
    return res

def save_course_enrichment(
    course_id: int,
    syllabus: Optional[Dict[str, Any]],
    roadmaps: Optional[List[Dict[str, Any]]],
    reqs: Optional[Dict[str, Any]],
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """Save enriched academic metadata, target study years, syllabus and track roadmaps."""
    study_years_set = set()
    target_degrees_set = set()
    roadmap_records = []

    if roadmaps and isinstance(roadmaps, list):
        for item in roadmaps:
            years = item.get("studyYears") or []
            study_years_set.update(years)
            rm = item.get("roadmap") or {}
            
            rm_code = rm.get("code") or rm.get("roadmapCode")
            rm_name = rm.get("name") if isinstance(rm.get("name"), dict) else {}
            if not rm_name and isinstance(rm.get("roadmap"), dict):
                rm_name = rm.get("roadmap", {}).get("name") if isinstance(rm.get("roadmap", {}).get("name"), dict) else {}

            rm_name_he = _extract_text(rm_name) or rm_code or "מסלול לימודים"
            rm_name_en = rm_name.get("en") if isinstance(rm_name, dict) else None

            dept_name = rm.get("departmentName") if isinstance(rm.get("departmentName"), dict) else {}
            dept_name_he = _extract_text(dept_name)
            dept_id = rm.get("departmentId")

            degree_he = _extract_text(rm.get("learningProgramDisplayName")) or _extract_text(rm.get("learningProgramName"))
            if degree_he:
                target_degrees_set.add(degree_he)

            scope_he = _extract_text(rm.get("scopeName"))
            years_str = ",".join(str(y) for y in sorted(years)) if years else None

            roadmap_records.append((
                course_id, rm_code, rm_name_he, rm_name_en,
                dept_id, dept_name_he, degree_he, scope_he, years_str
            ))

    study_years_str = ",".join(str(y) for y in sorted(study_years_set)) if study_years_set else None
    target_degrees_str = ", ".join(sorted(target_degrees_set)) if target_degrees_set else None

    # Parse syllabus
    desc = aims = outcomes = content = method = coordinator = coord_email = eval_str = None
    if syllabus and isinstance(syllabus, dict):
        desc = _extract_text(syllabus.get("courseDescription"))
        aims = _extract_text(syllabus.get("courseAims"))
        outcomes = _extract_text(syllabus.get("learningOutcomes"))
        content = _extract_text(syllabus.get("courseContent"))
        method = _extract_text(syllabus.get("teachingMethod"))
        coordinator = _extract_text(syllabus.get("courseCoordinator"))
        coord_email = syllabus.get("coordinatorEmail")

        eval_parts = []
        for pct_key, label in [
            ("writtenExamPercentage", "בחינה בכתב"),
            ("midtermExamsPercentage", "בחני אמצע"),
            ("assignmentPercentage", "מטלות/תרגילים"),
            ("presentationPercentage", "רפרט/פרזנטציה"),
            ("activeParticipationPercentage", "השתתפות פעילה"),
            ("oralExamPercentage", "בחינה בעל פה"),
        ]:
            val = syllabus.get(pct_key)
            if val and val != "0" and val != 0:
                eval_parts.append(f"{label}: {val}%")
        eval_str = ", ".join(eval_parts) if eval_parts else None

    # Parse requirements
    req_parts = []
    if reqs and isinstance(reqs, dict):
        pos = reqs.get("positiveRequirements")
        if pos:
            pos_courses = _extract_req_courses(pos)
            if pos_courses:
                req_parts.append(f"דרישות קדם: {', '.join(pos_courses)}")
        neg = reqs.get("negativeRequirements")
        if neg:
            neg_courses = _extract_req_courses(neg)
            if neg_courses:
                req_parts.append(f"קורסים מנועים/חוסמים: {', '.join(neg_courses)}")
    prereq_str = " | ".join(req_parts) if req_parts else None

    with _db_lock:
        conn = get_connection(db_path)
        with conn:
            conn.execute("""
                UPDATE courses
                SET study_years = COALESCE(?, study_years),
                    target_degrees = COALESCE(?, target_degrees),
                    description = COALESCE(?, description),
                    aims = COALESCE(?, aims),
                    learning_outcomes = COALESCE(?, learning_outcomes),
                    content = COALESCE(?, content),
                    teaching_method = COALESCE(?, teaching_method),
                    prerequisites = COALESCE(?, prerequisites),
                    evaluation_breakdown = COALESCE(?, evaluation_breakdown),
                    course_coordinator = COALESCE(?, course_coordinator),
                    coordinator_email = COALESCE(?, coordinator_email)
                WHERE id = ?;
            """, (
                study_years_str, target_degrees_str, desc, aims, outcomes,
                content, method, prereq_str, eval_str, coordinator, coord_email, course_id
            ))

            if roadmap_records:
                conn.execute("DELETE FROM course_roadmaps WHERE course_id = ?", (course_id,))
                conn.executemany("""
                    INSERT INTO course_roadmaps (
                        course_id, roadmap_code, roadmap_name_he, roadmap_name_en,
                        department_id, department_name_he, degree_name_he, scope_name_he, study_years
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, roadmap_records)
        conn.close()

def get_all_rooms(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Return all unique classrooms/halls across all campuses with building and session count."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    sql = """
        SELECT
            s.campus_name_he AS campus,
            s.building_name_he AS building,
            s.room_name_he AS room,
            COUNT(s.id) AS total_sessions
        FROM sessions s
        WHERE s.room_name_he IS NOT NULL AND s.room_name_he != ''
        GROUP BY s.campus_name_he, s.building_name_he, s.room_name_he
        ORDER BY s.campus_name_he, s.building_name_he, s.room_name_he;
    """
    cur.execute(sql)
    results = [dict(r) for r in cur.fetchall()]
    conn.close()
    return results

def get_room_weekly_schedule(
    room_name: str,
    building_name: Optional[str] = None,
    campus_name: Optional[str] = None,
    semester: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    """Return all weekly scheduled classes for a specific classroom/hall, with optional semester filter."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    conditions = ["s.room_name_he = ?"]
    params = [room_name]

    if building_name:
        conditions.append("s.building_name_he = ?")
        params.append(building_name)
    if campus_name:
        conditions.append("s.campus_name_he = ?")
        params.append(campus_name)

    if semester and semester != 'all':
        if semester in ('1', 'א', 'סמסטר א', "סמסטר א'"):
            conditions.append("(COALESCE(s.period, g.period) IN (1, 4) OR c.semester IN (1, 5))")
        elif semester in ('2', 'ב', 'סמסטר ב', "סמסטר ב'"):
            conditions.append("(COALESCE(s.period, g.period) IN (2, 4) OR c.semester IN (2, 5))")
        elif semester in ('3', 'קיץ', 'סמסטר קיץ'):
            conditions.append("(COALESCE(s.period, g.period) = 3 OR c.semester = 4)")

    where = " WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            s.id AS session_id,
            s.day_of_week,
            s.day_name_he,
            s.start_time,
            s.end_time,
            s.campus_name_he AS campus,
            s.building_name_he AS building,
            s.room_name_he AS room,
            COALESCE(s.period, g.period) AS period,
            CASE
                WHEN COALESCE(s.period, g.period) = 1 THEN 'סמסטר א'''
                WHEN COALESCE(s.period, g.period) = 2 THEN 'סמסטר ב'''
                WHEN COALESCE(s.period, g.period) = 3 THEN 'סמסטר קיץ'
                WHEN COALESCE(s.period, g.period) = 4 THEN 'שנתי'
                ELSE COALESCE(g.period_name_he, c.semester_name_he)
            END AS period_name_he,
            c.id AS course_id,
            c.code AS course_code,
            c.name_he AS course_name_he,
            c.name_en AS course_name_en,
            c.semester AS course_semester,
            c.semester_name_he AS course_semester_name_he,
            g.group_code,
            g.session_type_name_he AS session_type,
            (
                SELECT GROUP_CONCAT(COALESCE(st.name_he, st.name_en), ', ')
                FROM session_teachers st
                WHERE st.session_id = s.id
            ) AS lecturers
        FROM sessions s
        JOIN courses c ON s.course_id = c.id
        JOIN groups g ON s.group_id = g.id
        {where}
        ORDER BY s.day_of_week, s.start_time;
    """
    cur.execute(sql, params)
    results = [dict(r) for r in cur.fetchall()]
    conn.close()
    return results

def get_campus_buildings(campus: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Return all campus buildings with geocoordinates, room counts, and room lists."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campus_buildings.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if campus:
            data = [b for b in data if b.get('campus') == campus or (campus in (b.get('campus') or ''))]
        return data

    # Fallback to DB
    conn = get_connection(db_path)
    cur = conn.cursor()
    cond = "WHERE building_name_he IS NOT NULL AND building_name_he != ''"
    params = []
    if campus:
        cond += " AND campus_name_he LIKE ?"
        params.append(f"%{campus}%")
    cur.execute(f"""
        SELECT campus_name_he as campus, building_name_he as building,
               COUNT(DISTINCT room_name_he) as rooms_count, COUNT(*) as sessions_count,
               GROUP_CONCAT(DISTINCT room_name_he) as room_list
        FROM sessions
        {cond}
        GROUP BY campus_name_he, building_name_he
        ORDER BY rooms_count DESC
    """, params)
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        d['rooms'] = sorted([rm.strip() for rm in (d.pop('room_list', '') or '').split(',') if rm.strip()])
        d['lat'] = 31.7800
        d['lon'] = 35.2100
        rows.append(d)
    conn.close()
    return rows

def get_all_teachers(query: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Return all unique teachers with the number of courses they teach."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    where = ""
    params = []
    if query:
        where = "WHERE st.name_he LIKE ? OR st.name_en LIKE ?"
        kw = f"%{query.strip()}%"
        params = [kw, kw]

    sql = f"""
        SELECT
            COALESCE(st.name_he, st.name_en) AS name,
            st.name_he,
            st.name_en,
            st.title_he,
            st.email,
            COUNT(DISTINCT s.course_id) AS courses_count,
            COUNT(DISTINCT s.id) AS sessions_count
        FROM session_teachers st
        JOIN sessions s ON st.session_id = s.id
        {where}
        GROUP BY COALESCE(st.name_he, st.name_en)
        ORDER BY courses_count DESC, name ASC;
    """
    cur.execute(sql, params)
    teachers = [dict(r) for r in cur.fetchall()]
    conn.close()
    return teachers

def get_teacher_courses_and_schedule(teacher_name: str, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Return all courses and weekly class sessions for a specific lecturer."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    raw_name = teacher_name.strip()
    clean_name = re.sub(r'^(פרופ\'?|ד"ר|דר\'?|מר|גב\'?|עו"ד|עוד\'?)\s+', '', raw_name).strip()

    # 1. Courses taught by this teacher
    sql_courses = """
        SELECT DISTINCT
            c.id, c.code, c.name_he, c.name_en, c.academic_points,
            c.semester_name_he, c.faculty_name_he, c.department_name_he
        FROM courses c
        JOIN sessions s ON s.course_id = c.id
        JOIN session_teachers st ON st.session_id = s.id
        WHERE st.name_he = ? OR st.name_en = ? 
           OR st.name_he = ? OR st.name_en = ?
           OR (st.name_he || ' ' || COALESCE(st.name_en, '')) LIKE ?
           OR (st.name_he || ' ' || COALESCE(st.name_en, '')) LIKE ?
        ORDER BY c.code;
    """
    cur.execute(sql_courses, (
        raw_name, raw_name,
        clean_name, clean_name,
        f"%{clean_name}%", f"%{raw_name}%"
    ))
    courses = [dict(r) for r in cur.fetchall()]

    # 2. Weekly teaching sessions
    sql_sessions = """
        SELECT
            s.id AS session_id,
            s.day_of_week,
            s.day_name_he,
            s.start_time,
            s.end_time,
            s.campus_name_he AS campus,
            s.building_name_he AS building,
            s.room_name_he AS room,
            c.id AS course_id,
            c.code AS course_code,
            c.name_he AS course_name,
            g.group_code,
            g.session_type_name_he AS session_type
        FROM sessions s
        JOIN session_teachers st ON st.session_id = s.id
        JOIN courses c ON s.course_id = c.id
        JOIN groups g ON s.group_id = g.id
        WHERE st.name_he = ? OR st.name_en = ? 
           OR st.name_he = ? OR st.name_en = ?
           OR (st.name_he || ' ' || COALESCE(st.name_en, '')) LIKE ?
           OR (st.name_he || ' ' || COALESCE(st.name_en, '')) LIKE ?
        ORDER BY s.day_of_week, s.start_time;
    """
    cur.execute(sql_sessions, (
        raw_name, raw_name,
        clean_name, clean_name,
        f"%{clean_name}%", f"%{raw_name}%"
    ))
    sessions = [dict(r) for r in cur.fetchall()]

    conn.close()
    return {"teacher_name": raw_name, "clean_name": clean_name, "courses": courses, "sessions": sessions}

def get_departments(faculty_code: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Return all departments, optionally filtered by faculty_code."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    if faculty_code:
        cur.execute("SELECT id, faculty_code, code, name_he, name_en FROM departments WHERE faculty_code = ? AND name_he IS NOT NULL ORDER BY name_he", (faculty_code,))
    else:
        cur.execute("SELECT id, faculty_code, code, name_he, name_en FROM departments WHERE name_he IS NOT NULL ORDER BY name_he")
    results = [dict(r) for r in cur.fetchall()]
    conn.close()
    return results

def get_roadmaps_list(
    q: Optional[str] = None,
    degree: Optional[str] = None,
    scope: Optional[str] = None,
    faculty: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 150,
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    """Search and filter academic roadmaps / study programs."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    conditions = ["cr.roadmap_code IS NOT NULL"]
    params: List[Any] = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        conditions.append("(cr.roadmap_name_he LIKE ? OR cr.roadmap_code LIKE ? OR cr.department_name_he LIKE ? OR cr.roadmap_name_en LIKE ?)")
        params.extend([term, term, term, term])

    if degree and degree.strip() and degree.strip() != "all":
        conditions.append("cr.degree_name_he LIKE ?")
        params.append(f"%{degree.strip()}%")

    if scope and scope.strip() and scope.strip() != "all":
        conditions.append("cr.scope_name_he LIKE ?")
        params.append(f"%{scope.strip()}%")

    if department and department.strip() and department.strip() != "all":
        conditions.append("cr.department_name_he LIKE ?")
        params.append(f"%{department.strip()}%")

    where_clause = " WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT 
            cr.roadmap_code,
            cr.roadmap_name_he,
            cr.roadmap_name_en,
            cr.department_id,
            cr.department_name_he,
            cr.department_name_en,
            cr.degree_name_he,
            cr.scope_name_he,
            cr.study_years,
            COUNT(DISTINCT cr.course_id) AS course_count
        FROM course_roadmaps cr
        {where_clause}
        GROUP BY cr.roadmap_code
        ORDER BY cr.roadmap_name_he ASC
        LIMIT ?
    """
    params.append(limit)
    cur.execute(sql, params)
    roadmaps = [dict(r) for r in cur.fetchall()]
    conn.close()
    return roadmaps

def get_roadmap_curriculum(roadmap_code: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve cached curriculum tree for a specific roadmap code."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT roadmap_code, title_he, title_en, data_json, updated_at FROM roadmap_curricula WHERE roadmap_code = ?", (roadmap_code,))
    row = cur.fetchone()
    conn.close()
    if row and row["data_json"]:
        try:
            return json.loads(row["data_json"])
        except Exception:
            return None
    return None

def save_roadmap_curriculum(roadmap_code: str, title_he: str, title_en: Optional[str], data: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> None:
    """Cache curriculum tree for a roadmap code."""
    data_json = json.dumps(data, ensure_ascii=False)
    with _db_lock:
        conn = get_connection(db_path)
        with conn:
            conn.execute("""
                INSERT INTO roadmap_curricula (roadmap_code, title_he, title_en, data_json, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(roadmap_code) DO UPDATE SET
                    title_he = excluded.title_he,
                    title_en = excluded.title_en,
                    data_json = excluded.data_json,
                    updated_at = CURRENT_TIMESTAMP;
            """, (roadmap_code, title_he, title_en or "", data_json))
        conn.close()

def get_course_exams(course_id: int, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Get all scheduled exams for a course."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM exams 
        WHERE course_id = ? 
        ORDER BY 
            CASE WHEN start_time IS NOT NULL THEN 0 ELSE 1 END,
            moed ASC, 
            start_time ASC
    """, (course_id,))
    exams = [dict(r) for r in cur.fetchall()]
    conn.close()
    return exams

def get_exams_list(
    q: Optional[str] = None,
    faculty: Optional[str] = None,
    semester: Optional[str] = None,
    moed: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    has_date_only: bool = False,
    limit: int = 250,
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    """Query exams across all courses with joined course information."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    conditions = []
    params: List[Any] = []

    if has_date_only:
        conditions.append("e.start_time IS NOT NULL")

    if q and q.strip():
        term = f"%{q.strip()}%"
        conditions.append("(c.name_he LIKE ? OR c.code LIKE ? OR c.name_en LIKE ? OR e.assignment_name_he LIKE ? OR e.rooms_summary LIKE ?)")
        params.extend([term, term, term, term, term])

    if faculty and faculty.strip() and faculty.strip() != "all":
        conditions.append("(c.faculty_code = ? OR c.faculty_name_he LIKE ?)")
        params.extend([faculty.strip(), f"%{faculty.strip()}%"])

    if semester and semester.strip() and semester.strip() != "all":
        conditions.append("(e.period = ? OR e.period_name_he LIKE ?)")
        params.extend([semester.strip(), f"%{semester.strip()}%"])

    if moed is not None and str(moed).strip() and str(moed).strip() != "all":
        conditions.append("e.moed = ?")
        params.append(int(moed))

    if from_date and from_date.strip():
        conditions.append("COALESCE(e.exam_date, SUBSTR(e.start_time, 1, 10)) >= ?")
        params.append(from_date.strip())

    if to_date and to_date.strip():
        conditions.append("COALESCE(e.exam_date, SUBSTR(e.start_time, 1, 10)) <= ?")
        params.append(to_date.strip())

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT 
            e.id AS exam_id,
            e.course_id,
            c.code AS course_code,
            c.name_he AS course_name_he,
            c.name_en AS course_name_en,
            c.faculty_name_he,
            c.department_name_he,
            c.academic_points,
            e.assignment_id,
            e.moed,
            e.period,
            e.period_name_he,
            e.start_time,
            e.end_time,
            e.exam_date,
            e.rooms_summary,
            e.assignment_name_he,
            e.weight,
            e.campus_name_he,
            e.building_name_he
        FROM exams e
        JOIN courses c ON e.course_id = c.id
        {where_clause}
        ORDER BY 
            CASE WHEN e.start_time IS NOT NULL THEN 0 ELSE 1 END,
            e.start_time ASC, 
            e.moed ASC,
            c.code ASC
        LIMIT ?
    """
    params.append(limit)
    cur.execute(sql, params)
    exams = [dict(r) for r in cur.fetchall()]
    conn.close()
    return exams



