from dotenv import load_dotenv
load_dotenv()
"""
GSP — Generational Story Preserver
Flask application entry point.
"""
import os
import json
import uuid
import wave
import struct
import traceback
from pathlib import Path
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_file, jsonify, g
)
from db import init_app, get_db
import ai_engine

# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gsp-dev-secret-change-in-prod")
app.config["DATABASE_PATH"] = str(BASE_DIR / "instance" / "gsp.db")
app.config["UPLOAD_FOLDER"] = str(BASE_DIR / "static" / "uploads")
app.config["PDF_FOLDER"]    = str(BASE_DIR / "static" / "pdf")

# Ensure dirs exist
for d in [app.config["UPLOAD_FOLDER"] + "/photos",
          app.config["UPLOAD_FOLDER"] + "/audio",
          app.config["PDF_FOLDER"]]:
    Path(d).mkdir(parents=True, exist_ok=True)

init_app(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user(user_id):
    db = get_db()
    return db.execute("SELECT * FROM user WHERE id=?", (user_id,)).fetchone()

def _get_story(user_id):
    db = get_db()
    return db.execute("SELECT * FROM story WHERE user_id=?", (user_id,)).fetchone()

def _get_photos(user_id):
    db = get_db()
    return db.execute("SELECT * FROM photo WHERE user_id=? ORDER BY created_at", (user_id,)).fetchall()

def _story_or_404(user_id):
    user  = _get_user(user_id)
    story = _get_story(user_id)
    if not user:
        flash("Story not found.", "error")
        return None, None
    return user, story

def _progress(story):
    """Return completion % (0-100) for nav progress bar."""
    if not story:
        return 0
    fields = ["childhood","education","career","family_notes","wisdom_corrected"]
    filled = sum(1 for f in fields if story[f] and str(story[f]).strip())
    return int(filled / len(fields) * 100)

def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)

# ---------------------------------------------------------------------------
# Routes — Home
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("home.html")


# ---------------------------------------------------------------------------
# Routes — Create Story
# ---------------------------------------------------------------------------

@app.route("/create-story", methods=["GET","POST"])
def create_story():
    if request.method == "POST":
        name        = request.form.get("name","").strip()
        birth_year  = request.form.get("birth_year","").strip()
        birth_place = request.form.get("birth_place","").strip()
        gender      = request.form.get("gender","").strip()
        occupation  = request.form.get("occupation","").strip()

        if not name:
            flash("Please enter a name.", "error")
            return render_template("create_story.html")

        db = get_db()
        cur = db.execute(
            "INSERT INTO user (name, birth_year, birth_place, gender, occupation) VALUES (?,?,?,?,?)",
            (name, birth_year or None, birth_place or None, gender or None, occupation or None)
        )
        user_id = cur.lastrowid
        db.execute(
            "INSERT INTO story (user_id, story_title) VALUES (?,?)",
            (user_id, f"The Life of {name}")
        )
        db.commit()
        return redirect(url_for("childhood", user_id=user_id))

    return render_template("create_story.html")


# ---------------------------------------------------------------------------
# Chapter routes — Childhood, Education, Career, Family, Wisdom
# ---------------------------------------------------------------------------

def _chapter_view(user_id, template, field, title):
    user, story = _story_or_404(user_id)
    if not user:
        return redirect(url_for("home"))
    return render_template(template, user=_row_to_dict(user),
                           story=_row_to_dict(story),
                           progress=_progress(story),
                           chapter_title=title)

def _chapter_save(user_id, field, next_route, extra_fields=None):
    _, story = _story_or_404(user_id)
    if not story:
        return redirect(url_for("home"))
    db = get_db()
    # Discover which columns actually exist (handles DB created before migrations)
    existing_cols = {row[1] for row in db.execute("PRAGMA table_info(story)").fetchall()}
    value = request.form.get(field,"").strip()
    sets  = {field: value}
    if extra_fields:
        for ef in extra_fields:
            if ef in existing_cols:
                sets[ef] = request.form.get(ef,"").strip() or None
    cols = ", ".join(f"{k}=?" for k in sets)
    vals = list(sets.values()) + [user_id]
    db.execute(f"UPDATE story SET {cols}, updated_at=CURRENT_TIMESTAMP WHERE user_id=?", vals)
    db.commit()
    flash("Saved!", "success")
    return redirect(url_for(next_route, user_id=user_id))


