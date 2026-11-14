/**
 * db_engine.js - Client-Side SQLite WASM Database Engine for HUJI Course Catalog
 * 
 * Runs 100% in the user's browser via sql.js and WebAssembly.
 * Intercepts /api/* fetch requests transparently, providing zero-latency responses
 * on GitHub Pages and static web servers without requiring any backend Python server.
 * 
 * Features:
 * - Streaming download of shnaton.db.gz with real-time percentage progress.
 * - In-browser streaming decompression via DecompressionStream('gzip').
 * - High-speed IndexedDB persistent caching (first load takes ~2s, subsequent visits take ~50ms).
 * - Full relational queries matching database.py 1:1.
 */

(function () {
    'use strict';

    const DB_CACHE_NAME = 'HujiShnatonCache';
    const DB_CACHE_STORE = 'dbStore';
    const DB_CACHE_KEY = 'shnaton_sqlite_db';
    const DB_VERSION_KEY = 'shnaton_db_version';

    let dbInstance = null;
    let isDbReady = false;
    let readyCallbacks = [];

    // Helper: open IndexedDB
    function openIDB() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_CACHE_NAME, 1);
            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(DB_CACHE_STORE)) {
                    db.createObjectStore(DB_CACHE_STORE);
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async function getFromIDB(key) {
        try {
            const idb = await openIDB();
            return new Promise((resolve) => {
                const tx = idb.transaction(DB_CACHE_STORE, 'readonly');
                const req = tx.objectStore(DB_CACHE_STORE).get(key);
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => resolve(null);
            });
        } catch (e) {
            console.warn('[IDB] Get failed:', e);
            return null;
        }
    }

    async function saveToIDB(key, val) {
        try {
            const idb = await openIDB();
            return new Promise((resolve) => {
                const tx = idb.transaction(DB_CACHE_STORE, 'readwrite');
                tx.objectStore(DB_CACHE_STORE).put(val, key);
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            });
        } catch (e) {
            console.warn('[IDB] Save failed:', e);
            return false;
        }
    }

    async function clearIDB() {
        try {
            const idb = await openIDB();
            const tx = idb.transaction(DB_CACHE_STORE, 'readwrite');
            tx.objectStore(DB_CACHE_STORE).clear();
        } catch (e) {
            console.warn('[IDB] Clear failed:', e);
        }
    }

    // Modern UI overlay for download progress
    function showProgressOverlay(text, percent = null) {
        let el = document.getElementById('huji-db-loader-overlay');
        if (!el) {
            el = document.createElement('div');
            el.id = 'huji-db-loader-overlay';
            el.innerHTML = `
                <div style="background: rgba(15, 23, 42, 0.92); backdrop-filter: blur(8px); position: fixed; inset: 0; z-index: 999999; display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: 'Heebo', sans-serif; direction: rtl; color: white;">
                    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 20px; padding: 32px 40px; max-width: 440px; width: 90%; text-align: center; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
                        <div style="font-size: 40px; margin-bottom: 12px;">📚</div>
                        <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 8px; color: #f8fafc;">שנתון האוניברסיטה העברית</h3>
                        <p id="huji-db-loader-text" style="font-size: 14px; color: #94a3b8; margin-bottom: 20px; line-height: 1.5;">טוען את מאגר המידע...</p>
                        <div style="background: #0f172a; border-radius: 9999px; height: 10px; width: 100%; overflow: hidden; margin-bottom: 10px;">
                            <div id="huji-db-loader-bar" style="background: linear-gradient(90deg, #C9963B, #0284c7); height: 100%; width: 0%; transition: width 0.2s ease; border-radius: 9999px;"></div>
                        </div>
                        <div id="huji-db-loader-sub" style="font-size: 12px; color: #64748b;">שמירה מקומית מאפשרת גישה מיידית וללא חיבור לרשת</div>
                    </div>
                </div>
            `;
            document.body.appendChild(el);
        }
        const textEl = document.getElementById('huji-db-loader-text');
        const barEl = document.getElementById('huji-db-loader-bar');
        if (textEl && text) textEl.textContent = text;
        if (barEl && percent !== null) barEl.style.width = Math.min(100, Math.max(0, percent)) + '%';
    }

    function hideProgressOverlay() {
        const el = document.getElementById('huji-db-loader-overlay');
        if (el) {
            el.style.opacity = '0';
            el.style.transition = 'opacity 0.3s ease';
            setTimeout(() => el.remove(), 300);
        }
    }

    // Initialize Database
    async function initDatabase() {
        if (dbInstance) return dbInstance;

        try {
            // 1. Fetch remote version info
            let remoteVersion = 1;
            try {
                const vRes = await window.__originalFetch('version.json?t=' + Date.now());
                if (vRes.ok) {
                    const vData = await vRes.json();
                    remoteVersion = vData.version || remoteVersion;
                }
            } catch (e) {
                console.warn('[DB Engine] Could not fetch version.json, proceeding with cache check:', e);
            }

            // 2. Check IndexedDB
            const cachedVersion = await getFromIDB(DB_VERSION_KEY);
            const cachedBytes = await getFromIDB(DB_CACHE_KEY);

            let dbBytes = null;
            if (cachedBytes && cachedVersion === remoteVersion) {
                console.log('[DB Engine] Loading database from local IndexedDB cache...');
                dbBytes = cachedBytes;
            } else {
                console.log('[DB Engine] Downloading database (new or updated)...');
                showProgressOverlay('מוריד מאגר נתונים (כ-18MB)...', 5);

                const response = await window.__originalFetch('shnaton.db.gz?v=' + remoteVersion);
                if (!response.ok) {
                    throw new Error('Failed to fetch shnaton.db.gz (HTTP ' + response.status + ')');
                }

                const contentLength = parseInt(response.headers.get('Content-Length') || '19651363', 10);
                let loaded = 0;

                const reader = response.body.getReader();
                const stream = new ReadableStream({
                    async start(controller) {
                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) break;
                            loaded += value.byteLength;
                            const pct = Math.min(95, Math.round((loaded / contentLength) * 100));
                            showProgressOverlay(`מוריד מאגר נתונים (${(loaded / (1024 * 1024)).toFixed(1)}MB / ${(contentLength / (1024 * 1024)).toFixed(1)}MB)...`, pct);
                            controller.enqueue(value);
                        }
                        controller.close();
                    }
                });

                showProgressOverlay('פורס ומכין את מסד הנתונים...', 96);
                const decompressedStream = stream.pipeThrough(new DecompressionStream('gzip'));
                const decompressedRes = new Response(decompressedStream);
                dbBytes = new Uint8Array(await decompressedRes.arrayBuffer());

                // Save to IndexedDB
                showProgressOverlay('שומר בזיכרון המכשיר לטעינה מיידית...', 99);
                await saveToIDB(DB_CACHE_KEY, dbBytes);
                await saveToIDB(DB_VERSION_KEY, remoteVersion);
            }

            // 3. Initialize sql.js WebAssembly
            showProgressOverlay('מאתחל מנוע שאילתות מהיר...', 100);
            if (typeof initSqlJs !== 'function') {
                throw new Error('sql.js is not loaded! Make sure sql-wasm.js is included.');
            }

            const SQL = await initSqlJs({
                locateFile: file => file
            });

            dbInstance = new SQL.Database(dbBytes);
            isDbReady = true;
            window.HujiDb = dbInstance;
            console.log('[DB Engine] SQLite WASM Database is ready!');

            hideProgressOverlay();

            // Run pending callbacks
            for (const cb of readyCallbacks) cb();
            readyCallbacks = [];

            return dbInstance;
        } catch (err) {
            console.error('[DB Engine] Initialization failed:', err);
            showProgressOverlay('שגיאה בטעינת מסד הנתונים: ' + err.message);
            throw err;
        }
    }

    // Run SQL query helper
    function queryRows(sql, params = {}) {
        if (!dbInstance) throw new Error('Database not initialized');
        const stmt = dbInstance.prepare(sql);
        stmt.bind(params);
        const rows = [];
        while (stmt.step()) {
            rows.push(stmt.getAsObject());
        }
        stmt.free();
        return rows;
    }

    function querySingle(sql, params = {}) {
        const rows = queryRows(sql, params);
        return rows.length > 0 ? rows[0] : null;
    }

    // =========================================================================
    // API IMPLEMENTATIONS
    // =========================================================================

    function handleFaculties() {
        return queryRows("SELECT code, name_he, name_en FROM faculties WHERE name_he IS NOT NULL ORDER BY name_he");
    }

    function handleDepartments(params) {
        const fac = params.get('faculty');
        if (fac) {
            return queryRows("SELECT id, name_he, name_en, faculty_code FROM departments WHERE faculty_code = :fac AND name_he IS NOT NULL ORDER BY name_he", { ':fac': fac });
        }
        return queryRows("SELECT id, name_he, name_en, faculty_code FROM departments WHERE name_he IS NOT NULL ORDER BY name_he");
    }

    function handleSearch(params) {
        const q = (params.get('q') || '').trim();
        const faculty = (params.get('faculty') || '').trim();
        const dept = (params.get('dept') || '').trim();
        const year = (params.get('year') || '').trim();
        const sem = (params.get('semester') || '').trim();

        const conditions = ["c.is_learning = 1"];
        const bindParams = {};

        if (q) {
            conditions.push(`(
                c.code LIKE :kw OR
                c.name_he LIKE :kw OR
                c.name_en LIKE :kw OR
                c.description LIKE :kw OR
                EXISTS (
                    SELECT 1 FROM session_teachers st
                    JOIN sessions s ON st.session_id = s.id
                    WHERE s.course_id = c.id AND (st.name_he LIKE :kw OR st.name_en LIKE :kw)
                )
            )`);
            bindParams[':kw'] = `%${q}%`;
        }

        if (faculty && faculty !== 'all') {
            conditions.push("c.faculty_code = :fac");
            bindParams[':fac'] = faculty;
        }

        if (dept && dept !== 'all') {
            conditions.push(`(
                c.department_id = :dept OR
                EXISTS (SELECT 1 FROM course_roadmaps cr WHERE cr.course_id = c.id AND cr.department_id = :dept)
            )`);
            bindParams[':dept'] = dept;
        }

        if (year && year !== 'all') {
            conditions.push(`(
                c.study_years LIKE :yr OR
                EXISTS (SELECT 1 FROM course_roadmaps cr WHERE cr.course_id = c.id AND cr.study_years LIKE :yr)
            )`);
            bindParams[':yr'] = `%${year}%`;
        }

        if (sem && sem !== 'all') {
            conditions.push("(c.semester = :sem OR c.semester_name_he LIKE :sem_str)");
            bindParams[':sem'] = parseInt(sem, 10) || 0;
            bindParams[':sem_str'] = `%${sem}%`;
        }

        const where = " WHERE " + conditions.join(" AND ");

        const countRow = querySingle(`SELECT COUNT(*) as count FROM courses c ${where}`, bindParams);
        const total = countRow ? countRow.count : 0;

        const sql = `
            SELECT
                c.id, c.code, c.name_he, c.name_en, c.academic_points,
                c.semester_name_he, c.faculty_name_he, c.department_name_he,
                c.study_years,
                (
                    SELECT GROUP_CONCAT(DISTINCT COALESCE(st.name_he, st.name_en))
                    FROM sessions s
                    JOIN session_teachers st ON st.session_id = s.id
                    WHERE s.course_id = c.id
                ) AS teacher_names,
                (
                    SELECT COUNT(*) FROM exams e WHERE e.course_id = c.id
                ) AS exams_count,
                (
                    SELECT GROUP_CONCAT(
                        (CASE WHEN e.moed = 1 THEN 'א׳' WHEN e.moed = 2 THEN 'ב׳' ELSE CAST(e.moed AS TEXT) END) || 
                        ': ' || SUBSTR(COALESCE(e.exam_date, e.start_time), 9, 2) || '/' || SUBSTR(COALESCE(e.exam_date, e.start_time), 6, 2),
                        ' | '
                    )
                    FROM exams e
                    WHERE e.course_id = c.id AND (e.exam_date IS NOT NULL OR e.start_time IS NOT NULL)
                ) AS exams_badge
            FROM courses c
            ${where}
            ORDER BY c.code ASC
            LIMIT 150
        `;

        const rawCourses = queryRows(sql, bindParams);
        const courses = rawCourses.map(r => {
            const tStr = r.teacher_names || "";
            delete r.teacher_names;
            r.teachers = tStr.split(",").map(t => t.trim()).filter(Boolean).slice(0, 3);
            return r;
        });

        return { total, courses };
    }

    function handleCourseDetail(courseIdOrCode) {
        const course = querySingle("SELECT * FROM courses WHERE id = :id OR code = :code", {
            ':id': parseInt(courseIdOrCode, 10) || -1,
            ':code': String(courseIdOrCode)
        });

        if (!course) return null;
        const cid = course.id;

        // Groups & sessions
        const groups = queryRows("SELECT * FROM groups WHERE course_id = :cid ORDER BY group_code", { ':cid': cid });
        for (const g of groups) {
            const sessions = queryRows(`
                SELECT s.* FROM sessions s
                WHERE s.group_id = :gid
                ORDER BY s.day_of_week, s.start_time
            `, { ':gid': g.id });

            for (const s of sessions) {
                s.teachers = queryRows(`
                    SELECT name_he, name_en, email, title_he FROM session_teachers
                    WHERE session_id = :sid
                `, { ':sid': s.id });
            }
            g.sessions = sessions;
        }
        course.groups = groups;

        // Roadmaps
        course.roadmaps = queryRows(`
            SELECT roadmap_code, roadmap_name_he, roadmap_name_en,
                   department_name_he, degree_name_he, scope_name_he, study_years
            FROM course_roadmaps
            WHERE course_id = :cid
            ORDER BY department_name_he, degree_name_he, roadmap_name_he
        `, { ':cid': cid });

        // Exams
        course.exams = queryRows(`
            SELECT * FROM exams 
            WHERE course_id = :cid 
            ORDER BY 
                CASE WHEN start_time IS NOT NULL THEN 0 ELSE 1 END,
                moed ASC, 
                start_time ASC
        `, { ':cid': cid });

        return course;
    }

    function handleExams(params) {
        const q = (params.get('q') || '').trim();
        const faculty = (params.get('faculty') || '').trim();
        const semester = (params.get('semester') || '').trim();
        const moedStr = (params.get('moed') || '').trim();
        const fromDate = (params.get('from') || '').trim();
        const toDate = (params.get('to') || '').trim();
        const hasDate = params.get('has_date') === '1';
        const limit = parseInt(params.get('limit') || '250', 10);

        const conditions = [];
        const bindParams = {};

        if (hasDate) {
            conditions.push("e.start_time IS NOT NULL");
        }

        if (q) {
            conditions.push("(c.name_he LIKE :kw OR c.code LIKE :kw OR c.name_en LIKE :kw OR e.assignment_name_he LIKE :kw OR e.rooms_summary LIKE :kw)");
            bindParams[':kw'] = `%${q}%`;
        }

        if (faculty && faculty !== 'all') {
            conditions.push("(c.faculty_code = :fac OR c.faculty_name_he LIKE :fac_kw)");
            bindParams[':fac'] = faculty;
            bindParams[':fac_kw'] = `%${faculty}%`;
        }

        if (semester && semester !== 'all') {
            conditions.push("(e.period = :sem OR e.period_name_he LIKE :sem_kw)");
            bindParams[':sem'] = semester;
            bindParams[':sem_kw'] = `%${semester}%`;
        }

        if (moedStr && moedStr !== 'all') {
            conditions.push("e.moed = :moed");
            bindParams[':moed'] = parseInt(moedStr, 10);
        }

        if (fromDate) {
            conditions.push("COALESCE(e.exam_date, SUBSTR(e.start_time, 1, 10)) >= :from_date");
            bindParams[':from_date'] = fromDate;
        }

        if (toDate) {
            conditions.push("COALESCE(e.exam_date, SUBSTR(e.start_time, 1, 10)) <= :to_date");
            bindParams[':to_date'] = toDate;
        }

        const where = conditions.length > 0 ? " WHERE " + conditions.join(" AND ") : "";

        const sql = `
            SELECT 
                e.*,
                c.code AS course_code,
                c.name_he AS course_name_he,
                c.name_en AS course_name_en,
                c.faculty_name_he,
                c.academic_points,
                c.semester_name_he AS course_semester
            FROM exams e
            JOIN courses c ON e.course_id = c.id
            ${where}
            ORDER BY 
                CASE WHEN e.start_time IS NOT NULL THEN 0 ELSE 1 END,
                e.start_time ASC,
                c.code ASC
            LIMIT ${limit}
        `;

        return queryRows(sql, bindParams);
    }

    function handleRooms() {
        return queryRows(`
            SELECT
                s.campus_name_he AS campus,
                s.building_name_he AS building,
                s.room_name_he AS room,
                COUNT(s.id) AS total_sessions
            FROM sessions s
            WHERE s.room_name_he IS NOT NULL AND s.room_name_he != ''
            GROUP BY s.campus_name_he, s.building_name_he, s.room_name_he
            ORDER BY s.campus_name_he, s.building_name_he, s.room_name_he
        `);
    }

    function handleRoomSchedule(params) {
        const room = (params.get('room') || '').trim();
        const building = (params.get('building') || '').trim();
        const campus = (params.get('campus') || '').trim();
        const semester = (params.get('semester') || '').trim();

        const conditions = ["s.room_name_he = :room"];
        const bindParams = { ':room': room };

        if (building) {
            conditions.push("s.building_name_he = :building");
            bindParams[':building'] = building;
        }
        if (campus) {
            conditions.push("s.campus_name_he = :campus");
            bindParams[':campus'] = campus;
        }

        if (semester && semester !== 'all') {
            if (semester === '1' || semester.includes('א')) {
                conditions.push("(COALESCE(s.period, g.period) IN (1, 4) OR c.semester IN (1, 5))");
            } else if (semester === '2' || semester.includes('ב')) {
                conditions.push("(COALESCE(s.period, g.period) IN (2, 4) OR c.semester IN (2, 5))");
            } else if (semester === '3' || semester.includes('קיץ')) {
                conditions.push("(COALESCE(s.period, g.period) = 3 OR c.semester = 4)");
            }
        }

        const where = " WHERE " + conditions.join(" AND ");

        const sql = `
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
                c.id AS course_id,
                c.code AS course_code,
                c.name_he AS course_name,
                c.academic_points,
                g.group_code,
                g.session_type_name_he AS session_type,
                (
                    SELECT GROUP_CONCAT(COALESCE(st.name_he, st.name_en), ', ')
                    FROM session_teachers st
                    WHERE st.session_id = s.id
                ) AS teacher_name
            FROM sessions s
            JOIN groups g ON s.group_id = g.id
            JOIN courses c ON s.course_id = c.id
            ${where}
            ORDER BY s.day_of_week, s.start_time
        `;

        return queryRows(sql, bindParams);
    }

    function handleTeachers(params) {
        const q = (params.get('q') || '').trim();
        const where = q ? "WHERE st.name_he LIKE :kw OR st.name_en LIKE :kw" : "";
        const bindParams = q ? { ':kw': `%${q}%` } : {};

        const sql = `
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
            ${where}
            GROUP BY COALESCE(st.name_he, st.name_en)
            ORDER BY courses_count DESC, name ASC
            LIMIT 200
        `;

        return queryRows(sql, bindParams);
    }

    function handleTeacherDetail(params) {
        const rawName = (params.get('name') || '').trim();
        const cleanName = rawName.replace(/^(פרופ'?|ד"ר|דר'?|מר|גב'?|עו"ד|עוד'?)\s+/, '').trim();

        // 1. Courses
        const courses = queryRows(`
            SELECT DISTINCT
                c.id, c.code, c.name_he, c.name_en, c.academic_points,
                c.semester_name_he, c.faculty_name_he, c.department_name_he
            FROM courses c
            JOIN sessions s ON s.course_id = c.id
            JOIN session_teachers st ON st.session_id = s.id
            WHERE st.name_he = :raw OR st.name_en = :raw 
               OR st.name_he = :clean OR st.name_en = :clean
               OR (st.name_he || ' ' || COALESCE(st.name_en, '')) LIKE :cleanKw
               OR (st.name_he || ' ' || COALESCE(st.name_en, '')) LIKE :rawKw
            ORDER BY c.code
        `, {
            ':raw': rawName,
            ':clean': cleanName,
            ':cleanKw': `%${cleanName}%`,
            ':rawKw': `%${rawName}%`
        });

        // 2. Sessions
        const sessions = queryRows(`
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
            WHERE st.name_he = :raw OR st.name_en = :raw 
               OR st.name_he = :clean OR st.name_en = :clean
               OR (st.name_he || ' ' || COALESCE(st.name_en, '')) LIKE :cleanKw
               OR (st.name_he || ' ' || COALESCE(st.name_en, '')) LIKE :rawKw
            ORDER BY s.day_of_week, s.start_time
        `, {
            ':raw': rawName,
            ':clean': cleanName,
            ':cleanKw': `%${cleanName}%`,
            ':rawKw': `%${rawName}%`
        });

        const teacherMeta = querySingle(`
            SELECT email, title_he FROM session_teachers 
            WHERE (name_he = :raw OR name_he = :clean) AND email IS NOT NULL AND email != ''
            LIMIT 1
        `, { ':raw': rawName, ':clean': cleanName });

        return {
            name: rawName,
            email: teacherMeta ? teacherMeta.email : "",
            title: teacherMeta ? teacherMeta.title_he : "",
            courses: courses,
            schedule: sessions
        };
    }

    function handleRoadmaps(params) {
        const q = (params.get('q') || '').trim();
        const degree = (params.get('degree') || '').trim();
        const scope = (params.get('scope') || '').trim();
        const dept = (params.get('department') || '').trim();

        const conditions = ["cr.roadmap_code IS NOT NULL"];
        const bindParams = {};

        if (q) {
            conditions.push("(cr.roadmap_name_he LIKE :kw OR cr.roadmap_code LIKE :kw OR cr.department_name_he LIKE :kw OR cr.roadmap_name_en LIKE :kw)");
            bindParams[':kw'] = `%${q}%`;
        }

        if (degree && degree !== 'all') {
            conditions.push("cr.degree_name_he LIKE :deg");
            bindParams[':deg'] = `%${degree}%`;
        }

        if (scope && scope !== 'all') {
            conditions.push("cr.scope_name_he LIKE :sc");
            bindParams[':sc'] = `%${scope}%`;
        }

        if (dept && dept !== 'all') {
            conditions.push("cr.department_name_he LIKE :dept");
            bindParams[':dept'] = `%${dept}%`;
        }

        const where = " WHERE " + conditions.join(" AND ");

        const sql = `
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
            ${where}
            GROUP BY cr.roadmap_code
            ORDER BY cr.roadmap_name_he ASC
            LIMIT 150
        `;

        return queryRows(sql, bindParams);
    }

    function handleRoadmapCurriculum(params) {
        const code = (params.get('code') || '').trim();
        if (!code) return null;

        // 1. Check roadmap_curricula table
        const cached = querySingle("SELECT curriculum_json FROM roadmap_curricula WHERE roadmap_code = :code", { ':code': code });
        if (cached && cached.curriculum_json) {
            try {
                const parsed = JSON.parse(cached.curriculum_json);
                if (parsed.years && parsed.years.length > 0) {
                    return parsed;
                }
            } catch (e) {
                console.warn('[Curriculum] Cached JSON parse error:', e);
            }
        }

        // 2. Dynamic Fallback from course_roadmaps + courses
        const rows = queryRows(`
            SELECT c.id, c.code, c.name_he, c.name_en, c.academic_points,
                   c.semester_name_he, cr.study_years, cr.roadmap_name_he
            FROM course_roadmaps cr
            JOIN courses c ON c.id = cr.course_id
            WHERE cr.roadmap_code = :code
            ORDER BY cr.study_years, c.code
        `, { ':code': code });

        const yearsMap = {};
        for (const r of rows) {
            const yStr = String(r.study_years || '1');
            const firstY = parseInt(yStr.split(',')[0], 10) || 1;
            if (!yearsMap[firstY]) yearsMap[firstY] = [];

            const semStr = r.semester_name_he || '';
            let semType = 'a';
            let semBadge = 'סמסטר א׳';
            if (semStr.includes('ב')) { semType = 'b'; semBadge = 'סמסטר ב׳'; }
            else if (semStr.includes('שנתי')) { semType = 'annual'; semBadge = 'שנתי'; }
            else if (semStr.includes('קיץ')) { semType = 'summer'; semBadge = 'קיץ'; }

            r.semester_type = semType;
            r.semester_badge = semBadge;
            yearsMap[firstY].push(r);
        }

        const hebrewYears = ['א׳', 'ב׳', 'ג׳', 'ד׳', 'ה׳', 'ו׳'];
        const yearsList = Object.keys(yearsMap).sort((a, b) => parseInt(a) - parseInt(b)).map(yKey => {
            const yNum = parseInt(yKey, 10);
            const coursesInYear = yearsMap[yNum];
            const totalPts = coursesInYear.reduce((acc, c) => acc + (parseFloat(c.academic_points) || 0), 0);
            const label = `שנה ${hebrewYears[Math.min(yNum - 1, 5)] || yNum}`;

            return {
                year_number: yNum,
                year_label: label,
                mandatory_points: totalPts,
                required_elective_min_points: 0,
                elective_min_points: 0,
                year_required_min_points: totalPts,
                categories: [
                    {
                        subchapter: "קורסי התוכנית",
                        category_type: "mandatory",
                        category_label: "חובה",
                        is_mandatory: true,
                        min_points: totalPts,
                        max_points: totalPts,
                        obligation_text: `חובה ללמוד את כל הקורסים (${totalPts} נ"ז סה"כ)`,
                        note: "",
                        courses: coursesInYear
                    }
                ]
            };
        });

        return {
            code: code,
            title_he: rows.length > 0 ? rows[0].roadmap_name_he : code,
            title_en: "",
            years: yearsList,
            total_courses: rows.length,
            is_fallback: true
        };
    }

    function handleAutocomplete(params) {
        const q = (params.get('q') || '').trim();
        if (!q || q.length < 2) return [];

        const sql = `
            SELECT code, name_he, academic_points, faculty_name_he
            FROM courses
            WHERE is_learning = 1 AND (code LIKE :kw OR name_he LIKE :kw)
            ORDER BY code ASC
            LIMIT 10
        `;
        return queryRows(sql, { ':kw': `%${q}%` });
    }

    function handleStats() {
        const cRow = querySingle("SELECT COUNT(*) as count FROM courses");
        const gRow = querySingle("SELECT COUNT(*) as count FROM groups");
        const sRow = querySingle("SELECT COUNT(*) as count FROM sessions");
        const tRow = querySingle("SELECT COUNT(DISTINCT name_he) as count FROM session_teachers");
        const eRow = querySingle("SELECT COUNT(*) as count FROM exams");

        return {
            courses: cRow ? cRow.count : 0,
            groups: gRow ? gRow.count : 0,
            sessions: sRow ? sRow.count : 0,
            teachers: tRow ? tRow.count : 0,
            exams: eRow ? eRow.count : 0
        };
    }

    // =========================================================================
    // TRANSPARENT FETCH INTERCEPTOR
    // =========================================================================

    if (!window.__originalFetch) {
        window.__originalFetch = window.fetch;
    }

    window.fetch = async function (resource, options) {
        const urlStr = typeof resource === 'string' ? resource : (resource ? resource.url : '');

        // Intercept only /api/* calls
        if (urlStr.startsWith('/api/') || urlStr.startsWith('api/')) {
            // Wait for DB ready
            if (!isDbReady) {
                await new Promise(resolve => readyCallbacks.push(resolve));
            }

            const urlObj = new URL(urlStr, window.location.origin);
            const path = urlObj.pathname.startsWith('/') ? urlObj.pathname : '/' + urlObj.pathname;
            const params = urlObj.searchParams;

            let result = null;

            try {
                if (path === '/api/faculties') {
                    result = handleFaculties();
                } else if (path === '/api/departments') {
                    result = handleDepartments(params);
                } else if (path === '/api/search') {
                    result = handleSearch(params);
                } else if (path.startsWith('/api/course/')) {
                    const cid = path.split('/').pop();
                    result = handleCourseDetail(cid);
                    if (!result) {
                        return new Response(JSON.stringify({ error: "Course Not Found" }), {
                            status: 404,
                            headers: { 'Content-Type': 'application/json; charset=utf-8' }
                        });
                    }
                } else if (path === '/api/exams') {
                    result = handleExams(params);
                } else if (path === '/api/rooms') {
                    result = handleRooms();
                } else if (path === '/api/room/schedule') {
                    result = handleRoomSchedule(params);
                } else if (path === '/api/map/buildings') {
                    // Try fetching static json
                    try {
                        const mRes = await window.__originalFetch('campus_buildings.json');
                        if (mRes.ok) return mRes;
                    } catch (e) { }
                    result = [];
                } else if (path === '/api/autocomplete') {
                    result = handleAutocomplete(params);
                } else if (path === '/api/stats') {
                    result = handleStats();
                } else if (path === '/api/teachers') {
                    result = handleTeachers(params);
                } else if (path === '/api/teacher/detail') {
                    result = handleTeacherDetail(params);
                } else if (path === '/api/roadmaps') {
                    result = handleRoadmaps(params);
                } else if (path === '/api/roadmap/curriculum') {
                    result = handleRoadmapCurriculum(params);
                } else {
                    return new Response(JSON.stringify({ error: "Endpoint not found" }), {
                        status: 404,
                        headers: { 'Content-Type': 'application/json; charset=utf-8' }
                    });
                }

                return new Response(JSON.stringify(result), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json; charset=utf-8' }
                });
            } catch (err) {
                console.error('[DB Engine] API Error on ' + path + ':', err);
                return new Response(JSON.stringify({ error: err.message }), {
                    status: 500,
                    headers: { 'Content-Type': 'application/json; charset=utf-8' }
                });
            }
        }

        // Non-api requests pass through
        return window.__originalFetch(resource, options);
    };

    // Expose force reload function
    window.forceRefreshDatabase = async function () {
        if (!confirm('האם ברצונך למחוק את מאגר הנתונים המקומי ולהוריד מחדש את הגרסה העדכנית ביותר מהשרת?')) {
            return;
        }
        await clearIDB();
        window.location.reload();
    };

    // Auto-boot DB engine when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDatabase);
    } else {
        initDatabase();
    }

})();
