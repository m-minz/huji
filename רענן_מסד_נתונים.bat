@echo off
chcp 65001 > nul
title רענון מאגר נתונים - שנתון האוניברסיטה העברית
cls
echo ======================================================================
echo           רענון מאגר שנתון האוניברסיטה העברית - HUJI Shnaton
echo ======================================================================
echo.
echo  בחר פעולת רענון:
echo.
echo   [1] רענון מהיר של לוח הבחינות (מועדי א', ב', שעות וכיתות - כ-2 דקות)
echo   [2] רענון מלא של כל הקטלוג והסילבוסים (ייקח כ-15-20 דקות)
echo   [3] דחיסה ועדכון קבצי האתר בלבד (ללא משיכת נתונים חדשים מהאוניברסיטה)
echo   [4] יציאה
echo.
set /p choice="הכנס מספר בחירה (1-4): "

if "%choice%"=="1" (
    echo.
    echo [*] מפעיל רענון מועדי בחינות...
    python refresh_and_build.py --mode exams
    pause
    exit /b
)

if "%choice%"=="2" (
    echo.
    echo [*] מפעיל סריקה מלאה של שנתון האוניברסיטה העברית...
    python refresh_and_build.py --mode full
    pause
    exit /b
)

if "%choice%"=="3" (
    echo.
    echo [*] דוחס ומעדכן גרסה מקומית...
    python refresh_and_build.py --mode compress-only
    pause
    exit /b
)

echo להתראות!