@app.route("/story/<int:user_id>/childhood", methods=["GET","POST"])
def childhood(user_id):
    if request.method == "POST":
        return _chapter_save(user_id, "childhood", "education",
            extra_fields=["q_friend","q_game","q_festival","q_nickname"])
    return _chapter_view(user_id, "childhood.html", "childhood", "Childhood")

@app.route("/story/<int:user_id>/education", methods=["GET","POST"])
def education(user_id):
    if request.method == "POST":
        return _chapter_save(user_id, "education", "career",
            extra_fields=["q_school","q_teacher","q_subject","q_achievement"])
    return _chapter_view(user_id, "education.html", "education", "Education")

@app.route("/story/<int:user_id>/career", methods=["GET","POST"])
def career(user_id):
    if request.method == "POST":
        return _chapter_save(user_id, "career", "family",
            extra_fields=["q_firstjob","q_career_achievement","q_advice"])
    return _chapter_view(user_id, "career.html", "career", "Career")

@app.route("/story/<int:user_id>/family", methods=["GET","POST"])
def family(user_id):
    if request.method == "POST":
        extra = ["father_name","mother_name","spouse_name","children","siblings"]
        return _chapter_save(user_id, "family_notes", "wisdom", extra_fields=extra)
    return _chapter_view(user_id, "family.html", "family_notes", "Family")

@app.route("/story/<int:user_id>/wisdom", methods=["GET","POST"])
def wisdom(user_id):
    if request.method == "POST":
        return _chapter_save(user_id, "wisdom_corrected", "biography",
            extra_fields=["life_lesson","q_future_advice","q_learned_late"])
    return _chapter_view(user_id, "wisdom.html", "wisdom_corrected", "Wisdom")


# ---------------------------------------------------------------------------
# AI Generation routes
# ---------------------------------------------------------------------------

