"""
ai_engine.py — every "AI does X" feature in the GSP blueprint lives here.

Design decision (documented for the examiner)
-----------------------------------------------
If a ``GEMINI_API_KEY`` is present in the environment, GSP calls the
Gemini API for richer, genuinely-generated prose. If the key is
missing, the call fails, or the response can't be parsed, GSP falls
back to a deterministic, dependency-free "offline engine" below.

This means the project **runs and demos completely offline** — no
API key, no internet — which matters a lot for a live viva where
campus wifi is not guaranteed. The offline engine is not a stub: it
does real natural-language work (sentence segmentation, regex year
extraction, keyword-weighted emotion detection, template-based prose
assembly) and produces a complete biography / timeline / wisdom
analysis on its own.
"""
from __future__ import annotations

import json
import os
import re
import textwrap

import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


# ---------------------------------------------------------------------------
# Gemini transport helper
# ---------------------------------------------------------------------------
def _call_gemini(prompt: str, *, json_mode: bool = False, timeout: int = 25):
    """Return Gemini's text reply, or None if anything goes wrong.

    Never raises — callers always have the offline fallback to lean on.
    """
    if not GEMINI_API_KEY:
        return None
    try:
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        if json_mode:
            body["generationConfig"] = {"response_mime_type": "application/json"}
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=body,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        # Network down, bad key, rate limit, unexpected schema, etc.
        # GSP degrades to the offline engine rather than breaking the page.
        return None


