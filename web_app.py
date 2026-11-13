"""
Web GUI for Hebrew University Course Catalog (שנתון האוניברסיטה העברית) - Version 2.0.
A rich, full-featured web application built with the pure Python standard library.
Includes:
1. Advanced Course Catalog & Syllabus viewer (study years, prerequisites, aims, roadmaps, grade breakdown).
2. Dedicated Classroom & Lecture Hall Occupancy section (search any room, weekly 08:00-20:00 occupancy grid & free slots).
3. Lecturer Hub (click any lecturer across the system to view all their courses and teaching timetable).
4. Personal Timetable (interactive weekly schedule builder).
Full RTL layout, modern typography (Heebo/Rubik), responsive design.
"""

import sys
import os
import json
import sqlite3
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import List, Dict, Any, Optional

import database

PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
DB_PATH = database.DEFAULT_DB_PATH

INDEX_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>שנתון האוניברסיטה העברית | מערכת שעות, כיתות וסילבוסים</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800&family=Rubik:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #003366;
      --primary-hover: #002244;
      --gold: #b38f4d;
      --gold-hover: #9c7c3d;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --border-focus: #2563eb;
      --badge-bg: #eff6ff;
      --badge-text: #1d4ed8;
      --shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.08);
      --shadow: 0 4px 12px -2px rgb(0 0 0 / 0.1);
      --shadow-lg: 0 10px 25px -5px rgb(0 0 0 / 0.15);
      --radius: 12px;
      --free-bg: #f0fdf4;
      --free-border: #86efac;
      --busy-bg: #eff6ff;
      --busy-border: #3b82f6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Heebo', system-ui, -apple-system, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      direction: rtl;
    }
    header {
      background: linear-gradient(135deg, var(--primary) 0%, #001f3f 100%);
      color: white;
      padding: 0.85rem 2rem;
      box-shadow: 0 4px 14px rgba(0,0,0,0.18);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .header-content {
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }
    .logo-area {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      cursor: pointer;
    }
    .logo-badge {
      background: var(--gold);
      color: #fff;
      font-weight: 800;
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      font-size: 1.15rem;
      font-family: 'Rubik', sans-serif;
      letter-spacing: -0.5px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    }
    .header-title h1 {
      font-size: 1.35rem;
      font-weight: 700;
      font-family: 'Rubik', sans-serif;
    }
    .header-title p {
      font-size: 0.82rem;
      color: #cbd5e1;
    }
    .nav-tabs {
      display: flex;
      gap: 0.4rem;
      background: rgba(255,255,255,0.12);
      padding: 4px;
      border-radius: 10px;
    }
    .nav-btn {
      background: transparent;
      border: none;
      color: #e2e8f0;
      padding: 0.55rem 1.1rem;
      border-radius: 8px;
      cursor: pointer;
      font-family: inherit;
      font-size: 0.92rem;
      font-weight: 600;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
    }
    .nav-btn.active {
      background: white;
      color: var(--primary);
      box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    .nav-btn:hover:not(.active) {
      background: rgba(255,255,255,0.2);
      color: white;
    }
    .counter-badge {
      background: var(--gold);
      color: white;
      font-size: 0.75rem;
      padding: 2px 7px;
      border-radius: 10px;
      font-weight: 700;
    }
    main {
      max-width: 1440px;
      margin: 1.5rem auto;
      padding: 0 1.5rem 3rem;
    }
    .tab-view { display: none; }
    .tab-view.active { display: block; animation: fadeIn 0.25s ease-out; }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Common Card & Buttons */
    .card {
      background: var(--card-bg);
      border-radius: var(--radius);
      padding: 1.25rem;
      box-shadow: var(--shadow-sm);
      border: 1px solid var(--border);
      margin-bottom: 1.25rem;
    }
    .btn {
      padding: 0.65rem 1.25rem;
      border: none;
      border-radius: 8px;
      font-family: inherit;
      font-size: 0.92rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.45rem;
      transition: all 0.18s;
      text-decoration: none;
    }
    .btn-primary { background: var(--primary); color: white; }
    .btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }
    .btn-secondary { background: #f1f5f9; color: var(--text); border: 1px solid var(--border); }
    .btn-secondary:hover { background: #e2e8f0; }
    .btn-gold { background: var(--gold); color: white; }
    .btn-gold:hover { background: var(--gold-hover); }
    .btn-sm { padding: 0.4rem 0.8rem; font-size: 0.82rem; border-radius: 6px; }

    /* Filter Form */
    .filter-grid {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr 1fr auto;
      gap: 0.75rem;
      align-items: center;
    }
    @media (max-width: 1100px) {
      .filter-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 650px) {
      .filter-grid { grid-template-columns: 1fr; }
    }
    .input-wrapper { position: relative; width: 100%; }
    .input-text, .input-select {
      width: 100%;
      padding: 0.7rem 0.9rem;
      font-size: 0.95rem;
      border: 1.5px solid var(--border);
      border-radius: 8px;
      outline: none;
      font-family: inherit;
      background: white;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .input-text:focus, .input-select:focus {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
    }

    /* Course Cards List */
    .courses-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(430px, 1fr));
      gap: 1.25rem;
      margin-top: 1rem;
    }
    @media (max-width: 500px) {
      .courses-grid { grid-template-columns: 1fr; }
    }
    .course-card {
      background: white;
      border: 1.5px solid var(--border);
      border-radius: var(--radius);
      padding: 1.2rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: all 0.2s;
      box-shadow: var(--shadow-sm);
    }
    .course-card:hover {
      border-color: #93c5fd;
      transform: translateY(-2px);
      box-shadow: var(--shadow);
    }
    .course-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }
    .course-code {
      font-family: 'Rubik', sans-serif;
      font-weight: 700;
      color: var(--primary);
      font-size: 1.15rem;
    }
    .course-points {
      background: #fef3c7;
      color: #92400e;
      font-weight: 700;
      font-size: 0.8rem;
      padding: 3px 9px;
      border-radius: 20px;
    }
    .course-title-he {
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--text);
      line-height: 1.35;
      margin-bottom: 0.25rem;
    }
    .course-title-en {
      font-size: 0.85rem;
      color: var(--text-muted);
      direction: ltr;
      text-align: right;
      margin-bottom: 0.75rem;
    }
    .badge-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      margin-bottom: 0.85rem;
    }
    .tag {
      font-size: 0.78rem;
      padding: 2px 8px;
      border-radius: 6px;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .tag-faculty { background: #f1f5f9; color: #475569; }
    .tag-year { background: #e0e7ff; color: #3730a3; font-weight: 600; }
    .tag-semester { background: #dcfce7; color: #166534; }
    .tag-teacher {
      background: #fae8ff;
      color: #86198f;
      cursor: pointer;
      transition: background 0.15s;
    }
    .tag-teacher:hover { background: #f0abfc; color: #701a75; }
    .course-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.75rem;
      padding-top: 0.75rem;
      border-top: 1px solid #f1f5f9;
    }

    /* Modal Styles */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.65);
      backdrop-filter: blur(4px);
      z-index: 100;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }
    .modal-overlay.active { display: flex; animation: fadeIn 0.2s; }
    .modal-box {
      background: white;
      border-radius: 16px;
      max-width: 900px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-lg);
      overflow: hidden;
    }
    .modal-header {
      background: linear-gradient(135deg, var(--primary) 0%, #002244 100%);
      color: white;
      padding: 1.25rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
    }
    .modal-close {
      background: rgba(255,255,255,0.15);
      border: none;
      color: white;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      font-size: 1.1rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
    }
    .modal-close:hover { background: rgba(255,255,255,0.3); }
    .modal-subtabs {
      display: flex;
      background: #f1f5f9;
      border-bottom: 1px solid var(--border);
      padding: 0 1.5rem;
      overflow-x: auto;
    }
    .modal-tab-btn {
      padding: 0.75rem 1.2rem;
      border: none;
      background: transparent;
      font-family: inherit;
      font-size: 0.92rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border-bottom: 3px solid transparent;
      white-space: nowrap;
    }
    .modal-tab-btn.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
      background: white;
    }
    .modal-body {
      padding: 1.5rem;
      overflow-y: auto;
      flex: 1;
    }
    .modal-subpane { display: none; }
    .modal-subpane.active { display: block; animation: fadeIn 0.2s; }
    .section-title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--primary);
      margin: 1rem 0 0.5rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .section-title:first-child { margin-top: 0; }
    .info-box {
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem;
      margin-bottom: 1rem;
      line-height: 1.6;
    }
    .info-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.5rem;
      font-size: 0.92rem;
    }
    .info-table th, .info-table td {
      border: 1px solid var(--border);
      padding: 0.6rem 0.8rem;
      text-align: right;
    }
    .info-table th { background: #f1f5f9; font-weight: 600; color: var(--primary); }

    /* Dedicated Classroom Occupancy View */
    .room-header-card {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: white;
      border-radius: var(--radius);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: var(--shadow);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1.25rem;
    }
    .room-title-h2 {
      font-size: 1.6rem;
      font-weight: 800;
      font-family: 'Rubik', sans-serif;
      margin-bottom: 0.3rem;
    }
    .room-subtitle {
      color: #94a3b8;
      font-size: 0.95rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .room-stats-chips {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }
    .stat-chip {
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 10px;
      padding: 0.6rem 1rem;
      text-align: center;
    }
    .stat-chip-num {
      font-size: 1.3rem;
      font-weight: 800;
      color: #38bdf8;
      font-family: 'Rubik', sans-serif;
    }
    .stat-chip-lbl { font-size: 0.75rem; color: #cbd5e1; }

    /* Timetable Grid (Used in Classroom Occupancy & My Timetable) */
    .timetable-wrapper {
      background: white;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow-x: auto;
      box-shadow: var(--shadow-sm);
    }
    .timetable-grid {
      display: grid;
      grid-template-columns: 70px repeat(6, minmax(170px, 1fr));
      min-width: 1100px;
      background: #cbd5e1;
      gap: 1px;
    }
    .tt-header-cell {
      background: #f1f5f9;
      color: var(--primary);
      font-weight: 700;
      padding: 0.85rem 0.5rem;
      text-align: center;
      font-size: 0.95rem;
    }
    .tt-time-col {
      background: #f8fafc;
      color: var(--text-muted);
      font-weight: 600;
      font-size: 0.82rem;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding-top: 6px;
      border-bottom: 1px solid #e2e8f0;
      height: 60px;
    }
    .tt-cell {
      background: white;
      height: 60px;
      position: relative;
      border-bottom: 1px solid #f1f5f9;
      transition: background 0.15s;
    }
    .tt-cell.is-free:hover {
      background: #f0fdf4;
    }
    .tt-event {
      position: absolute;
      left: 3px;
      right: 3px;
      border-radius: 6px;
      padding: 4px 6px;
      font-size: 0.75rem;
      overflow: hidden;
      cursor: pointer;
      z-index: 10;
      box-shadow: 0 1px 3px rgba(0,0,0,0.12);
      transition: transform 0.15s, box-shadow 0.15s;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .tt-event:hover {
      transform: scale(1.02);
      box-shadow: 0 4px 8px rgba(0,0,0,0.18);
      z-index: 20;
    }
    .tt-event-title {
      font-weight: 700;
      line-height: 1.2;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .tt-event-subtitle {
      font-size: 0.7rem;
      opacity: 0.9;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Lecturer Hub Grid */
    .teachers-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1rem;
      margin-top: 1rem;
    }
    .teacher-card {
      background: white;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.1rem;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .teacher-card:hover {
      border-color: var(--primary);
      box-shadow: var(--shadow);
      transform: translateY(-2px);
    }
    .teacher-name {
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 0.25rem;
    }
    .teacher-email {
      font-size: 0.82rem;
      color: var(--text-muted);
      direction: ltr;
      text-align: right;
    }
    .teacher-meta {
      display: flex;
      gap: 0.75rem;
      margin-top: 0.85rem;
      font-size: 0.82rem;
      color: #475569;
    }

    /* Quick Hall Chips */
    .quick-chips-bar {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      align-items: center;
      margin-top: 0.6rem;
    }
    .chip-btn {
      background: white;
      border: 1px solid var(--border);
      padding: 4px 10px;
      border-radius: 16px;
      font-size: 0.82rem;
      font-weight: 500;
      cursor: pointer;
      color: #334155;
      transition: all 0.15s;
    }
    .chip-btn:hover, .chip-btn.active {
      background: var(--primary);
      color: white;
      border-color: var(--primary);
    }
    .clickable-link {
      color: var(--primary);
      text-decoration: underline;
      cursor: pointer;
      font-weight: 600;
    }
    .clickable-link:hover {
      color: #2563eb;
    }
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="header-content">
      <div class="logo-area" onclick="switchNavTab('catalog')">
        <div class="logo-badge">HUJI</div>
        <div class="header-title">
          <h1>שנתון האוניברסיטה העברית</h1>
          <p>מאגר קורסים מתקדם, סילבוסים, לוח תפוסת כיתות ואיתור מרצים</p>
        </div>
      </div>
      <nav class="nav-tabs">
        <button class="nav-btn active" id="nav-catalog" onclick="switchNavTab('catalog')">
          <span>📚 קטלוג וחיפוש קורסים</span>
        </button>
        <button class="nav-btn" id="nav-rooms" onclick="switchNavTab('rooms')">
          <span>🏛️ תפוסת כיתות ואולמות</span>
        </button>
        <button class="nav-btn" id="nav-teachers" onclick="switchNavTab('teachers')">
          <span>👨‍🏫 סגל ומרצים</span>
        </button>
        <button class="nav-btn" id="nav-schedule" onclick="switchNavTab('schedule')">
          <span>📅 המערכת שלי</span>
          <span class="counter-badge" id="savedCount">0</span>
        </button>
      </nav>
    </div>
  </header>

  <main>
    <!-- TAB 1: CATALOG & COURSES SEARCH -->
    <div id="view-catalog" class="tab-view active">
      <div class="card">
        <div class="filter-grid">
          <div class="input-wrapper">
            <input type="text" id="searchInput" class="input-text" placeholder="חיפוש לפי שם קורס, מספר, מרצה או מילת מפתח..." onkeyup="handleSearchKey(event)">
          </div>
          <select id="facultySelect" class="input-select" onchange="onFacultyChange()">
            <option value="">כל הפקולטות</option>
          </select>
          <select id="deptSelect" class="input-select" onchange="performSearch()">
            <option value="">כל החוגים</option>
          </select>
          <select id="yearSelect" class="input-select" onchange="performSearch()">
            <option value="">כל השנים</option>
            <option value="1">שנה א'</option>
            <option value="2">שנה ב'</option>
            <option value="3">שנה ג'</option>
            <option value="4">שנה ד' ומעלה</option>
          </select>
          <select id="semesterSelect" class="input-select" onchange="performSearch()">
            <option value="">כל הסמסטרים</option>
            <option value="1">סמסטר א'</option>
            <option value="2">סמסטר ב'</option>
            <option value="3">שנתי</option>
            <option value="4">סמסטר קיץ</option>
          </select>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-primary" onclick="performSearch()">🔍 חפש</button>
            <button class="btn btn-secondary" onclick="resetFilters()">איפוס</button>
          </div>
        </div>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
        <div id="resultsCount" style="font-weight: 600; color: var(--text-muted); font-size: 0.95rem;">טוען קורסים...</div>
        <div style="font-size: 0.85rem; color: var(--text-muted);">מציג עד 150 קורסים התואמים את החיפוש</div>
      </div>

      <div id="coursesList" class="courses-grid"></div>
    </div>

    <!-- TAB 2: DEDICATED CLASSROOM & AUDITORIUM OCCUPANCY -->
    <div id="view-rooms" class="tab-view">
      <div class="card">
        <h3 style="color: var(--primary); margin-bottom: 0.75rem; font-family: 'Rubik', sans-serif;">🔍 איתור כיתה או אולם הרצאות</h3>
        <div class="filter-grid" style="grid-template-columns: 1fr 1fr 2fr auto;">
          <select id="campusFilter" class="input-select" onchange="onCampusFilterChange()">
            <option value="">כל הקמפוסים</option>
            <option value="אדמונד י. ספרא">קמפוס ספרא (גבעת רם)</option>
            <option value="הר הצופים">קמפוס הר הצופים</option>
            <option value="עין כרם">קמפוס עין כרם</option>
            <option value="רחובות">קמפוס רחובות</option>
          </select>
          <select id="buildingFilter" class="input-select" onchange="onBuildingFilterChange()">
            <option value="">כל הבניינים</option>
          </select>
          <div class="input-wrapper">
            <input type="text" id="roomSearchInput" list="roomsDatalist" class="input-text" placeholder="הקלד שם כיתה / אולם (למשל: אודיטוריום הנדסה, קנדה, 101...)" onchange="onRoomSelectedFromInput()">
            <datalist id="roomsDatalist"></datalist>
          </div>
          <button class="btn btn-primary" onclick="loadSelectedRoomSchedule()">הצג לוח תפוסה</button>
        </div>

        <div class="quick-chips-bar">
          <span style="font-size: 0.82rem; font-weight: 600; color: var(--text-muted);">אולמות מובילים:</span>
          <button class="chip-btn" onclick="quickSelectRoom('אודיטוריום הנדסה', 'אדמונד י. ספרא')">אודיטוריום הנדסה</button>
          <button class="chip-btn" onclick="quickSelectRoom('טבע קנדה', 'אדמונד י. ספרא')">טבע קנדה</button>
          <button class="chip-btn" onclick="quickSelectRoom('שפרינצק 214', 'אדמונד י. ספרא')">שפרינצק 214</button>
          <button class="chip-btn" onclick="quickSelectRoom('רוטברג אולם הרצאות', 'הר הצופים')">רוטברג הרצאות</button>
          <button class="chip-btn" onclick="quickSelectRoom('אולם מגל', 'הר הצופים')">אולם מגל</button>
          <button class="chip-btn" onclick="quickSelectRoom('אולם סמואלס', 'אדמונד י. ספרא')">סמואלס</button>
          <button class="chip-btn" onclick="quickSelectRoom('אולם גילברט', 'אדמונד י. ספרא')">גילברט</button>
        </div>
      </div>

      <!-- Room Header Info -->
      <div id="roomHeaderBox" class="room-header-card" style="display: none;">
        <div>
          <div class="room-title-h2" id="roomDisplayTitle">שם האולם</div>
          <div class="room-subtitle">
            <span id="roomDisplayBuilding">בניין</span>
            <span>•</span>
            <span id="roomDisplayCampus">קמפוס</span>
          </div>
        </div>
        <div class="room-stats-chips">
          <div class="stat-chip">
            <div class="stat-chip-num" id="statWeeklySessions">0</div>
            <div class="stat-chip-lbl">שיעורים בשבוע</div>
          </div>
          <div class="stat-chip">
            <div class="stat-chip-num" id="statWeeklyHours">0</div>
            <div class="stat-chip-lbl">שעות הוראה</div>
          </div>
          <div class="stat-chip">
            <div class="stat-chip-num" id="statFreeHours" style="color: #4ade80;">0</div>
            <div class="stat-chip-lbl">שעות פנויות</div>
          </div>
        </div>
      </div>

      <!-- Weekly Occupancy Timetable Grid (08:00 - 20:00, Sun - Fri) -->
      <div id="roomTimetableContainer" style="display: none;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
          <h4 style="color: var(--primary);">📅 לוח תפוסה שבועי (08:00 - 20:00)</h4>
          <div style="display: flex; gap: 0.75rem; font-size: 0.85rem; align-items: center;">
            <span style="display: inline-flex; align-items: center; gap: 4px;">
              <span style="width: 12px; height: 12px; background: #3b82f6; border-radius: 3px; display: inline-block;"></span> תפוס (שיעור/הרצאה)
            </span>
            <span style="display: inline-flex; align-items: center; gap: 4px;">
              <span style="width: 12px; height: 12px; background: #f0fdf4; border: 1px solid #86efac; border-radius: 3px; display: inline-block;"></span> פנוי
            </span>
          </div>
        </div>

        <div class="timetable-wrapper">
          <div class="timetable-grid" id="roomTimetableGrid">
            <div class="tt-header-cell">שעה</div>
            <div class="tt-header-cell">ראשון</div>
            <div class="tt-header-cell">שני</div>
            <div class="tt-header-cell">שלישי</div>
            <div class="tt-header-cell">רביעי</div>
            <div class="tt-header-cell">חמישי</div>
            <div class="tt-header-cell">שישי</div>
          </div>
        </div>

        <!-- Detailed Sessions Table in Room -->
        <div class="card" style="margin-top: 1.5rem;">
          <h4 style="color: var(--primary); margin-bottom: 0.75rem;">📋 פירוט כל השיעורים המתקיימים בכיתה</h4>
          <table class="info-table" id="roomSessionsTable">
            <thead>
              <tr>
                <th>יום</th>
                <th>שעות</th>
                <th>מספר קורס</th>
                <th>שם הקורס</th>
                <th>סוג</th>
                <th>מרצה / מתרגל</th>
                <th>פעולות</th>
              </tr>
            </thead>
            <tbody id="roomSessionsTableBody"></tbody>
          </table>
        </div>
      </div>
      <div id="roomEmptyNotice" class="card" style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🏫</div>
        <div style="font-size: 1.1rem; font-weight: 600;">בחר כיתה או אולם למעלה כדי לצפות בלוח התפוסה המלא</div>
        <p style="font-size: 0.9rem; margin-top: 0.25rem;">ניתן לסנן לפי קמפוס, בניין או לבחור מהאולמות המובילים.</p>
      </div>
    </div>

    <!-- TAB 3: LECTURERS & STAFF HUB -->
    <div id="view-teachers" class="tab-view">
      <div class="card">
        <h3 style="color: var(--primary); margin-bottom: 0.75rem; font-family: 'Rubik', sans-serif;">👨‍🏫 איתור מרצים, מתרגלים וסגל הוראה</h3>
        <div style="display: flex; gap: 0.75rem; max-width: 600px;">
          <input type="text" id="teacherSearchInput" class="input-text" placeholder="הקלד שם מרצה או מתרגל..." onkeyup="if(event.key==='Enter') searchTeachers()">
          <button class="btn btn-primary" onclick="searchTeachers()">חפש סגל</button>
        </div>
      </div>

      <div id="teachersList" class="teachers-grid"></div>
    </div>

    <!-- TAB 4: MY TIMETABLE -->
    <div id="view-schedule" class="tab-view">
      <div class="card" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
        <div>
          <h3 style="color: var(--primary); font-family: 'Rubik', sans-serif;">לוח השעות השבועי שלי</h3>
          <p style="font-size: 0.85rem; color: var(--text-muted);">הקורסים ששמרת מוצגים כאן לפי ימים ושעות</p>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <button class="btn btn-secondary btn-sm" onclick="window.print()">🖨️ הדפסה</button>
          <button class="btn btn-secondary btn-sm" onclick="clearMySchedule()">🗑️ ריקון מערכת</button>
        </div>
      </div>

      <div class="card" id="selectedPillsCard">
        <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem;">קורסים שנבחרו:</div>
        <div id="selectedPills" style="display: flex; flex-wrap: wrap; gap: 0.5rem;"></div>
      </div>

      <div class="timetable-wrapper">
        <div class="timetable-grid" id="myTimetableGrid">
          <div class="tt-header-cell">שעה</div>
          <div class="tt-header-cell">ראשון</div>
          <div class="tt-header-cell">שני</div>
          <div class="tt-header-cell">שלישי</div>
          <div class="tt-header-cell">רביעי</div>
          <div class="tt-header-cell">חמישי</div>
          <div class="tt-header-cell">שישי</div>
        </div>
      </div>
    </div>
  </main>

  <!-- MODAL: COURSE DETAILS & SYLLABUS -->
  <div id="courseModal" class="modal-overlay" onclick="onModalOverlayClick(event, 'courseModal')">
    <div class="modal-box">
      <div class="modal-header">
        <div>
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span class="course-code" id="modalCourseCode" style="color: #93c5fd; font-size: 1.3rem;">00000</span>
            <h2 id="modalCourseTitleHe" style="font-size: 1.25rem;">שם הקורס</h2>
          </div>
          <div id="modalCourseTitleEn" style="color: #cbd5e1; font-size: 0.85rem; direction: ltr; text-align: right;">Course Name English</div>
        </div>
        <button class="modal-close" onclick="closeModal('courseModal')">✕</button>
      </div>

      <!-- Subtabs inside Course Modal -->
      <div class="modal-subtabs">
        <button class="modal-tab-btn active" onclick="switchModalTab('overview')">סקירה ומטרות</button>
        <button class="modal-tab-btn" onclick="switchModalTab('syllabus')">סילבוס ונושאים</button>
        <button class="modal-tab-btn" onclick="switchModalTab('requirements')">דרישות והערכה</button>
        <button class="modal-tab-btn" onclick="switchModalTab('roadmaps')">תוכניות לימוד וחוגים</button>
        <button class="modal-tab-btn" onclick="switchModalTab('sessions')">קבוצות ולוח זמנים</button>
        <button class="modal-tab-btn" onclick="switchModalTab('exams')">מועדי בחינות</button>
      </div>

      <div class="modal-body">
        <!-- Subpane 1: Overview -->
        <div id="modal-pane-overview" class="modal-subpane active">
          <div class="info-box">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; font-size: 0.92rem;">
              <div><strong>פקולטה:</strong> <span id="mFaculty">-</span></div>
              <div><strong>חוג:</strong> <span id="mDept">-</span></div>
              <div><strong>נקודות זכות:</strong> <span id="mPoints">-</span></div>
              <div><strong>סמסטר:</strong> <span id="mSemester">-</span></div>
              <div><strong>שעות שבועיות:</strong> <span id="mHours">-</span></div>
              <div><strong>מיועד לשנים:</strong> <span id="mStudyYears" style="color: #2563eb; font-weight: 700;">-</span></div>
            </div>
            <div id="mCoordinatorBox" style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px dashed var(--border); font-size: 0.92rem;">
              <strong>רכז/ת הקורס:</strong> <span id="mCoordinator">-</span>
            </div>
          </div>

          <div class="section-title">📝 תיאור הקורס</div>
          <div class="info-box" id="mDescription">אין תיאור זמין.</div>

          <div class="section-title">🎯 מטרות הקורס</div>
          <div class="info-box" id="mAims">לא צוינו מטרות ספציפיות.</div>
        </div>

        <!-- Subpane 2: Syllabus & Content -->
        <div id="modal-pane-syllabus" class="modal-subpane">
          <div class="section-title">🎓 תוצרי למידה</div>
          <div class="info-box" id="mOutcomes">לא צוינו תוצרי למידה.</div>

          <div class="section-title">📚 תוכן הקורס ורשימת נושאים</div>
          <div class="info-box" id="mContent">לא צוין פירוט נושאים.</div>

          <div class="section-title">🧑‍🏫 שיטת הוראה</div>
          <div class="info-box" id="mMethod">לא צוין.</div>
        </div>

        <!-- Subpane 3: Requirements & Evaluation -->
        <div id="modal-pane-requirements" class="modal-subpane">
          <div class="section-title">🔒 דרישות קדם וקורסים חוסמים</div>
          <div class="info-box" id="mPrereqs">אין דרישות קדם רשומות לקורס זה.</div>

          <div class="section-title">📊 הרכב הציון הסופי</div>
          <div class="info-box" id="mEvaluation">לא הוגדר הרכב ציון.</div>
        </div>

        <!-- Subpane 4: Roadmaps & Programs -->
        <div id="modal-pane-roadmaps" class="modal-subpane">
          <div class="section-title">🧭 תוכניות לימוד, מסלולים וחוגים בהם נלמד הקורס</div>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">להלן המסלולים והחוגים האקדמיים שקורס זה נכלל בהם:</p>
          <table class="info-table" id="mRoadmapsTable">
            <thead>
              <tr>
                <th>שם תוכנית הלימודים / מסלול</th>
                <th>חוג</th>
                <th>תואר</th>
                <th>היקף</th>
                <th>שנת לימוד</th>
              </tr>
            </thead>
            <tbody id="mRoadmapsBody"></tbody>
          </table>
        </div>

        <!-- Subpane 5: Groups & Sessions -->
        <div id="modal-pane-sessions" class="modal-subpane">
          <div class="section-title">🗓️ קבוצות לימוד, מועדים וכיתות</div>
          <div id="mGroupsContainer"></div>
        </div>

        <!-- Subpane 6: Exams -->
        <div id="modal-pane-exams" class="modal-subpane">
          <div class="section-title">📝 מועדי בחינות</div>
          <table class="info-table" id="mExamsTable">
            <thead>
              <tr>
                <th>מועד</th>
                <th>תאריך ושעה</th>
                <th>קמפוס ובניין</th>
                <th>כיתה/אולם</th>
              </tr>
            </thead>
            <tbody id="mExamsBody"></tbody>
          </table>
        </div>
      </div>
      <div style="padding: 1rem 1.5rem; background: #f8fafc; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 0.5rem;">
        <button class="btn btn-primary" id="mBtnScheduleToggle" onclick="toggleCurrentModalCourse()">הוסף למערכת השעות</button>
        <button class="btn btn-secondary" onclick="closeModal('courseModal')">סגור</button>
      </div>
    </div>
  </div>

  <!-- MODAL: LECTURER PROFILE & SCHEDULE -->
  <div id="teacherModal" class="modal-overlay" onclick="onModalOverlayClick(event, 'teacherModal')">
    <div class="modal-box" style="max-width: 800px;">
      <div class="modal-header">
        <div>
          <h2 id="teacherModalName">שם המרצה</h2>
          <div id="teacherModalEmail" style="color: #cbd5e1; font-size: 0.88rem; direction: ltr; text-align: right;">email@huji.ac.il</div>
        </div>
        <button class="modal-close" onclick="closeModal('teacherModal')">✕</button>
      </div>
      <div class="modal-body">
        <div class="section-title">📚 קורסים המועברים על ידי המרצה</div>
        <div id="teacherCoursesList" style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem;"></div>

        <div class="section-title">🗓️ לוח הוראה שבועי של המרצה</div>
        <table class="info-table">
          <thead>
            <tr>
              <th>יום</th>
              <th>שעות</th>
              <th>קורס</th>
              <th>סוג</th>
              <th>מיקום (קמפוס / בניין / כיתה)</th>
            </tr>
          </thead>
          <tbody id="teacherSessionsTableBody"></tbody>
        </table>
      </div>
      <div style="padding: 1rem 1.5rem; background: #f8fafc; border-top: 1px solid var(--border); display: flex; justify-content: flex-end;">
        <button class="btn btn-secondary" onclick="closeModal('teacherModal')">סגור</button>
      </div>
    </div>
  </div>

  <script>
    // State
    let allFaculties = [];
    let allRooms = [];
    let myScheduleCourses = JSON.parse(localStorage.getItem('my_huji_schedule') || '[]');
    let currentModalCourseId = null;
    let selectedRoom = null;

    const HEBREW_DAYS = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"];

    const EVENT_COLORS = [
      { bg: '#dbeafe', border: '#2563eb', text: '#1e3a8a' },
      { bg: '#dcfce7', border: '#16a34a', text: '#14532d' },
      { bg: '#fef3c7', border: '#d97706', text: '#78350f' },
      { bg: '#f3e8ff', border: '#9333ea', text: '#581c87' },
      { bg: '#ffe4e6', border: '#e11d48', text: '#881337' },
      { bg: '#ccfbf1', border: '#0d9488', text: '#134e4a' },
      { bg: '#ffedd5', border: '#ea580c', text: '#9a3412' },
    ];

    document.addEventListener('DOMContentLoaded', () => {
      buildTimetableSkeletons();
      loadFaculties();
      loadRoomsCatalog();
      updateSavedCount();
      performSearch();
      searchTeachers();
    });

    // Navigation Tabs
    function switchNavTab(tab) {
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));

      const btn = document.getElementById(`nav-${tab}`);
      const view = document.getElementById(`view-${tab}`);
      if (btn) btn.classList.add('active');
      if (view) view.classList.add('active');

      if (tab === 'schedule') {
        renderMySchedule();
      }
    }

    // Timetable Grid Builder (Hours 8 to 20, Days 0 to 5)
    function buildTimetableSkeletons() {
      ['myTimetableGrid', 'roomTimetableGrid'].forEach(gridId => {
        const grid = document.getElementById(gridId);
        if (!grid) return;
        for (let h = 8; h <= 20; h++) {
          const timeLabel = document.createElement('div');
          timeLabel.className = 'tt-time-col';
          timeLabel.textContent = `${h.toString().padStart(2, '0')}:00`;
          grid.appendChild(timeLabel);

          for (let d = 0; d < 6; d++) {
            const cell = document.createElement('div');
            cell.className = 'tt-cell is-free';
            cell.id = `${gridId}-cell-${d}-${h}`;
            grid.appendChild(cell);
          }
        }
      });
    }

    // Faculties & Search
    async function loadFaculties() {
      try {
        const res = await fetch('/api/faculties');
        allFaculties = await res.json();
        const sel = document.getElementById('facultySelect');
        allFaculties.forEach(f => {
          const opt = document.createElement('option');
          opt.value = f.code;
          opt.textContent = `${f.code} - ${f.name_he}`;
          sel.appendChild(opt);
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function onFacultyChange() {
      const facCode = document.getElementById('facultySelect').value;
      const deptSel = document.getElementById('deptSelect');
      deptSel.innerHTML = '<option value="">כל החוגים</option>';

      if (facCode) {
        try {
          const res = await fetch(`/api/departments?faculty=${facCode}`);
          const depts = await res.json();
          depts.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = d.name_he;
            deptSel.appendChild(opt);
          });
        } catch (e) {
          console.error(e);
        }
      }
      performSearch();
    }

    function handleSearchKey(e) {
      if (e.key === 'Enter') performSearch();
    }

    async function performSearch() {
      const q = document.getElementById('searchInput').value.trim();
      const fac = document.getElementById('facultySelect').value;
      const dept = document.getElementById('deptSelect').value;
      const year = document.getElementById('yearSelect').value;
      const sem = document.getElementById('semesterSelect').value;

      const params = new URLSearchParams();
      if (q) params.append('q', q);
      if (fac) params.append('faculty', fac);
      if (dept) params.append('dept', dept);
      if (year) params.append('year', year);
      if (sem) params.append('semester', sem);

      const countEl = document.getElementById('resultsCount');
      countEl.textContent = 'מחפש קורסים...';

      try {
        const res = await fetch(`/api/search?${params.toString()}`);
        const data = await res.json();
        countEl.textContent = `נמצאו ${data.total} קורסים פעילים`;
        renderCoursesList(data.courses);
      } catch (e) {
        countEl.textContent = 'שגיאה בחיפוש קורסים.';
        console.error(e);
      }
    }

    function resetFilters() {
      document.getElementById('searchInput').value = '';
      document.getElementById('facultySelect').value = '';
      document.getElementById('deptSelect').value = '';
      document.getElementById('yearSelect').value = '';
      document.getElementById('semesterSelect').value = '';
      performSearch();
    }

    function renderCoursesList(courses) {
      const list = document.getElementById('coursesList');
      list.innerHTML = '';

      if (!courses || courses.length === 0) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--text-muted);">לא נמצאו קורסים התואמים את החיפוש. נסה להרחיב את החיפוש.</div>';
        return;
      }

      courses.forEach(c => {
        const inSchedule = isCourseInSchedule(c.id);
        const card = document.createElement('div');
        card.className = 'course-card';

        // Study years badge
        let yearBadge = '';
        if (c.study_years) {
          const formattedYears = c.study_years.split(',').map(y => `שנה ${formatYearHebrew(y)}`).join(', ');
          yearBadge = `<span class="tag tag-year">🎓 ${formattedYears}</span>`;
        }

        // Teachers tags
        const teachersHtml = (c.teachers || []).map(t =>
          `<span class="tag tag-teacher" onclick="openTeacherModalByName('${escapeJs(t)}')">👤 ${t}</span>`
        ).join(' ');

        card.innerHTML = `
          <div>
            <div class="course-top">
              <span class="course-code">${c.code}</span>
              <span class="course-points">${c.academic_points || 0} נ"ז</span>
            </div>
            <div class="course-title-he">${c.name_he}</div>
            <div class="course-title-en">${c.name_en || ''}</div>
            <div class="badge-tags">
              ${c.faculty_name_he ? `<span class="tag tag-faculty">${c.faculty_name_he}</span>` : ''}
              ${c.semester_name_he ? `<span class="tag tag-semester">${c.semester_name_he}</span>` : ''}
              ${yearBadge}
            </div>
            ${teachersHtml ? `<div class="badge-tags" style="margin-top: 4px;">${teachersHtml}</div>` : ''}
          </div>
          <div class="course-actions">
            <button class="btn btn-primary btn-sm" onclick="openCourseModal(${c.id})">🔍 סילבוס ופרטים</button>
            <button class="btn ${inSchedule ? 'btn-secondary' : 'btn-gold'} btn-sm" onclick="toggleCourseSchedule(${c.id}, this)">
              ${inSchedule ? '✓ במערכת' : '+ הוסף למערכת'}
            </button>
          </div>
        `;
        list.appendChild(card);
      });
    }

    function formatYearHebrew(y) {
      const map = { '1': "א'", '2': "ב'", '3': "ג'", '4': "ד'", '5': "ה'", '6': "ו'" };
      return map[y.trim()] || y;
    }

    // COURSE DETAILS MODAL
    async function openCourseModal(courseId) {
      currentModalCourseId = courseId;
      const modal = document.getElementById('courseModal');
      modal.classList.add('active');
      switchModalTab('overview');

      try {
        const res = await fetch(`/api/course/${courseId}`);
        const c = await res.json();

        document.getElementById('modalCourseCode').textContent = c.code;
        document.getElementById('modalCourseTitleHe').textContent = c.name_he;
        document.getElementById('modalCourseTitleEn').textContent = c.name_en || '';

        document.getElementById('mFaculty').textContent = c.faculty_name_he || '-';
        document.getElementById('mDept').textContent = c.department_name_he || '-';
        document.getElementById('mPoints').textContent = (c.academic_points || 0) + ' נ"ז';
        document.getElementById('mSemester').textContent = c.semester_name_he || '-';
        document.getElementById('mHours').textContent = (c.total_hours || 0) + ' שעות';

        // Study Years
        if (c.study_years) {
          document.getElementById('mStudyYears').textContent = c.study_years.split(',').map(y => `שנה ${formatYearHebrew(y)}`).join(', ');
        } else {
          document.getElementById('mStudyYears').textContent = 'כל השנים / לא הוגדר';
        }

        // Coordinator
        const coordBox = document.getElementById('mCoordinatorBox');
        if (c.course_coordinator) {
          coordBox.style.display = 'block';
          document.getElementById('mCoordinator').innerHTML = `${c.course_coordinator} ${c.coordinator_email ? `(<a href="mailto:${c.coordinator_email}">${c.coordinator_email}</a>)` : ''}`;
        } else {
          coordBox.style.display = 'none';
        }

        // Overview & Syllabus
        document.getElementById('mDescription').innerHTML = c.description || 'אין תיאור זמין.';
        document.getElementById('mAims').innerHTML = c.aims || 'לא צוינו מטרות ספציפיות.';
        document.getElementById('mOutcomes').innerHTML = c.learning_outcomes || 'לא צוינו תוצרי למידה.';
        document.getElementById('mContent').innerHTML = c.content || 'לא צוין פירוט נושאים.';
        document.getElementById('mMethod').innerHTML = c.teaching_method || 'לא צוין.';

        // Requirements & Evaluation
        document.getElementById('mPrereqs').innerHTML = c.prerequisites || 'אין דרישות קדם רשומות לקורס זה.';
        document.getElementById('mEvaluation').innerHTML = c.evaluation_breakdown || 'לא הוגדר הרכב ציון.';

        // Roadmaps
        const rmBody = document.getElementById('mRoadmapsBody');
        rmBody.innerHTML = '';
        if (c.roadmaps && c.roadmaps.length > 0) {
          c.roadmaps.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td><strong>${r.roadmap_name_he || '-'}</strong></td>
              <td>${r.department_name_he || '-'}</td>
              <td>${r.degree_name_he || '-'}</td>
              <td>${r.scope_name_he || '-'}</td>
              <td>${r.study_years ? r.study_years.split(',').map(y => `שנה ${formatYearHebrew(y)}`).join(', ') : '-'}</td>
            `;
            rmBody.appendChild(tr);
          });
        } else {
          rmBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">לא נמצאו תוכניות לימוד מוגדרות עבור קורס זה במאגר.</td></tr>';
        }

        // Groups & Sessions
        const groupsDiv = document.getElementById('mGroupsContainer');
        groupsDiv.innerHTML = '';
        if (c.groups && c.groups.length > 0) {
          c.groups.forEach(g => {
            const gCard = document.createElement('div');
            gCard.className = 'info-box';
            gCard.style.marginBottom = '0.75rem';

            let sessionsHtml = '';
            (g.sessions || []).forEach(s => {
              const teachersList = (s.teachers || []).map(t =>
                `<span class="clickable-link" onclick="openTeacherModalByName('${escapeJs(t.name_he || t.name_en)}')">${t.name_he || t.name_en}</span>`
              ).join(', ') || 'לא נקבע מרצה';

              const roomStr = s.room_name_he ?
                `<span class="clickable-link" onclick="jumpToRoomOccupancy('${escapeJs(s.room_name_he)}', '${escapeJs(s.building_name_he || '')}', '${escapeJs(s.campus_name_he || '')}')">📍 ${s.room_name_he} (${s.building_name_he || ''})</span>` :
                'ללא חדר מוגדר';

              sessionsHtml += `
                <div style="margin-top: 4px; font-size: 0.9rem;">
                  🗓️ <strong>${s.day_name_he || ''}</strong> ${s.start_time || ''}-${s.end_time || ''} | ${roomStr} | מורה: ${teachersList}
                </div>
              `;
            });

            gCard.innerHTML = `
              <div style="font-weight: 700; color: var(--primary); font-size: 0.95rem;">
                קבוצה ${g.group_code || ''} - ${g.session_type_name_he || 'שיעור'} (${g.period_name_he || ''})
              </div>
              ${sessionsHtml || '<div style="font-size: 0.85rem; color: var(--text-muted);">אין מועדי שיעור מוגדרים</div>'}
            `;
            groupsDiv.appendChild(gCard);
          });
        } else {
          groupsDiv.innerHTML = '<div class="info-box">אין קבוצות לימוד רשומות לקורס זה.</div>';
        }

        // Exams
        const exBody = document.getElementById('mExamsBody');
        exBody.innerHTML = '';
        if (c.exams && c.exams.length > 0) {
          c.exams.forEach(e => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td><strong>מועד ${e.moed || ''}</strong></td>
              <td>${e.start_time || '-'}</td>
              <td>${e.campus_name_he || ''} ${e.building_name_he ? '• ' + e.building_name_he : ''}</td>
              <td>${e.room_name_he || '-'}</td>
            `;
            exBody.appendChild(tr);
          });
        } else {
          exBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">לא נקבעו עדיין מועדי בחינות.</td></tr>';
        }

        updateModalScheduleButton();
      } catch (err) {
        console.error(err);
      }
    }

    function switchModalTab(tabName) {
      document.querySelectorAll('.modal-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.modal-subpane').forEach(p => p.classList.remove('active'));

      const btns = Array.from(document.querySelectorAll('.modal-tab-btn'));
      const activeBtn = btns.find(b => b.getAttribute('onclick').includes(tabName));
      if (activeBtn) activeBtn.classList.add('active');

      const pane = document.getElementById(`modal-pane-${tabName}`);
      if (pane) pane.classList.add('active');
    }

    function updateModalScheduleButton() {
      const btn = document.getElementById('mBtnScheduleToggle');
      if (isCourseInSchedule(currentModalCourseId)) {
        btn.textContent = '✓ הסר ממערכת השעות';
        btn.className = 'btn btn-secondary';
      } else {
        btn.textContent = '+ הוסף למערכת השעות';
        btn.className = 'btn btn-primary';
      }
    }

    function toggleCurrentModalCourse() {
      if (currentModalCourseId) {
        toggleCourseSchedule(currentModalCourseId);
        updateModalScheduleButton();
      }
    }

    function closeModal(modalId) {
      document.getElementById(modalId).classList.remove('active');
    }

    function onModalOverlayClick(e, modalId) {
      if (e.target.id === modalId) closeModal(modalId);
    }

    // CLASSROOM & AUDITORIUM OCCUPANCY
    async function loadRoomsCatalog() {
      try {
        const res = await fetch('/api/rooms');
        allRooms = await res.json();

        // Populate datalist & buildings
        updateRoomDatalist();
        populateBuildingsDropdown();
      } catch (e) {
        console.error(e);
      }
    }

    function populateBuildingsDropdown() {
      const campus = document.getElementById('campusFilter').value;
      const bSel = document.getElementById('buildingFilter');
      bSel.innerHTML = '<option value="">כל הבניינים</option>';

      const buildings = new Set();
      allRooms.forEach(r => {
        if (!campus || (r.campus && r.campus.includes(campus))) {
          if (r.building) buildings.add(r.building);
        }
      });

      Array.from(buildings).sort().forEach(b => {
        const opt = document.createElement('option');
        opt.value = b;
        opt.textContent = b;
        bSel.appendChild(opt);
      });
    }

    function updateRoomDatalist() {
      const campus = document.getElementById('campusFilter').value;
      const building = document.getElementById('buildingFilter').value;
      const datalist = document.getElementById('roomsDatalist');
      datalist.innerHTML = '';

      allRooms.forEach(r => {
        if (campus && (!r.campus || !r.campus.includes(campus))) return;
        if (building && r.building !== building) return;
        const opt = document.createElement('option');
        opt.value = r.room;
        opt.label = `${r.building || ''} (${r.campus || ''}) - ${r.total_sessions} שיעורים`;
        datalist.appendChild(opt);
      });
    }

    function onCampusFilterChange() {
      populateBuildingsDropdown();
      updateRoomDatalist();
    }

    function onBuildingFilterChange() {
      updateRoomDatalist();
    }

    function onRoomSelectedFromInput() {
      const val = document.getElementById('roomSearchInput').value.trim();
      if (val) loadSelectedRoomSchedule();
    }

    function quickSelectRoom(roomName, campusName) {
      document.getElementById('roomSearchInput').value = roomName;
      if (campusName) {
        document.getElementById('campusFilter').value = campusName;
        onCampusFilterChange();
      }
      loadSelectedRoomSchedule();
    }

    function jumpToRoomOccupancy(roomName, buildingName, campusName) {
      closeModal('courseModal');
      switchNavTab('rooms');
      document.getElementById('roomSearchInput').value = roomName;
      if (campusName) {
        document.getElementById('campusFilter').value = campusName;
        onCampusFilterChange();
      }
      if (buildingName) {
        document.getElementById('buildingFilter').value = buildingName;
        updateRoomDatalist();
      }
      loadSelectedRoomSchedule();
    }

    async function loadSelectedRoomSchedule() {
      const room = document.getElementById('roomSearchInput').value.trim();
      const campus = document.getElementById('campusFilter').value;
      const building = document.getElementById('buildingFilter').value;

      if (!room) {
        alert('אנא הזן או בחר שם כיתה/אולם');
        return;
      }

      const params = new URLSearchParams();
      params.append('room', room);
      if (campus) params.append('campus', campus);
      if (building) params.append('building', building);

      try {
        const res = await fetch(`/api/room/schedule?${params.toString()}`);
        const sessions = await res.json();

        renderRoomWeeklySchedule(room, sessions);
      } catch (e) {
        console.error(e);
      }
    }

    function renderRoomWeeklySchedule(roomName, sessions) {
      document.getElementById('roomEmptyNotice').style.display = 'none';
      document.getElementById('roomHeaderBox').style.display = 'flex';
      document.getElementById('roomTimetableContainer').style.display = 'block';

      // Header info
      document.getElementById('roomDisplayTitle').textContent = `כיתה / אולם: ${roomName}`;
      const firstS = sessions[0] || {};
      document.getElementById('roomDisplayBuilding').textContent = firstS.building || 'בניין לא מוגדר';
      document.getElementById('roomDisplayCampus').textContent = firstS.campus || 'קמפוס לא מוגדר';

      // Clear timetable events
      document.querySelectorAll('#roomTimetableGrid .tt-event').forEach(e => e.remove());

      let totalTeachingMinutes = 0;

      sessions.forEach(s => {
        if (s.day_of_week === null || !s.start_time || !s.end_time) return;

        const [startH, startM] = s.start_time.split(':').map(Number);
        const [endH, endM] = s.end_time.split(':').map(Number);

        if (startH < 8 || startH > 20) return;

        const durationMinutes = (endH * 60 + endM) - (startH * 60 + startM);
        if (durationMinutes > 0) totalTeachingMinutes += durationMinutes;

        const cell = document.getElementById(`roomTimetableGrid-cell-${s.day_of_week}-${startH}`);
        if (!cell) return;

        const durationHours = durationMinutes / 60;
        const topOffset = (startM / 60) * 60;
        const heightPx = Math.max(26, durationHours * 60 - 4);

        const ev = document.createElement('div');
        ev.className = 'tt-event';
        ev.style.cssText = `
          top: ${topOffset}px;
          height: ${heightPx}px;
          background: #eff6ff;
          border-right: 4px solid #2563eb;
          color: #1e3a8a;
        `;
        ev.onclick = () => openCourseModal(s.course_id);

        ev.innerHTML = `
          <div class="tt-event-title">${s.course_code} - ${s.course_name_he}</div>
          <div class="tt-event-subtitle">${s.session_type || 'שיעור'} | ${s.start_time}-${s.end_time}</div>
          <div class="tt-event-subtitle" style="color: #64748b;">${s.lecturers || ''}</div>
        `;
        cell.appendChild(ev);
      });

      const totalTeachingHours = (totalTeachingMinutes / 60).toFixed(1);
      const totalWeeklySlots = 6 * 12; // 6 days * 12 hours (08:00 to 20:00) = 72 hours
      const freeHours = Math.max(0, (totalWeeklySlots - totalTeachingHours)).toFixed(1);

      document.getElementById('statWeeklySessions').textContent = sessions.length;
      document.getElementById('statWeeklyHours').textContent = `${totalTeachingHours} ש'`;
      document.getElementById('statFreeHours').textContent = `${freeHours} ש'`;

      // Render table rows
      const tbody = document.getElementById('roomSessionsTableBody');
      tbody.innerHTML = '';
      if (sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">הכיתה פנויה לחלוטין! לא מתקיימים בה שיעורים במערכת.</td></tr>';
        return;
      }

      sessions.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${s.day_name_he || ''}</strong></td>
          <td>${s.start_time} - ${s.end_time}</td>
          <td><span class="course-code" style="font-size: 0.95rem;">${s.course_code}</span></td>
          <td><strong>${s.course_name_he}</strong></td>
          <td>${s.session_type || 'שיעור'}</td>
          <td>${s.lecturers ? `<span class="clickable-link" onclick="openTeacherModalByName('${escapeJs(s.lecturers)}')">${s.lecturers}</span>` : '-'}</td>
          <td><button class="btn btn-secondary btn-sm" onclick="openCourseModal(${s.course_id})">פרטי קורס</button></td>
        `;
        tbody.appendChild(tr);
      });
    }

    // TEACHER / LECTURER PROFILE & HUB
    async function searchTeachers() {
      const q = document.getElementById('teacherSearchInput').value.trim();
      const list = document.getElementById('teachersList');
      list.innerHTML = '<div style="color: var(--text-muted); padding: 1rem;">מחפש סגל הוראה...</div>';

      try {
        const res = await fetch(`/api/teachers?q=${encodeURIComponent(q)}`);
        const teachers = await res.json();
        list.innerHTML = '';

        if (!teachers || teachers.length === 0) {
          list.innerHTML = '<div style="color: var(--text-muted); padding: 1rem;">לא נמצאו מרצים מתאימים.</div>';
          return;
        }

        teachers.slice(0, 60).forEach(t => {
          const card = document.createElement('div');
          card.className = 'teacher-card';
          card.onclick = () => openTeacherModalByName(t.name);

          card.innerHTML = `
            <div>
              <div class="teacher-name">👤 ${t.name}</div>
              <div class="teacher-email">${t.email || ''}</div>
            </div>
            <div class="teacher-meta">
              <span>📚 <strong>${t.courses_count}</strong> קורסים</span>
              <span>•</span>
              <span>🗓️ <strong>${t.sessions_count}</strong> שיעורים בשבוע</span>
            </div>
          `;
          list.appendChild(card);
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function openTeacherModalByName(teacherName) {
      if (!teacherName) return;
      // If comma-separated multiple names, pick the first
      const cleanName = teacherName.split(',')[0].trim();

      const modal = document.getElementById('teacherModal');
      modal.classList.add('active');

      document.getElementById('teacherModalName').textContent = cleanName;
      document.getElementById('teacherModalEmail').textContent = 'טוען נתונים...';

      try {
        const res = await fetch(`/api/teacher/detail?name=${encodeURIComponent(cleanName)}`);
        const data = await res.json();

        document.getElementById('teacherModalName').textContent = data.teacher_name;
        document.getElementById('teacherModalEmail').textContent = data.email || '';

        // Courses list
        const cList = document.getElementById('teacherCoursesList');
        cList.innerHTML = '';
        (data.courses || []).forEach(c => {
          const item = document.createElement('div');
          item.style.cssText = 'background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center;';
          item.innerHTML = `
            <div>
              <span class="course-code" style="font-size: 0.95rem;">${c.code}</span>
              <strong style="margin-right: 8px;">${c.name_he}</strong>
              <span style="font-size: 0.8rem; color: var(--text-muted); margin-right: 8px;">(${c.semester_name_he || ''})</span>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="openCourseModal(${c.id})">צפה בסילבוס</button>
          `;
          cList.appendChild(item);
        });

        // Weekly schedule
        const sBody = document.getElementById('teacherSessionsTableBody');
        sBody.innerHTML = '';
        if (data.sessions && data.sessions.length > 0) {
          data.sessions.forEach(s => {
            const tr = document.createElement('tr');
            const loc = [s.campus, s.building, s.room].filter(Boolean).join(' • ');
            tr.innerHTML = `
              <td><strong>${s.day_name_he || ''}</strong></td>
              <td>${s.start_time} - ${s.end_time}</td>
              <td>${s.course_code} - ${s.course_name}</td>
              <td>${s.session_type || 'שיעור'}</td>
              <td>${loc ? `<span class="clickable-link" onclick="jumpToRoomOccupancy('${escapeJs(s.room)}', '${escapeJs(s.building)}', '${escapeJs(s.campus)}')">📍 ${loc}</span>` : 'לא נקבע מיקום'}</td>
            `;
            sBody.appendChild(tr);
          });
        } else {
          sBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">אין שיעורים שבועיים מקושרים.</td></tr>';
        }
      } catch (e) {
        console.error(e);
      }
    }

    // PERSONAL TIMETABLE
    function isCourseInSchedule(id) {
      return myScheduleCourses.includes(id);
    }

    function toggleCourseSchedule(id, btnElement) {
      const idx = myScheduleCourses.indexOf(id);
      if (idx > -1) {
        myScheduleCourses.splice(idx, 1);
      } else {
        myScheduleCourses.push(id);
      }
      localStorage.setItem('my_huji_schedule', JSON.stringify(myScheduleCourses));
      updateSavedCount();
      if (btnElement) {
        const inNow = isCourseInSchedule(id);
        btnElement.textContent = inNow ? '✓ במערכת' : '+ הוסף למערכת';
        btnElement.className = `btn ${inNow ? 'btn-secondary' : 'btn-gold'} btn-sm`;
      }
      renderMySchedule();
    }

    function clearMySchedule() {
      if (confirm('האם אתה בטוח שברצונך לרוקן את כל הקורסים ממערכת השעות שלך?')) {
        myScheduleCourses = [];
        localStorage.setItem('my_huji_schedule', JSON.stringify([]));
        updateSavedCount();
        renderMySchedule();
        performSearch();
      }
    }

    function updateSavedCount() {
      document.getElementById('savedCount').textContent = myScheduleCourses.length;
    }

    async function renderMySchedule() {
      document.querySelectorAll('#myTimetableGrid .tt-event').forEach(el => el.remove());
      const pillsContainer = document.getElementById('selectedPills');
      pillsContainer.innerHTML = '';

      if (myScheduleCourses.length === 0) {
        pillsContainer.innerHTML = '<span style="color: var(--text-muted); font-size: 0.9rem;">לא הוספת עדיין קורסים. ניתן להוסיף קורסים מהקטלוג באמצעות כפתור "+ הוסף למערכת".</span>';
        return;
      }

      for (let i = 0; i < myScheduleCourses.length; i++) {
        const cid = myScheduleCourses[i];
        const color = EVENT_COLORS[i % EVENT_COLORS.length];

        try {
          const res = await fetch(`/api/course/${cid}`);
          const c = await res.json();

          // Pill
          const pill = document.createElement('span');
          pill.style.cssText = `background: ${color.bg}; color: ${color.text}; border: 1px solid ${color.border}; padding: 4px 10px; border-radius: 20px; font-size: 0.82rem; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;`;
          pill.innerHTML = `<span>${c.code} - ${c.name_he}</span> <span style="cursor: pointer;" onclick="toggleCourseSchedule(${c.id})">✖</span>`;
          pillsContainer.appendChild(pill);

          // Place sessions on grid
          (c.groups || []).forEach(g => {
            (g.sessions || []).forEach(s => {
              if (s.day_of_week === null || !s.start_time || !s.end_time) return;
              const [startH, startM] = s.start_time.split(':').map(Number);
              const [endH, endM] = s.end_time.split(':').map(Number);
              if (startH < 8 || startH > 20) return;

              const cell = document.getElementById(`myTimetableGrid-cell-${s.day_of_week}-${startH}`);
              if (!cell) return;

              const durationHours = (endH + endM/60) - (startH + startM/60);
              const topOffset = (startM / 60) * 60;
              const heightPx = Math.max(25, durationHours * 60 - 4);

              const ev = document.createElement('div');
              ev.className = 'tt-event';
              ev.style.cssText = `
                top: ${topOffset}px;
                height: ${heightPx}px;
                background: ${color.bg};
                border-right: 4px solid ${color.border};
                color: ${color.text};
              `;
              ev.onclick = () => openCourseModal(c.id);

              const loc = [s.building_name_he, s.room_name_he].filter(Boolean).join(' ') || '';
              ev.innerHTML = `
                <div class="tt-event-title">${c.code} - ${c.name_he}</div>
                <div class="tt-event-subtitle">${g.session_type_name_he || 'שיעור'} | ${s.start_time}-${s.end_time} ${loc ? '📍 ' + loc : ''}</div>
              `;
              cell.appendChild(ev);
            });
          });
        } catch (e) {
          console.error(e);
        }
      }
    }

    function escapeJs(str) {
      if (!str) return '';
      return String(str).replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }
  </script>
</body>
</html>
"""

class ShnatonHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            html_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
            if os.path.exists(html_file):
                with open(html_file, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
            else:
                content = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        elif path == "/api/faculties":
            self.handle_faculties()
            return

        elif path == "/api/departments":
            fac = query.get("faculty", [""])[0].strip()
            self.handle_departments(fac or None)
            return

        elif path == "/api/search":
            self.handle_search(query)
            return

        elif path.startswith("/api/course/"):
            cid_str = path.split("/")[-1]
            try:
                cid = int(cid_str)
                self.handle_course_detail(cid)
            except ValueError:
                self.handle_course_detail(cid_str)
            return

        elif path == "/api/exams":
            q = query.get("q", [""])[0].strip()
            faculty = query.get("faculty", [""])[0].strip()
            semester = query.get("semester", [""])[0].strip()
            moed_str = query.get("moed", [""])[0].strip()
            moed = int(moed_str) if moed_str.isdigit() else None
            from_date = query.get("from", [""])[0].strip()
            to_date = query.get("to", [""])[0].strip()
            has_date = query.get("has_date", ["0"])[0].strip() == "1"
            limit_str = query.get("limit", ["200"])[0].strip()
            limit = int(limit_str) if limit_str.isdigit() else 200
            self.handle_exams(q or None, faculty or None, semester or None, moed, from_date or None, to_date or None, has_date, limit)
            return

        elif path == "/api/rooms":
            self.handle_rooms()
            return

        elif path == "/api/room/schedule":
            room = query.get("room", [""])[0].strip()
            building = query.get("building", [""])[0].strip()
            campus = query.get("campus", [""])[0].strip()
            semester = query.get("semester", [""])[0].strip()
            self.handle_room_schedule(room, building or None, campus or None, semester or None)
            return

        elif path == "/api/map/buildings":
            campus = query.get("campus", [""])[0].strip()
            self.handle_map_buildings(campus or None)
            return

        elif path == "/api/autocomplete":
            q = query.get("q", [""])[0].strip()
            self.handle_autocomplete(q)
            return

        elif path == "/api/stats":
            self.handle_stats()
            return

        elif path == "/api/teachers":
            q = query.get("q", [""])[0].strip()
            self.handle_teachers(q or None)
            return

        elif path == "/api/teacher/detail":
            name = query.get("name", [""])[0].strip()
            if not name:
                self.send_error(400, "Missing teacher name")
                return
            self.handle_teacher_detail(name)
            return

        elif path == "/api/roadmaps":
            q = query.get("q", [""])[0].strip()
            degree = query.get("degree", [""])[0].strip()
            scope = query.get("scope", [""])[0].strip()
            faculty = query.get("faculty", [""])[0].strip()
            dept = query.get("department", [""])[0].strip()
            self.handle_roadmaps(q or None, degree or None, scope or None, faculty or None, dept or None)
            return

        elif path == "/api/roadmap/curriculum":
            code = query.get("code", [""])[0].strip()
            if not code:
                self.send_error(400, "Missing Roadmap Code")
                return
            self.handle_roadmap_curriculum(code)
            return

        self.send_error(404, "Not Found")

    def handle_faculties(self):
        conn = database.get_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT code, name_he, name_en FROM faculties WHERE name_he IS NOT NULL ORDER BY name_he")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        self.send_json(rows)

    def handle_departments(self, faculty_code: Optional[str] = None):
        rows = database.get_departments(faculty_code, DB_PATH)
        self.send_json(rows)

    def handle_search(self, query):
        q = query.get("q", [""])[0].strip()
        faculty = query.get("faculty", [""])[0].strip()
        dept = query.get("dept", [""])[0].strip()
        year = query.get("year", [""])[0].strip()
        sem = query.get("semester", [""])[0].strip()

        conn = database.get_connection(DB_PATH)
        cur = conn.cursor()

        conditions = ["c.is_learning = 1"]
        params = []

        if q:
            kw = f"%{q}%"
            conditions.append("""(
                c.code LIKE ? OR
                c.name_he LIKE ? OR
                c.name_en LIKE ? OR
                c.description LIKE ? OR
                EXISTS (
                    SELECT 1 FROM session_teachers st
                    JOIN sessions s ON st.session_id = s.id
                    WHERE s.course_id = c.id AND (st.name_he LIKE ? OR st.name_en LIKE ?)
                )
            )""")
            params.extend([kw, kw, kw, kw, kw, kw])

        if faculty:
            conditions.append("c.faculty_code = ?")
            params.append(faculty)

        if dept:
            conditions.append("""(
                c.department_id = ? OR
                EXISTS (SELECT 1 FROM course_roadmaps cr WHERE cr.course_id = c.id AND cr.department_id = ?)
            )""")
            params.extend([dept, dept])

        if year:
            y_kw = f"%{year}%"
            conditions.append("""(
                c.study_years LIKE ? OR
                EXISTS (SELECT 1 FROM course_roadmaps cr WHERE cr.course_id = c.id AND cr.study_years LIKE ?)
            )""")
            params.extend([y_kw, y_kw])

        if sem:
            sem_int = int(sem)
            conditions.append("(c.semester = ? OR c.semester_name_he LIKE ?)")
            params.extend([sem_int, f"%{sem_int}%"])

        where = " WHERE " + " AND ".join(conditions)

        cur.execute(f"SELECT COUNT(*) FROM courses c {where}", params)
        total = cur.fetchone()[0]

        sql = f"""
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
            {where}
            ORDER BY c.code ASC
            LIMIT 150
        """
        cur.execute(sql, params)
        raw_courses = [dict(r) for r in cur.fetchall()]
        conn.close()

        courses = []
        for r in raw_courses:
            t_str = r.pop("teacher_names", "") or ""
            r["teachers"] = [t.strip() for t in t_str.split(",") if t.strip()][:3]
            courses.append(r)

        self.send_json({"total": total, "courses": courses})

    def handle_course_detail(self, course_id_or_code: Any):
        conn = database.get_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM courses WHERE id = ? OR code = ?", (course_id_or_code, str(course_id_or_code)))
        course_row = cur.fetchone()
        if not course_row:
            conn.close()
            self.send_error(404, "Course Not Found")
            return

        course = dict(course_row)
        course_id = course["id"]

        # Groups & sessions
        cur.execute("SELECT * FROM groups WHERE course_id = ? ORDER BY group_code", (course_id,))
        groups = [dict(g) for g in cur.fetchall()]
        for g in groups:
            cur.execute("""
                SELECT s.* FROM sessions s
                WHERE s.group_id = ?
                ORDER BY s.day_of_week, s.start_time
            """, (g['id'],))
            sessions = [dict(s) for s in cur.fetchall()]
            for s in sessions:
                cur.execute("""
                    SELECT name_he, name_en, email, title_he FROM session_teachers
                    WHERE session_id = ?
                """, (s['id'],))
                s['teachers'] = [dict(t) for t in cur.fetchall()]
            g['sessions'] = sessions
        course['groups'] = groups

        # Roadmaps
        cur.execute("""
            SELECT roadmap_code, roadmap_name_he, roadmap_name_en,
                   department_name_he, degree_name_he, scope_name_he, study_years
            FROM course_roadmaps
            WHERE course_id = ?
            ORDER BY department_name_he, degree_name_he, roadmap_name_he
        """, (course_id,))
        course['roadmaps'] = [dict(r) for r in cur.fetchall()]

        # Exams
        cur.execute("""
            SELECT * FROM exams 
            WHERE course_id = ? 
            ORDER BY 
                CASE WHEN start_time IS NOT NULL THEN 0 ELSE 1 END,
                moed ASC, 
                start_time ASC
        """, (course_id,))
        exams = [dict(e) for e in cur.fetchall()]

        if not exams:
            # On-demand live fetch from Shnaton API (Year 2027)
            try:
                req = urllib.request.Request(
                    f"https://shnaton.huji.ac.il/api/assignments?year=2027&courseId={course_id}",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    assign_data = json.loads(resp.read().decode("utf-8"))
                    if assign_data:
                        database.save_exams(course_id, assign_data, DB_PATH)
                        cur.execute("""
                            SELECT * FROM exams 
                            WHERE course_id = ? 
                            ORDER BY 
                                CASE WHEN start_time IS NOT NULL THEN 0 ELSE 1 END,
                                moed ASC, 
                                start_time ASC
                        """, (course_id,))
                        exams = [dict(e) for e in cur.fetchall()]
            except Exception:
                pass

        course['exams'] = exams

        conn.close()
        self.send_json(course)

    def handle_exams(self, q=None, faculty=None, semester=None, moed=None, from_date=None, to_date=None, has_date=False, limit=200):
        exams = database.get_exams_list(
            q=q,
            faculty=faculty,
            semester=semester,
            moed=moed,
            from_date=from_date,
            to_date=to_date,
            has_date_only=has_date,
            limit=limit,
            db_path=DB_PATH
        )
        self.send_json(exams)

    def handle_roadmaps(self, q: Optional[str] = None, degree: Optional[str] = None, scope: Optional[str] = None, faculty: Optional[str] = None, dept: Optional[str] = None):
        roadmaps = database.get_roadmaps_list(q=q, degree=degree, scope=scope, faculty=faculty, department=dept, db_path=DB_PATH)
        self.send_json(roadmaps)

    def handle_roadmap_curriculum(self, code: str):
        # 1. Check SQLite cache
        cached = database.get_roadmap_curriculum(code, DB_PATH)
        # Use cache only if it has the updated rich fields
        if cached and cached.get("years") and len(cached["years"]) > 0:
            first_cat = cached["years"][0].get("categories", [{}])[0]
            if "category_type" in first_cat and "obligation_text" in first_cat:
                self.send_json(cached)
                return

        # 2. Fetch live from Shnaton API
        url = f"https://shnaton.huji.ac.il/api/yearly-roadmaps/{code}/thresholds?activeYear=2027&thresholdYear=2027&include=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print("API fetch failed for roadmap:", code, type(e), e)
            # Fallback to courses mapped to roadmap in database
            conn = database.get_connection(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT c.id, c.code, c.name_he, c.name_en, c.academic_points,
                       c.semester_name_he, cr.study_years, cr.roadmap_name_he
                FROM course_roadmaps cr
                JOIN courses c ON c.id = cr.course_id
                WHERE cr.roadmap_code = ?
                ORDER BY cr.study_years, c.code
            """, (code,))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

            years_map: Dict[int, List[Dict[str, Any]]] = {}
            for r in rows:
                y_str = str(r.get("study_years") or "1")
                first_y = int(y_str.split(",")[0]) if y_str.split(",")[0].isdigit() else 1
                if first_y not in years_map:
                    years_map[first_y] = []
                sem_str = r.get("semester_name_he") or ""
                sem_type, sem_badge = self._parse_semester_type(sem_str)
                r["semester_type"] = sem_type
                r["semester_badge"] = sem_badge
                years_map[first_y].append(r)

            years_list = []
            for y_num in sorted(years_map.keys()):
                label = f"שנה {['א׳', 'ב׳', 'ג׳', 'ד׳', 'ה׳', 'ו׳'][min(y_num - 1, 5)]}"
                total_pts = sum(c.get("academic_points", 0) or 0 for c in years_map[y_num])
                years_list.append({
                    "year_number": y_num,
                    "year_label": label,
                    "mandatory_points": total_pts,
                    "required_elective_min_points": 0,
                    "elective_min_points": 0,
                    "year_required_min_points": total_pts,
                    "categories": [
                        {
                            "subchapter": "קורסי התוכנית",
                            "category_type": "mandatory",
                            "category_label": "חובה",
                            "is_mandatory": True,
                            "min_points": total_pts,
                            "max_points": total_pts,
                            "obligation_text": f"חובה ללמוד את כל הקורסים ({total_pts} נ\"ז סה\"כ)",
                            "note": "",
                            "courses": years_map[y_num]
                        }
                    ]
                })

            fallback_data = {
                "code": code,
                "title_he": rows[0]["roadmap_name_he"] if rows else code,
                "title_en": "",
                "years": years_list,
                "total_courses": len(rows),
                "is_fallback": True
            }
            self.send_json(fallback_data)
            return

        # 3. Process Shnaton API raw_data into structured years and categories
        roadmap_info = raw_data.get("roadmap", {}) or {}
        title_he = (roadmap_info.get("name") or {}).get("he") if isinstance(roadmap_info.get("name"), dict) else str(raw_data.get("roadmapCode", code))
        title_en = (roadmap_info.get("name") or {}).get("en") if isinstance(roadmap_info.get("name"), dict) else ""
        scope_name = (raw_data.get("scopeName") or {}).get("he") if isinstance(raw_data.get("scopeName"), dict) else ""
        degree_name = (raw_data.get("diplomaDegreeTypeName") or {}).get("he") if isinstance(raw_data.get("diplomaDegreeTypeName"), dict) else ""
        dept_name = (raw_data.get("departmentName") or {}).get("he") if isinstance(raw_data.get("departmentName"), dict) else ""
        fac_name = (raw_data.get("facultyName") or {}).get("he") if isinstance(raw_data.get("facultyName"), dict) else ""

        thresholds = raw_data.get("thresholds", [])
        
        years_dict: Dict[int, List[Dict[str, Any]]] = {}
        total_courses_count = 0

        for t in thresholds:
            raw_courses = t.get("courses", [])
            min_naz = t.get("minNaz", 0) or 0
            max_naz = t.get("maxNaz")

            # Skip empty placeholders
            if len(raw_courses) == 0 and min_naz == 0:
                continue

            y = t.get("displayAcademicYear")
            if not y and t.get("fromToAcademicYear"):
                valid_yrs = [yr for yr in t.get("fromToAcademicYear", []) if yr and yr > 0]
                y = valid_yrs[0] if valid_yrs else 1
            y = int(y or 1)

            if y not in years_dict:
                years_dict[y] = []

            sub_he = (t.get("subChapter") or {}).get("he") if isinstance(t.get("subChapter"), dict) else (t.get("subChapter") or "כללי")
            is_mand_flag = bool(t.get("isMandatory"))
            
            # 3-tier Classification
            cat_type, cat_label = self._classify_curriculum_category(sub_he, is_mand_flag, min_naz)
            
            # Clear obligation explanation
            if cat_type == "mandatory":
                courses_sum = sum(c.get("academicPoints", 0) or 0 for c in raw_courses)
                pts_label = min_naz if min_naz > 0 else courses_sum
                obligation_text = f"חובה ללמוד את כל הקורסים ({pts_label} נ\"ז סה\"כ)"
            elif cat_type == "required_elective":
                if max_naz and max_naz > min_naz:
                    obligation_text = f"חובה לבחור בין {min_naz} ל-{max_naz} נ\"ז מתוך רשימה זו"
                elif min_naz > 0:
                    obligation_text = f"חובה לבחור לפחות {min_naz} נ\"ז מתוך רשימה זו"
                else:
                    obligation_text = "קורסי חובת בחירה"
            elif cat_type == "elective":
                if min_naz > 0:
                    obligation_text = f"יש לצבור לפחות {min_naz} נ\"ז מתוך הרשימה"
                elif max_naz:
                    obligation_text = f"ניתן ללמוד עד {max_naz} נ\"ז מתוך הרשימה"
                else:
                    obligation_text = "קורסי בחירה חופשית"
            elif cat_type == "cornerstone":
                obligation_text = f"תוכנית אבני פינה{' (מינימום ' + str(min_naz) + ' נ\"ז)' if min_naz > 0 else ''}"
            elif cat_type == "workshop":
                obligation_text = "סדנאות עזר וליווי אקדמי (רשות, ללא עלות נ\"ז)"
            else:
                obligation_text = f"דרישת מינימום: {min_naz} נ\"ז" if min_naz > 0 else "קורסים נוספים והעשרה"

            note = (t.get("hebrewNote") or "").strip()
            
            parsed_courses = []
            for c in raw_courses:
                c_name = (c.get("name") or {}).get("he") if isinstance(c.get("name"), dict) else str(c.get("name", ""))
                c_name_en = (c.get("name") or {}).get("en") if isinstance(c.get("name"), dict) else ""
                period_name = (c.get("coursePeriodName") or {}).get("he") if isinstance(c.get("coursePeriodName"), dict) else ""
                sem_type, sem_badge = self._parse_semester_type(period_name)
                pts = c.get("academicPoints") or 0
                parsed_courses.append({
                    "id": c.get("id"),
                    "code": c.get("code"),
                    "name_he": c_name,
                    "name_en": c_name_en,
                    "academic_points": pts,
                    "semester_name_he": period_name,
                    "semester_type": sem_type,
                    "semester_badge": sem_badge,
                    "course_structure": c.get("courseStructureType", "")
                })
                total_courses_count += 1

            years_dict[y].append({
                "subchapter": sub_he,
                "category_type": cat_type,
                "category_label": cat_label,
                "is_mandatory": cat_type == "mandatory",
                "min_points": min_naz,
                "max_points": max_naz,
                "obligation_text": obligation_text,
                "note": note,
                "order": t.get("subChapterOrder", 0) or 0,
                "courses": parsed_courses
            })

        category_order = {
            "mandatory": 0,
            "required_elective": 1,
            "elective": 2,
            "cornerstone": 3,
            "enrichment": 4,
            "workshop": 5,
            "other": 6
        }

        structured_years = []
        for y_num in sorted(years_dict.keys()):
            categories = years_dict[y_num]
            categories.sort(key=lambda cat: (category_order.get(cat["category_type"], 9), cat["order"]))
            
            mand_pts = sum(cat["min_points"] if cat["min_points"] > 0 else sum(c["academic_points"] for c in cat["courses"]) 
                           for cat in categories if cat["category_type"] == "mandatory")
            req_elec_pts = sum(cat["min_points"] for cat in categories if cat["category_type"] == "required_elective")
            elec_pts = sum(cat["min_points"] for cat in categories if cat["category_type"] == "elective")
            total_req = mand_pts + req_elec_pts + elec_pts
            
            label = f"שנה {['א׳', 'ב׳', 'ג׳', 'ד׳', 'ה׳', 'ו׳'][min(y_num - 1, 5)]}"
            structured_years.append({
                "year_number": y_num,
                "year_label": label,
                "mandatory_points": mand_pts,
                "required_elective_min_points": req_elec_pts,
                "elective_min_points": elec_pts,
                "year_required_min_points": total_req,
                "categories": categories
            })

        curriculum_result = {
            "code": code,
            "title_he": title_he,
            "title_en": title_en,
            "department_name_he": dept_name,
            "faculty_name_he": fac_name,
            "degree_name_he": degree_name,
            "scope_name_he": scope_name,
            "total_courses": total_courses_count,
            "years": structured_years
        }

        # Cache in SQLite
        database.save_roadmap_curriculum(code, title_he, title_en, curriculum_result, DB_PATH)
        self.send_json(curriculum_result)

    def _classify_curriculum_category(self, sub_he: str, is_mand_flag: bool, min_naz: float) -> tuple:
        sub = (sub_he or "").strip()
        if sub == "חובה" or (is_mand_flag and "בחירה" not in sub):
            return "mandatory", "חובה"
        elif "חובת בחירה" in sub or (min_naz > 0 and not is_mand_flag and "בחירה" in sub and "מרחיבי" not in sub and "נוספים" not in sub):
            return "required_elective", "חובת בחירה"
        elif "אבני פינה" in sub:
            return "cornerstone", "אבני פינה"
        elif "סדנא" in sub:
            return "workshop", "סדנת עזר"
        elif "מרחיב" in sub or "העשרה" in sub:
            return "enrichment", "הרחבת דעת"
        else:
            return "elective", "בחירה"

    def _parse_semester_type(self, sem_str: str) -> tuple:
        s = (sem_str or "").strip()
        if "או ב" in s:
            return "sem_either", "🔀 סמסטר א׳ או ב׳"
        elif "סמסטר א" in s:
            return "sem_a", "☀️ סמסטר א׳"
        elif "סמסטר ב" in s:
            return "sem_b", "🌱 סמסטר ב׳"
        elif "שנתי" in s:
            return "sem_year", "🔄 שנתי"
        elif "קיץ" in s:
            return "sem_summer", "🏖️ סמסטר קיץ"
        else:
            return "sem_other", s or "לא נקבע"

    def handle_rooms(self):
        rooms = database.get_all_rooms(DB_PATH)
        self.send_json(rooms)

    def handle_room_schedule(self, room: str, building: Optional[str], campus: Optional[str], semester: Optional[str] = None):
        schedule = database.get_room_weekly_schedule(room, building, campus, semester, DB_PATH)
        self.send_json(schedule)

    def handle_map_buildings(self, campus: Optional[str] = None):
        buildings = database.get_campus_buildings(campus, DB_PATH)
        self.send_json(buildings)

    def handle_teachers(self, q: Optional[str] = None):
        teachers = database.get_all_teachers(q, DB_PATH)
        self.send_json(teachers)

    def handle_teacher_detail(self, name: str):
        detail = database.get_teacher_courses_and_schedule(name, DB_PATH)
        clean_name = detail.get("clean_name", name)
        conn = database.get_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT email, title_he FROM session_teachers 
            WHERE name_he = ? OR name_en = ? OR name_he = ? OR name_en = ?
            ORDER BY CASE WHEN email IS NOT NULL AND email != '' THEN 0 ELSE 1 END
            LIMIT 1
        """, (name, name, clean_name, clean_name))
        row = cur.fetchone()
        if row:
            detail["email"] = row["email"]
            detail["title"] = row["title_he"]
        conn.close()
        self.send_json(detail)

    def handle_autocomplete(self, q: str):
        """Return up to 12 course/teacher suggestions for live search dropdown."""
        if not q or len(q) < 2:
            self.send_json([])
            return
        conn = database.get_connection(DB_PATH)
        cur = conn.cursor()
        results = []
        kw = f"%{q}%"
        # Course matches by name or code
        cur.execute("""
            SELECT id, code, name_he, faculty_name_he, academic_points, semester_name_he
            FROM courses
            WHERE is_learning = 1
              AND (name_he LIKE ? OR code LIKE ? OR name_en LIKE ?)
            ORDER BY
              CASE WHEN code LIKE ? THEN 0
                   WHEN name_he LIKE ? THEN 1
                   ELSE 2 END,
              code
            LIMIT 10
        """, (kw, kw, kw, f"{q}%", f"{q}%"))
        for r in cur.fetchall():
            results.append({
                "type": "course",
                "id": r["id"],
                "code": r["code"],
                "name": r["name_he"] or "",
                "faculty": r["faculty_name_he"] or "",
                "points": r["academic_points"],
                "semester": r["semester_name_he"] or "",
            })
        # Teacher matches
        cur.execute("""
            SELECT DISTINCT COALESCE(name_he, name_en) AS name,
                   COUNT(DISTINCT session_id) AS cnt
            FROM session_teachers
            WHERE (name_he LIKE ? OR name_en LIKE ?)
            GROUP BY COALESCE(name_he, name_en)
            ORDER BY cnt DESC
            LIMIT 5
        """, (kw, kw))
        for r in cur.fetchall():
            results.append({
                "type": "teacher",
                "name": r["name"] or "",
                "sessions": r["cnt"],
            })
        conn.close()
        self.send_json(results[:12])

    def handle_stats(self):
        """Return live statistics for the dashboard hero section."""
        conn = database.get_connection(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM courses WHERE is_learning = 1")
        courses_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM faculties WHERE name_he IS NOT NULL")
        faculties_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT COALESCE(name_he, name_en)) FROM session_teachers")
        teachers_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT room_name_he) FROM sessions WHERE room_name_he IS NOT NULL")
        rooms_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM course_roadmaps")
        roadmaps_count = cur.fetchone()[0]
        cur.execute("""
            SELECT faculty_name_he, COUNT(*) as c
            FROM courses WHERE is_learning=1 AND faculty_name_he IS NOT NULL
            GROUP BY faculty_name_he ORDER BY c DESC LIMIT 8
        """)
        top_faculties = [{"name": r["faculty_name_he"], "count": r["c"]} for r in cur.fetchall()]
        conn.close()
        self.send_json({
            "courses": courses_count,
            "faculties": faculties_count,
            "teachers": teachers_count,
            "rooms": rooms_count,
            "roadmaps": roadmaps_count,
            "top_faculties": top_faculties,
        })

    def send_json(self, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def run_web_gui(host: str = HOST, port: int = PORT, open_browser: bool = None):
    if open_browser is None:
        # In cloud environments (Render, Cloud Run, Docker etc.), do not try to open desktop browser
        open_browser = not bool(os.environ.get("PORT") or os.environ.get("K_SERVICE") or os.environ.get("RENDER"))
    server = HTTPServer((host, port), ShnatonHandler)
    url = f"http://localhost:{port}/" if host in ("0.0.0.0", "127.0.0.1") else f"http://{host}:{port}/"
    print("=" * 65)
    print(f"  ממשק משתמש מתקדם שנתון האוניברסיטה העברית פועל בכתובת:")
    print(f"  {url} (מאזין ב-{host}:{port})")
    print("=" * 65)
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nהשרת נעצר.")

if __name__ == "__main__":
    run_web_gui()