@app.route("/story/<int:user_id>/biography")
def biography(user_id):
    user, story = _story_or_404(user_id)
    if not user:
        return redirect(url_for("home"))
    ud = _row_to_dict(user)
    sd = _row_to_dict(story)

    # Generate if missing
    if not sd or not sd.get("biography"):
        bio = ai_engine.generate_biography(ud, sd or {})
        db = get_db()
        db.execute("UPDATE story SET biography=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                   (bio, user_id))
        db.commit()
        sd = _row_to_dict(_get_story(user_id))

    return render_template("biography.html", user=ud, story=sd,
                           progress=_progress(_get_story(user_id)))


@app.route("/story/<int:user_id>/biography/regenerate", methods=["POST"])
def biography_regenerate(user_id):
    user, story = _story_or_404(user_id)
    if not user:
        return redirect(url_for("home"))
    bio = ai_engine.generate_biography(_row_to_dict(user), _row_to_dict(story) or {})
    db = get_db()
    db.execute("UPDATE story SET biography=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
               (bio, user_id))
    db.commit()
    return redirect(url_for("biography", user_id=user_id))


@app.route("/story/<int:user_id>/timeline")
def timeline(user_id):
    user, story = _story_or_404(user_id)
    if not user:
        return redirect(url_for("home"))
    ud = _row_to_dict(user)
    sd = _row_to_dict(story)

    if not sd or not sd.get("timeline_json"):
        tl = ai_engine.generate_timeline(ud, sd or {})
        db = get_db()
        db.execute("UPDATE story SET timeline_json=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                   (json.dumps(tl), user_id))
        db.commit()
        sd = _row_to_dict(_get_story(user_id))

    events = []
    try:
        events = json.loads(sd.get("timeline_json") or "[]")
    except Exception:
        pass

    return render_template("timeline.html", user=ud, story=sd, events=events,
                           progress=_progress(_get_story(user_id)))


@app.route("/story/<int:user_id>/wisdom-analysis", methods=["POST"])
def wisdom_analysis(user_id):
    """AJAX endpoint: run AI wisdom analysis, return JSON."""
    user, story = _story_or_404(user_id)
    if not user:
        return jsonify(error="Not found"), 404
    raw = (request.json or {}).get("text") or (story["wisdom_corrected"] if story else "")
    result = ai_engine.analyze_wisdom(_row_to_dict(user), raw)
    db = get_db()
    db.execute("""UPDATE story SET
        wisdom_corrected=?, wisdom_emotions=?, life_lesson=?, wisdom_summary=?,
        updated_at=CURRENT_TIMESTAMP WHERE user_id=?""",
        (result.get("corrected_story"), json.dumps(result.get("emotions",[])),
         result.get("life_lesson"), result.get("wisdom_summary"), user_id))
    db.commit()
    return jsonify(result)


@app.route("/story/<int:user_id>/family-tree")
def family_tree(user_id):
    user, story = _story_or_404(user_id)
    if not user:
        return redirect(url_for("home"))
    return render_template("family_tree.html", user=_row_to_dict(user),
                           story=_row_to_dict(story),
                           progress=_progress(story))


# ---------------------------------------------------------------------------
# Photo upload
# ---------------------------------------------------------------------------

@app.route("/story/<int:user_id>/upload-photo", methods=["POST"])
def upload_photo(user_id):
    file    = request.files.get("photo")
    caption = request.form.get("caption","")
    category= request.form.get("category","general")
    if not file or not file.filename:
        return jsonify(error="No file"), 400
    ext  = Path(file.filename).suffix.lower()
    name = f"{uuid.uuid4().hex}{ext}"
    rel  = f"uploads/photos/{name}"
    file.save(str(BASE_DIR / "static" / rel))
    db = get_db()
    db.execute("INSERT INTO photo (user_id, image_path, category, caption) VALUES (?,?,?,?)",
               (user_id, rel, category, caption))
    db.commit()
    return jsonify(ok=True, path=rel)


# ---------------------------------------------------------------------------
# Audio upload
# ---------------------------------------------------------------------------

@app.route("/story/<int:user_id>/upload-audio", methods=["POST"])
def upload_audio(user_id):
    file       = request.files.get("audio")
    transcript = request.form.get("transcript","")
    category   = request.form.get("category","general")
    if not file:
        return jsonify(error="No file"), 400
    name = f"{uuid.uuid4().hex}.webm"
    rel  = f"uploads/audio/{name}"
    file.save(str(BASE_DIR / "static" / rel))
    db = get_db()
    db.execute("INSERT INTO audio (user_id, audio_path, category, transcript) VALUES (?,?,?,?)",
               (user_id, rel, category, transcript))
    db.commit()
    return jsonify(ok=True, transcript=transcript)



# ---------------------------------------------------------------------------
# AI Legacy — single combined generation page
# ---------------------------------------------------------------------------

@app.route("/story/<int:user_id>/ai-legacy")
def ai_legacy(user_id):
    user, story = _story_or_404(user_id)
    if not user:
        return redirect(url_for("home"))
    ud = _row_to_dict(user)
    sd = _row_to_dict(story) or {}
    return render_template("ai_legacy.html", user=ud, story=sd,
                           progress=_progress(_get_story(user_id)))


@app.route("/story/<int:user_id>/ai-legacy/generate", methods=["POST"])
def ai_legacy_generate(user_id):
    """Generate biography + timeline + wisdom in one call, return JSON."""
    user, story = _story_or_404(user_id)
    if not user:
        return jsonify(error="Not found"), 404
    ud = _row_to_dict(user)
    sd = _row_to_dict(story) or {}

    # Build one combined prompt for Gemini
    combined_prompt = f"""You are a professional biographer and life coach.
Analyze the following life stories for {ud.get('name','this person')} and generate a complete legacy profile.

== CHILDHOOD ==
{sd.get('childhood','Not provided')}

== EDUCATION ==
{sd.get('education','Not provided')}

== CAREER ==
{sd.get('career','Not provided')}

== FAMILY ==
{sd.get('family_notes','Not provided')}

== WISDOM / LIFE EXPERIENCE ==
{sd.get('wisdom_corrected','Not provided')}

Generate and return a JSON object with exactly these keys:
{{
  "biography": "A flowing 4-6 paragraph biography in third person",
  "timeline": [
    {{"year": "2001", "title": "Event Title", "detail": "Brief detail", "icon": "🎓"}},
    ...
  ],
  "life_lessons": ["Lesson one", "Lesson two", "Lesson three"],
  "values": ["Value1", "Value2", "Value3", "Value4"],
  "emotions": [
    {{"emoji": "❤️", "label": "Love"}},
    {{"emoji": "😊", "label": "Joy"}},
    ...
  ],
  "legacy_summary": "A 2-3 sentence legacy summary for future generations"
}}
Return ONLY the JSON object, no markdown, no explanation."""

    result = {}

    # Try Gemini first
    try:
        import os, requests as req
        key = os.environ.get("GEMINI_API_KEY","")
        model = os.environ.get("GEMINI_MODEL","gemini-2.0-flash")
        if key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            payload = {"contents":[{"parts":[{"text": combined_prompt}]}],
                       "generationConfig":{"temperature":0.7,"maxOutputTokens":2000}}
            resp = req.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            result = json.loads(text)
    except Exception as e:
        app.logger.warning(f"Gemini AI Legacy failed: {e}")

    # Offline fallback
    if not result:
        bio = ai_engine.generate_biography(ud, sd)
        tl  = ai_engine.generate_timeline(ud, sd)
        ws  = ai_engine.analyze_wisdom(ud, sd.get("wisdom_corrected",""))
        result = {
            "biography": bio,
            "timeline": [{"year": str(e.get("year","")), "title": e.get("title",""),
                           "detail": e.get("detail",""), "icon": e.get("icon","📌")}
                         for e in tl],
            "life_lessons": [ws.get("life_lesson","Be kind and grateful"),
                             "Family is the foundation of everything.",
                             "Experience is the greatest teacher."],
            "values": ["Family","Courage","Gratitude","Kindness"],
            "emotions": [{"emoji":"❤️","label":"Love"},{"emoji":"😊","label":"Joy"},
                         {"emoji":"🙏","label":"Gratitude"},{"emoji":"🌄","label":"Wonder"}],
            "legacy_summary": ws.get("wisdom_summary","A life lived with purpose, love, and wisdom.")
        }

    # Persist biography + timeline back to DB
    db = get_db()
    db.execute("UPDATE story SET biography=?, timeline_json=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
               (result.get("biography"), json.dumps(result.get("timeline",[])), user_id))
    db.commit()

    return jsonify(result)

# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

@app.route("/story/<int:user_id>/export-pdf")
def export_pdf(user_id):
    user, story = _story_or_404(user_id)
    if not user:
        return redirect(url_for("home"))
    ud = _row_to_dict(user)
    sd = _row_to_dict(story) or {}

    # Ensure biography & timeline exist
    if not sd.get("biography"):
        sd["biography"] = ai_engine.generate_biography(ud, sd)
    if not sd.get("timeline_json"):
        tl = ai_engine.generate_timeline(ud, sd)
        sd["timeline_json"] = json.dumps(tl)

    photos_raw = _get_photos(user_id)
    photos = [_row_to_dict(p) for p in photos_raw]

    name_slug = "".join(c for c in ud.get("name","story") if c.isalnum() or c in "-_")[:40]
    fname = f"legacy-book-{name_slug}.pdf"
    out   = str(BASE_DIR / "static" / "pdf" / fname)

    from pdf_generator import build_legacy_book
    build_legacy_book(ud, sd, photos, out)
    return send_file(out, as_attachment=True, download_name=fname, mimetype="application/pdf")


# ---------------------------------------------------------------------------
# Demo Story — seed K.H. Eklavya data
# ---------------------------------------------------------------------------

DEMO_USER = {
    "name": "K.H. Eklavya",
    "birth_year": "1967",
    "birth_place": "Odisha",
    "gender": "Male",
    "occupation": "Travel Creator",
}
DEMO_STORY = {
    "story_title": "The Life of K.H. Eklavya",
    "childhood": (
        "I was born in a small village in Odisha. My childhood was full of adventures "
        "in the fields and rivers near our home. I remember playing gilli-danda with "
        "my friends every evening and helping my mother in the kitchen garden. My best "
        "friend Raju and I would explore the nearby forest looking for mangoes. Every "
        "monsoon we built small boats of leaves and floated them down the lanes."
    ),
    "education": (
        "I joined the village primary school in 1971. My favourite teacher was "
        "Mr. Patnaik who taught mathematics and always encouraged me to dream big. "
        "I completed my schooling in 1997 and went on to study Mechanical Engineering, "
        "graduating in 1997 with first-class honours. I was always fascinated by ships "
        "and the vast, open sea."
    ),
    "career": (
        "After completing my engineering degree in 1997, I joined the Merchant Navy. "
        "I travelled to many countries including Singapore, Dubai, and Rotterdam. The "
        "journey was exciting but I became homesick after a year at sea. In 2008 I "
        "returned home and struggled to find a job for several months. In 2009 I got "
        "a new role in International Business. By 2011 I had built a solid career and "
        "in 2013 I became a full-time Travel Creator, sharing stories of my journeys "
        "with the world."
    ),
    "father_name": "Ramesh Eklavya",
    "mother_name": "Sunita Eklavya",
    "spouse_name": "Priya Eklavya",
    "children": "Aarav, Ananya",
    "siblings": "Rohit Eklavya",
    "family_notes": (
        "Our family has always valued togetherness. Every festival, no matter where I "
        "was in the world, I made sure to call home. My parents taught me that roots "
        "matter more than wings."
    ),
    "wisdom_corrected": (
        "I had an argument with my parents about how to celebrate their anniversary. "
        "I wanted to plan something simple, but they wanted a big celebration. To "
        "convince them, I took them on a trek to Harishchandragad instead. There, we "
        "witnessed something rare and beautiful: a Brocken Spectre — our shadows ringed "
        "by a halo of light on the clouds below. Watching their faces light up with "
        "wonder, I realised that memories shared together are far more valuable than "
        "expensive celebrations."
    ),
    "life_lesson": "Beautiful memories shared with loved ones outlast any expensive celebration.",
    "wisdom_emotions": json.dumps(["Wonder", "Love", "Reflection", "Gratitude"]),
    "wisdom_summary": (
        "The experience became a lesson Eklavya carries everywhere: that the richest "
        "gifts we can offer those we love are not things but moments — witnessed "
        "together, remembered always."
    ),
}


def _make_demo_photo():
    """Generate a simple placeholder photo with PIL so demo mode works offline."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img  = Image.new("RGB", (400, 300), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 380, 280], outline=(212, 175, 55), width=2)
        draw.text((200, 140), "GSP", fill=(212, 175, 55), anchor="mm")
        draw.text((200, 170), "Demo Photo", fill=(248, 250, 252), anchor="mm")
        fname = "demo_placeholder.jpg"
        path  = BASE_DIR / "static" / "uploads" / "photos" / fname
        img.save(str(path), "JPEG")
        return f"uploads/photos/{fname}"
    except Exception:
        return None


@app.route("/demo-story")
def demo_story():
    db = get_db()
    # Check if demo user already exists
    existing = db.execute("SELECT id FROM user WHERE is_demo=1 LIMIT 1").fetchone()
    if existing:
        return redirect(url_for("biography", user_id=existing["id"]))

    # Create demo user
    cur = db.execute(
        "INSERT INTO user (name, birth_year, birth_place, gender, occupation, is_demo) VALUES (?,?,?,?,?,1)",
        (DEMO_USER["name"], DEMO_USER["birth_year"], DEMO_USER["birth_place"],
         DEMO_USER["gender"], DEMO_USER["occupation"])
    )
    uid = cur.lastrowid

    # Generate biography & timeline via AI engine (offline fallback always works)
    ud  = dict(DEMO_USER, id=uid)
    sd  = dict(DEMO_STORY)
    bio = ai_engine.generate_biography(ud, sd)
    tl  = json.dumps(ai_engine.generate_timeline(ud, sd))

    db.execute("""INSERT INTO story
        (user_id, story_title, childhood, education, career,
         father_name, mother_name, spouse_name, children, siblings, family_notes,
         wisdom_corrected, life_lesson, wisdom_emotions, wisdom_summary,
         biography, timeline_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (uid, sd["story_title"], sd["childhood"], sd["education"], sd["career"],
         sd["father_name"], sd["mother_name"], sd["spouse_name"],
         sd["children"], sd["siblings"], sd["family_notes"],
         sd["wisdom_corrected"], sd["life_lesson"], sd["wisdom_emotions"],
         sd["wisdom_summary"], bio, tl))

    # Add a demo photo if PIL is available
    photo_path = _make_demo_photo()
    if photo_path:
        db.execute("INSERT INTO photo (user_id, image_path, category, caption) VALUES (?,?,?,?)",
                   (uid, photo_path, "general", "A memory from the journey"))

    db.commit()
    flash("Demo story loaded for K.H. Eklavya!", "success")
    return redirect(url_for("biography", user_id=uid))


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5056)