def is_live() -> bool:
    """True if a Gemini key is configured (used by the UI to show a badge)."""
    return bool(GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# Small text utilities shared by the offline engine
# ---------------------------------------------------------------------------
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    return parts


def _tidy_sentence(s: str) -> str:
    """Light, rule-based grammar polish — capitalisation, spacing, punctuation.

    This is intentionally modest. It will not rewrite phrasing, but it
    fixes the small mechanical slips (lowercase 'i', missing full stop,
    double spaces) that make a first draft look unedited.
    """
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return s
    s = s[0].upper() + s[1:]
    s = re.sub(r"\bi\b", "I", s)
    if s[-1] not in ".!?":
        s += "."
    return s


def polish_paragraph(text: str) -> str:
    return " ".join(_tidy_sentence(s) for s in _sentences(text))


def first_name(full_name: str) -> str:
    """Pick the most natural 'first name' token, skipping initials like
    'S.N.' so 'S.N. Sarthak' reads as 'Sarthak', not 'S.N.'."""
    full_name = (full_name or "").strip()
    if not full_name:
        return "They"
    tokens = full_name.split()
    for tok in tokens:
        if "." in tok:  # 'S.', 'S.N.', 'J.R.R.' read as initials, not a name
            continue
        if len(tok) > 1:
            return tok
    return tokens[0]


def pronoun(gender: str) -> dict:
    g = (gender or "").strip().lower()
    if g.startswith("f"):
        return {"subj": "she", "obj": "her", "poss": "her"}
    if g.startswith("m"):
        return {"subj": "he", "obj": "him", "poss": "his"}
    return {"subj": "they", "obj": "them", "poss": "their"}


# ---------------------------------------------------------------------------
# 1. Biography generation
# ---------------------------------------------------------------------------
def generate_biography(user: dict, story: dict) -> str:
    gemini_prompt = textwrap.dedent(f"""
        You are a warm, literary ghostwriter producing a short biography
        for a personal "legacy book". Write 4-6 flowing paragraphs in the
        THIRD PERSON, based only on the facts given below. Do not invent
        names, dates, or events that are not implied by the notes. Keep
        the tone tender and dignified, suitable for being read by
        grandchildren. Do not use markdown headers, just paragraphs of
        prose separated by blank lines.

        Name: {user.get('name')}
        Born: {user.get('birth_year')} in {user.get('birth_place')}
        Occupation: {user.get('occupation') or 'Not specified'}

        Childhood notes: {story.get('childhood') or 'Not provided'}
        Education notes: {story.get('education') or 'Not provided'}
        Career notes: {story.get('career') or 'Not provided'}
        Family notes: {_family_sentence(story)}
        A life-changing story in their own words: {story.get('wisdom') or 'Not provided'}
    """).strip()

    live = _call_gemini(gemini_prompt)
    if live:
        return live.strip()
    return _offline_biography(user, story)


def _family_sentence(story: dict) -> str:
    bits = []
    if story.get("father_name"):
        bits.append(f"father {story['father_name']}")
    if story.get("mother_name"):
        bits.append(f"mother {story['mother_name']}")
    if story.get("spouse_name"):
        bits.append(f"spouse {story['spouse_name']}")
    if story.get("children"):
        bits.append(f"children: {story['children']}")
    if story.get("siblings"):
        bits.append(f"siblings: {story['siblings']}")
    return "; ".join(bits) if bits else "Not provided"


def _offline_biography(user: dict, story: dict) -> str:
    name = user.get("name") or "This storyteller"
    fname = first_name(name)
    pr = pronoun(user.get("gender"))
    birth_place = user.get("birth_place") or "a place close to the heart"
    birth_year = user.get("birth_year")
    occupation = user.get("occupation")

    paragraphs = []

    opener = f"{name} was born"
    if birth_year:
        opener += f" in {birth_year}"
    opener += f" in {birth_place}."
    if occupation:
        opener += f" Today, {pr['subj']} is known as {occupation}."
    paragraphs.append(opener)

    if story.get("childhood"):
        paragraphs.append(
            f"Childhood left its mark early. {polish_paragraph(story['childhood'])}"
        )

    if story.get("education"):
        paragraphs.append(
            f"Learning shaped the years that followed. {polish_paragraph(story['education'])}"
        )

    if story.get("career"):
        paragraphs.append(
            f"In time, {fname}'s path opened into a working life of its own. "
            f"{polish_paragraph(story['career'])}"
        )

    fam = _family_sentence(story)
    if fam != "Not provided":
        paragraphs.append(
            f"Family has always been close at hand — {fam.replace(';', ',')}."
        )

    if story.get("wisdom"):
        lesson = extract_life_lesson(story["wisdom"])
        closing = f'The lesson stayed with {pr["obj"]}: "{lesson}"' if lesson else ""
        paragraphs.append(
            f"If there is one story {fname} returns to, it is this: "
            f"{polish_paragraph(story['wisdom'])} {closing}".strip()
        )

    paragraphs.append(
        f"This page is only a beginning. {fname}'s story — like any life worth "
        f"keeping — will keep being told."
    )

    return "\n\n".join(p for p in paragraphs if p.strip())


# ---------------------------------------------------------------------------
# 2. Timeline generation
# ---------------------------------------------------------------------------
_YEAR_RE = re.compile(r"\b(?:18|19|20)\d{2}\b")

_TIMELINE_ICONS = {
    "birth": "cake",
    "education": "graduation-cap",
    "career": "briefcase",
    "marriage": "heart",
    "family": "home",
    "achievement": "trophy",
}


def generate_timeline(user: dict, story: dict) -> list[dict]:
    gemini_prompt = textwrap.dedent(f"""
        Build a chronological life timeline from these notes. Respond with
        ONLY a JSON array (no markdown, no commentary), where each item is:
        {{"year": "YYYY or approximate phrase", "title": "3-6 word title",
        "category": "birth|education|career|marriage|family|achievement",
        "detail": "one short sentence"}}
        Order the array chronologically. Include 4 to 9 events. Use only
        facts implied by the notes.

        Birth year: {user.get('birth_year')}
        Childhood notes: {story.get('childhood') or ''}
        Education notes: {story.get('education') or ''}
        Career notes: {story.get('career') or ''}
        Family notes: {_family_sentence(story)}
    """).strip()

    live = _call_gemini(gemini_prompt, json_mode=True)
    if live:
        try:
            cleaned = live.strip().strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            events = json.loads(cleaned)
            if isinstance(events, list) and events:
                for e in events:
                    e.setdefault("category", "achievement")
                    e["icon"] = _TIMELINE_ICONS.get(e["category"], "star")
                return events
        except Exception:
            pass  # fall through to offline engine

    return _offline_timeline(user, story)


def _offline_timeline(user: dict, story: dict) -> list[dict]:
    events = []

    if user.get("birth_year"):
        events.append({
            "year": str(user["birth_year"]),
            "title": "Born",
            "category": "birth",
            "icon": _TIMELINE_ICONS["birth"],
            "detail": f"Born in {user.get('birth_place') or 'their hometown'}.",
        })

    def harvest(text, category, fallback_title):
        if not text:
            return
        for sentence in _sentences(text):
            year_match = _YEAR_RE.search(sentence)
            if year_match:
                year = year_match.group(0)
                title = sentence.strip().rstrip(".")
                if len(title) > 48:
                    title = title[:45].rsplit(" ", 1)[0] + "…"
                events.append({
                    "year": year,
                    "title": title or fallback_title,
                    "category": category,
                    "icon": _TIMELINE_ICONS.get(category, "star"),
                    "detail": _tidy_sentence(sentence),
                })

    harvest(story.get("education"), "education", "A milestone in education")
    harvest(story.get("career"), "career", "A milestone in career")

    if story.get("spouse_name"):
        # No explicit year given for marriage — place it without one.
        events.append({
            "year": "—",
            "title": f"Married {story['spouse_name']}",
            "category": "marriage",
            "icon": _TIMELINE_ICONS["marriage"],
            "detail": f"Began a life together with {story['spouse_name']}.",
        })

    if story.get("children"):
        events.append({
            "year": "—",
            "title": "Became a parent",
            "category": "family",
            "icon": _TIMELINE_ICONS["family"],
            "detail": f"Welcomed: {story['children']}.",
        })

    if not events:
        events.append({
            "year": "—",
            "title": "The story begins",
            "category": "achievement",
            "icon": "star",
            "detail": "Add more detail to childhood, education or career to build a timeline.",
        })

    def sort_key(e):
        try:
            return int(e["year"])
        except (ValueError, TypeError):
            return 9999  # undated events sink to the end, but stay present

    events.sort(key=sort_key)
    return events


# ---------------------------------------------------------------------------
# 3. Wisdom-page analysis: corrected story, emotions, life lesson, summary
# ---------------------------------------------------------------------------
_EMOTION_KEYWORDS = {
    "Love": ["love", "loved", "cherish", "dear", "affection", "beloved"],
    "Wonder": ["wonder", "amazed", "astonish", "magical", "incredible", "spectre", "awe"],
    "Happiness": ["happy", "happiness", "joy", "delight", "smile", "laughed"],
    "Gratitude": ["grateful", "gratitude", "thankful", "blessed", "appreciate"],
    "Reflection": ["realised", "realized", "learned", "understood", "reflect", "thought"],
    "Anger": ["anger", "angry", "argument", "furious", "frustrat", "fight"],
    "Sadness": ["sad", "cried", "loss", "lost", "grief", "miss", "homesick"],
    "Courage": ["brave", "courage", "fear", "overcame", "struggled", "challenge"],
    "Nostalgia": ["remember", "memory", "memories", "childhood", "old days", "back then"],
    "Pride": ["proud", "pride", "achievement", "accomplished"],
}


def detect_emotions(text: str, limit: int = 4) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    scored = []
    for emotion, words in _EMOTION_KEYWORDS.items():
        score = sum(lowered.count(w) for w in words)
        if score:
            scored.append((score, emotion))
    scored.sort(reverse=True)
    result = [e for _, e in scored[:limit]]
    return result or ["Reflection"]


def extract_life_lesson(text: str) -> str:
    """Heuristic: people very often state the lesson in their final
    sentence ("...I realised that ..."). We look for that pattern first,
    then fall back to the last sentence, then a generic line."""
    sentences = _sentences(text)
    if not sentences:
        return "Every memory we keep becomes a small inheritance for those who come after us."

    realization_markers = ["realised", "realized", "learned", "understood", "taught me"]
    for s in reversed(sentences):
        if any(m in s.lower() for m in realization_markers):
            return _tidy_sentence(s)

    return _tidy_sentence(sentences[-1])


def build_wisdom_summary(name: str, lesson: str) -> str:
    fname = first_name(name)
    lesson_clean = lesson.rstrip(".").strip()
    return (
        f'The experience became a lesson for {fname}: "{lesson_clean}." '
        f"It is a memory {fname} now carries forward, and one worth "
        f"passing on to the next generation."
    )


def analyze_wisdom(user: dict, raw_text: str) -> dict:
    """Returns dict: corrected_story, emotions (list), life_lesson, wisdom_summary."""
    gemini_prompt = textwrap.dedent(f"""
        A person wrote the following true story about a moment that
        changed their life. Respond with ONLY JSON, no markdown:
        {{"corrected_story": "the story, lightly polished for grammar and
        flow, same meaning, same first-person voice, not rewritten in a
        flowery way", "emotions": ["2 to 4 single-word emotions present in
        the story"], "life_lesson": "one sentence stating the lesson
        learned, third person, starting with the person's first name",
        "wisdom_summary": "two sentences paraphrasing the lesson for a
        family legacy book"}}

        Person's first name: {first_name(user.get('name', ''))}
        Story: {raw_text}
    """).strip()

    live = _call_gemini(gemini_prompt, json_mode=True)
    if live:
        try:
            cleaned = live.strip().strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            data = json.loads(cleaned)
            if all(k in data for k in ("corrected_story", "emotions", "life_lesson", "wisdom_summary")):
                return data
        except Exception:
            pass

    lesson = extract_life_lesson(raw_text)
    return {
        "corrected_story": polish_paragraph(raw_text),
        "emotions": detect_emotions(raw_text),
        "life_lesson": lesson,
        "wisdom_summary": build_wisdom_summary(user.get("name", ""), lesson),
    }
