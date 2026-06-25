# GSP — Generational Story Preserver

A Flask web application that helps families preserve life stories — childhood memories, education, career, family history, and hard-earned wisdom — and export them as a beautifully designed **Legacy Book PDF**.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set environment variables
cp .env.example .env
# Edit .env and add GEMINI_API_KEY if you have one

# 3. Run
python app.py
# Open http://localhost:5050
```

---

## Features

| Feature | Details |
|---|---|
| **5-chapter story entry** | Childhood, Education, Career, Family, Wisdom |
| **Voice input** | Browser Web Speech API — speak directly into text fields (Chrome/Edge) |
| **AI Biography** | Gemini API or built-in offline engine — always works without internet |
| **AI Timeline** | Automatically extracts years from your story text |
| **AI Wisdom Analysis** | Detects emotions, extracts life lesson, writes wisdom summary |
| **Family Tree** | Visual tree: parents → subject → children, plus siblings |
| **Photo upload** | Drag-and-drop photos, included in the Legacy Book |
| **Legacy Book PDF** | Premium print-ready PDF: navy/gold cover, chapters, timeline, family tree, photos |
| **Demo Mode** | Pre-loaded story for S.N. Sarthak — great for demos and vivas |

---

## AI Setup

### With Gemini API (recommended for best quality)

```bash
export GEMINI_API_KEY=your_api_key_here
```

Get a free API key at [Google AI Studio](https://aistudio.google.com).

### Without an API key (offline mode)

The app works fully offline. The built-in engine:
- Assembles biographies from your story sections
- Extracts years via regex for the timeline
- Uses keyword scoring to detect emotions
- Always produces a valid Legacy Book PDF

No fallback message shown to the user — it's seamless.

---

## PDF Font Notes

The Legacy Book uses **Lora** (literary serif, instanced from the Google Fonts variable font at build time) for headings and **Poppins** for body text — both bundled in `static/fonts/`.

To upgrade to Playfair Display (the design-spec font):

1. Download `PlayfairDisplay-Regular.ttf`, `PlayfairDisplay-Bold.ttf`, `PlayfairDisplay-SemiBold.ttf`, `PlayfairDisplay-Italic.ttf` from Google Fonts.
2. Drop them into `static/fonts/`.
3. `pdf_generator.py` auto-detects them at startup — no code change needed.

---

## Voice Input Notes

Voice input uses the browser's built-in **Web Speech API** — no server-side ML required, no Whisper dependency. This means:

- Works instantly with zero setup
- Requires Chrome, Edge, or Safari (not Firefox)
- Requires microphone permission
- Language defaults to `en-IN` (Indian English)

---

## Project Structure

```
gsp/
├── app.py              Flask application + routes
├── db.py               SQLite data-access layer (raw sqlite3, no ORM)
├── ai_engine.py        AI: Gemini REST API + offline fallback engine
├── pdf_generator.py    ReportLab Legacy Book PDF generator
├── schema.sql          Database schema
├── requirements.txt
├── .env.example
├── static/
│   ├── css/style.css   Premium navy/gold theme
│   ├── js/main.js      Voice input + UI utilities
│   └── fonts/          Bundled Lora + Poppins TTF files
└── templates/
    ├── base.html        Navbar, flash messages, progress bar
    ├── home.html
    ├── create_story.html
    ├── childhood.html   } 5 chapter entry pages
    ├── education.html   }
    ├── career.html      }
    ├── family.html      }
    ├── wisdom.html      }
    ├── biography.html   AI biography + photo upload
    ├── timeline.html    Life timeline
    └── family_tree.html Visual family tree
```

---

## Design Choices

| Choice | Reason |
|---|---|
| Raw `sqlite3` (no SQLAlchemy) | Simpler for a student project; easier to explain at a viva |
| Web Speech API for voice | Zero ML dependencies; works offline after page load |
| Offline AI fallback | Ensures demo works without WiFi or API key |
| Lora font in PDF | Instanced from bundled variable font; no download needed |
| ReportLab Platypus | Mature, dependency-free PDF generation |

---

## License

MIT — free to use, modify, and distribute.
