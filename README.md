# 🏛️ שנתון האוניברסיטה העברית | HUJI Shnaton & Smart Schedule Hub

מערכת ווב מודרנית ואינטואיטיבית לקטלוג הקורסים, מערכות השעות, תפוסת הכיתות, לוח הבחינות ותוכניות הלימודים של האוניברסיטה העברית בירושלים.

---

## ✨ תכונות עיקריות
- 🔍 **קטלוג קורסים וסילבוסים**: חיפוש חופשי והשלמה אוטומטית (Autocomplete), סינון לפי פקולטות, שנת לימוד וסמסטרים.
- 🏫 **תפוסת כיתות ואולמות**: לוח שבועי גרפי (08:00–20:00) לכל כיתה ואולם בכל הקמפוסים, כולל זיהוי שעות פנויות.
- 👤 **מרכז מרצים**: צפייה בכל הקורסים ושעות ההוראה השבועיות של כל מרצה בלחיצה אחת.
- 📝 **לוח בחינות ומטלות ארצי**: 15,825 מועדי בחינות (מועד א׳, ב׳, ג׳, מטלות, אולמות), ייצוא ליומן Google בלחיצה אחת, וייצוא ל-CSV/iCal.
- 🎓 **תוכניות לימוד ומסלולים**: עץ קורסים אקדמי מלא לפי שנים (שנה א׳ עד ד׳) בחלוקה לקורסי חובה ובחירה.
- 🗓️ **המערכת שלי**: בניית מערכת שעות אישית עם זיהוי התנגשויות אוטומטי (Conflicts Detection).
- 🗺️ **מפת קמפוס אינטראקטיבית**: התמקדות בבניינים והגעה ישירה לכיתות שבהם.
- ⚡ **0 תלויות חיצוניות (Zero pip dependencies)**: פועל על ספריית הליבה של Python בלבד.
- 💾 **בסיס נתונים מוטמע (SQLite)**: ביצועי מיקרו-שניות ללא צורך בשרת מסד נתונים נפרד.

---

## 🚀 מדריך העלאה ל-GitHub והרצה בענן (צעד-אחר-צעד)

תיקייה זו (`huji_cloud_deploy`) מוכנה לחלוטין לדחיפה ל-GitHub ולפריסה בענן.

### שלב 1: פתיחת מאגר ב-GitHub ודחיפת הקוד
1. פתח חשבון/התחבר אל [GitHub](https://github.com/) וצור מאגר חדש (New Repository), למשל בשם: `huji-shnaton`.
2. פתח שורת פקודה (Terminal / PowerShell) **בתוך התיקייה הזו (`huji_cloud_deploy`)**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Hebrew University Smart Shnaton Hub"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/huji-shnaton.git
   git push -u origin main
   ```

---

### אפשרות א׳: פריסה חינמית ב-Render.com (מומלץ למתחילים – 2 דקות)
1. היכנס אל [Render.com](https://render.com/) והירשם בחינם (Sign in with GitHub).
2. לחץ על **New +** ובחר **Web Service**.
3. בחר את המאגר שיצרת (`huji-shnaton`).
4. הגדר את הפרטים הבאים:
   - **Name**: `huji-shnaton`
   - **Runtime**: `Python 3`
   - **Build Command**: השאר ריק (או `echo Ready`)
   - **Start Command**: `python web_app.py`
   - **Instance Type**: `Free`
5. לחץ **Deploy Web Service** – תוך דקה האתר יעלה לאוויר בכתובת ציבורית ומאובטחת עם HTTPS:
   `https://huji-shnaton.onrender.com`

---

### אפשרות ב׳: פריסה ב-Google Cloud Run (הכי מקצועית וחסכונית)
גוגל מעניקה במסגרת ה-Free Tier **עד 2 מיליון בקשות בחודש בחינם**. כשאף אחד לא גולש, השרת נרדם (0$ עלות) ומתעורר מיד בכניסת משתמש.
1. התקן את ה-Google Cloud CLI והתחבר לחשבונך:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
2. הרץ מתוך התיקייה פקודה אחת בלבד:
   ```bash
   gcloud run deploy huji-shnaton --source . --region europe-west1 --allow-unauthenticated
   ```
3. בסיום התהליך תקבל קישור HTTPS חי ומהיר.

---

### אפשרות ג׳: הרצה ב-Docker (מקומי או בשרת VPS)
לבנייה והרצה של ה-Container:
```bash
docker build -t huji-shnaton .
docker run -d -p 8080:8080 --name huji-app huji-shnaton
```
האפליקציה תהיה זמינה בכתובת `http://localhost:8080/`.

---

## 🛠️ הרצה מקומית ללא דוקר
פשוט הרץ:
```bash
python web_app.py
```
או לחץ לחיצה כפולה על `start.bat`.

---

## 📄 רישיון
נוצר עבור קהילת הסטודנטים והמרצים של האוניברסיטה העברית בירושלים.
