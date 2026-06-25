"""
pdf_generator.py — builds the "Legacy Book" PDF (Export Legacy Book button).

Visual language mirrors the web app: a navy-and-gold cover and chapter
dividers (the "premium memory theme"), opening onto warm, paper-toned
content pages so long passages of biography are actually comfortable
to read and to print. Headings use Lora (a literary serif bundled in
static/fonts as an offline-safe stand-in for Playfair Display — see
README "Typography" section); body text uses Poppins, exactly as
specified in the design brief.
"""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, PageBreak,
    Paragraph, Spacer, Table, TableStyle, HRFlowable, Image, Flowable,
    KeepTogether,
)

BASE_DIR = Path(__file__).parent
FONT_DIR = BASE_DIR / "static" / "fonts"

# ---------------------------------------------------------------------------
# Palette — same hex values as static/css/style.css
# ---------------------------------------------------------------------------
NAVY = colors.HexColor("#0F172A")
NAVY_CARD = colors.HexColor("#1E293B")
GOLD = colors.HexColor("#D4AF37")
GOLD_SOFT = colors.HexColor("#E7CD7A")
IVORY = colors.HexColor("#F8FAFC")
PAPER = colors.HexColor("#FBF8F2")
PAPER_SHADE = colors.HexColor("#F0E9D8")
INK = colors.HexColor("#241F14")
INK_SOFT = colors.HexColor("#56503F")


# ---------------------------------------------------------------------------
# Fonts — register the static instances generated under static/fonts.
# Falls back to Helvetica/Times if a file is ever missing, so a broken
# font asset can never crash a PDF export.
# ---------------------------------------------------------------------------
def _register_fonts():
    mapping = {
        "Lora": "Lora-Regular.ttf",
        "Lora-Bold": "Lora-Bold.ttf",
        "Lora-SemiBold": "Lora-SemiBold.ttf",
        "Lora-Italic": "Lora-Italic.ttf",
        "Poppins": "Poppins-Regular.ttf",
        "Poppins-Medium": "Poppins-Medium.ttf",
        "Poppins-Bold": "Poppins-Bold.ttf",
        "Poppins-Italic": "Poppins-Italic.ttf",
    }
    # A user can drop real PlayfairDisplay-*.ttf files into static/fonts
    # and the book will pick them up automatically (a graceful upgrade
    # path back to the exact brief typography).
    playfair = {
        "Lora": "PlayfairDisplay-Regular.ttf",
        "Lora-Bold": "PlayfairDisplay-Bold.ttf",
        "Lora-SemiBold": "PlayfairDisplay-SemiBold.ttf",
        "Lora-Italic": "PlayfairDisplay-Italic.ttf",
    }
    for alias, fname in playfair.items():
        candidate = FONT_DIR / fname
        if candidate.exists():
            mapping[alias] = fname

    registered = set(pdfmetrics.getRegisteredFontNames())
    for alias, fname in mapping.items():
        if alias in registered:
            continue
        path = FONT_DIR / fname
        if path.exists():
            pdfmetrics.registerFont(TTFont(alias, str(path)))

    pdfmetrics.registerFontFamily(
        "Lora", normal="Lora", bold="Lora-Bold",
        italic="Lora-Italic", boldItalic="Lora-Bold",
    )
    pdfmetrics.registerFontFamily(
        "Poppins", normal="Poppins", bold="Poppins-Bold",
        italic="Poppins-Italic", boldItalic="Poppins-Bold",
    )


_register_fonts()


def _font(name, fallback):
    return name if name in pdfmetrics.getRegisteredFontNames() else fallback


F_HEAD = _font("Lora", "Times-Roman")
F_HEAD_BOLD = _font("Lora-Bold", "Times-Bold")
F_HEAD_SEMI = _font("Lora-SemiBold", F_HEAD_BOLD)
F_HEAD_ITALIC = _font("Lora-Italic", "Times-Italic")
F_BODY = _font("Poppins", "Helvetica")
F_BODY_MED = _font("Poppins-Medium", F_BODY)
F_BODY_BOLD = _font("Poppins-Bold", "Helvetica-Bold")
F_BODY_ITALIC = _font("Poppins-Italic", "Helvetica-Oblique")


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
def _styles():
    s = {}
    s["CoverTitle"] = ParagraphStyle(
        "CoverTitle", fontName=F_HEAD_BOLD, fontSize=34, leading=40,
        textColor=GOLD, alignment=TA_CENTER, spaceAfter=6,
    )
    s["CoverSubtitle"] = ParagraphStyle(
        "CoverSubtitle", fontName=F_BODY, fontSize=13, leading=18,
        textColor=IVORY, alignment=TA_CENTER, spaceAfter=2,
    )
    s["DividerEyebrow"] = ParagraphStyle(
        "DividerEyebrow", fontName=F_BODY_MED, fontSize=11, leading=14,
        textColor=GOLD_SOFT, alignment=TA_CENTER, spaceAfter=10,
        tracking=2,
    )
    s["DividerTitle"] = ParagraphStyle(
        "DividerTitle", fontName=F_HEAD_BOLD, fontSize=28, leading=34,
        textColor=IVORY, alignment=TA_CENTER,
    )
    s["DividerNote"] = ParagraphStyle(
        "DividerNote", fontName=F_HEAD_ITALIC, fontSize=12.5, leading=18,
        textColor=GOLD_SOFT, alignment=TA_CENTER, spaceBefore=14,
    )
    s["SectionHeading"] = ParagraphStyle(
        "SectionHeading", fontName=F_HEAD_BOLD, fontSize=20, leading=24,
        textColor=NAVY, spaceAfter=4,
    )
    s["SectionKicker"] = ParagraphStyle(
        "SectionKicker", fontName=F_BODY_MED, fontSize=9.5, leading=12,
        textColor=GOLD, alignment=TA_LEFT, spaceAfter=2,
    )
    s["Body"] = ParagraphStyle(
        "Body", fontName=F_BODY, fontSize=10.6, leading=17,
        textColor=INK, alignment=TA_JUSTIFY, spaceAfter=10,
    )
    s["BodyFirst"] = ParagraphStyle(
        "BodyFirst", parent=s["Body"],
    )
    s["DropCapLetter"] = ParagraphStyle(
        "DropCapLetter", fontName=F_HEAD_BOLD, fontSize=46, leading=42,
        textColor=GOLD, alignment=TA_CENTER,
    )
    s["Quote"] = ParagraphStyle(
        "Quote", fontName=F_HEAD_ITALIC, fontSize=12, leading=19,
        textColor=INK, alignment=TA_LEFT,
    )
    s["Caption"] = ParagraphStyle(
        "Caption", fontName=F_BODY_ITALIC, fontSize=8.5, leading=11,
        textColor=INK_SOFT, alignment=TA_CENTER,
    )
    s["Label"] = ParagraphStyle(
        "Label", fontName=F_BODY_MED, fontSize=9.5, leading=13,
        textColor=NAVY,
    )
    s["Value"] = ParagraphStyle(
        "Value", fontName=F_BODY, fontSize=10, leading=14,
        textColor=INK,
    )
    s["TimelineYear"] = ParagraphStyle(
        "TimelineYear", fontName=F_HEAD_BOLD, fontSize=13, leading=16,
        textColor=colors.HexColor("#B8860B"),
    )
    s["TimelineTitle"] = ParagraphStyle(
        "TimelineTitle", fontName=F_HEAD_SEMI, fontSize=12, leading=15,
        textColor=NAVY,
    )
    s["TimelineDetail"] = ParagraphStyle(
        "TimelineDetail", fontName=F_BODY, fontSize=9.5, leading=13.5,
        textColor=INK_SOFT,
    )
    s["TreeName"] = ParagraphStyle(
        "TreeName", fontName=F_BODY_MED, fontSize=9.5, leading=12,
        textColor=NAVY, alignment=TA_CENTER,
    )
    s["TreeRole"] = ParagraphStyle(
        "TreeRole", fontName=F_BODY_ITALIC, fontSize=7.5, leading=10,
        textColor=INK_SOFT, alignment=TA_CENTER,
    )
    s["FooterRunning"] = ParagraphStyle(
        "FooterRunning", fontName=F_BODY, fontSize=8, leading=10,
        textColor=INK_SOFT,
    )
    return s


STY = _styles()


# ---------------------------------------------------------------------------
# Small decorative helpers drawn straight on the canvas
# ---------------------------------------------------------------------------
def _gold_vine(c, x, y, length=120, flip=False):
    """The book's signature flourish: a simple growing vine with three
    leaves, echoing the family-tree / generations motif everywhere else
    in the product (timeline thread, family tree roots, this flourish)."""
    c.saveState()
    c.translate(x, y)
    if flip:
        c.scale(-1, 1)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.1)
    c.bezier(0, 0, length * 0.3, 14, length * 0.7, -10, length, 6)
    leaf_positions = [length * 0.22, length * 0.52, length * 0.8]
    for lx in leaf_positions:
        c.setFillColor(GOLD)
        c.saveState()
        c.translate(lx, 4)
        c.rotate(28)
        c.ellipse(-4, -2, 4, 2, stroke=0, fill=1)
        c.restoreState()
    c.restoreState()


def _fit_title_font(c, text, max_width, start_size=34, min_size=18):
    size = start_size
    while size > min_size and c.stringWidth(text, F_HEAD_BOLD, size) > max_width:
        size -= 1
    return size


def _seal(c, x, y, r=32, initials="G"):
    """Gold wax-seal monogram circle."""
    c.saveState()
    c.setFillColor(GOLD)
    c.circle(x, y, r, stroke=0, fill=1)
    c.setFillColor(NAVY)
    c.circle(x, y, r - 3.2, stroke=0, fill=1)
    c.setFillColor(GOLD)
    c.setFont(F_HEAD_BOLD, r * 0.62)
    c.drawCentredString(x, y - r * 0.22, initials[0])
    c.restoreState()


def _draw_cover(c, doc, user):
    w, h = A4
    _paint_navy_page(c, doc, footer=False)

    c.setFillColor(GOLD_SOFT)
    c.setFont(F_BODY_MED, 9.5)
    c.drawCentredString(w / 2, h - 3.0 * cm, "GENERATIONAL STORY PRESERVER")

    try:
        import ai_engine
        initial = ai_engine.first_name(user.get("name", ""))[:1].upper() or "G"
    except Exception:
        initial = (user.get("name") or "G")[:1].upper()
    seal_y = h - 9.0 * cm
    _seal(c, w / 2, seal_y, r=32, initials=initial)

    c.setFillColor(GOLD_SOFT)
    c.setFont(F_BODY_MED, 10.5)
    c.drawCentredString(w / 2, seal_y - 32 - 0.95 * cm, "THE LEGACY BOOK OF")

    name = user.get("name", "A Life Story")
    title_size = _fit_title_font(c, name, w - 5 * cm)
    title_y = seal_y - 32 - 0.95 * cm - title_size - 0.35 * cm
    c.setFillColor(GOLD)
    c.setFont(F_HEAD_BOLD, title_size)
    c.drawCentredString(w / 2, title_y, name)

    sub_bits = []
    if user.get("birth_year"):
        sub_bits.append(f"Born {user['birth_year']}")
    if user.get("birth_place"):
        sub_bits.append(user["birth_place"])
    if user.get("occupation"):
        sub_bits.append(user["occupation"])
    subtitle = "   ·   ".join(sub_bits)
    sub_y = title_y - 0.95 * cm
    if subtitle:
        c.setFillColor(IVORY)
        c.setFont(F_BODY, 12.5)
        c.drawCentredString(w / 2, sub_y, subtitle)

    vine_y = sub_y - 1.4 * cm
    _gold_vine(c, w / 2 - 100, vine_y, length=200)

    c.setFillColor(GOLD_SOFT)
    c.setFont(F_BODY, 8.5)
    c.drawCentredString(w / 2, 2.0 * cm, "Every life is a unique story, and every life deserves a legacy.")


# ---------------------------------------------------------------------------
# Page background painters (used as onPage callbacks per PageTemplate)
# ---------------------------------------------------------------------------
def _paint_navy_page(c: pdfcanvas.Canvas, doc, *, footer=True):
    w, h = A4
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    # hairline gold frame
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.7)
    c.rect(1.1 * cm, 1.1 * cm, w - 2.2 * cm, h - 2.2 * cm, stroke=1, fill=0)
    if footer:
        c.setFillColor(GOLD_SOFT)
        c.setFont(F_BODY, 8)
        c.drawCentredString(w / 2, 0.7 * cm, "Generational Story Preserver")
    c.restoreState()


def _paint_paper_page(c: pdfcanvas.Canvas, doc):
    w, h = A4
    c.saveState()
    c.setFillColor(PAPER)
    c.rect(0, 0, w, h, stroke=0, fill=1)
    # a faint top rule + running header
    c.setStrokeColor(PAPER_SHADE)
    c.setLineWidth(0.8)
    c.line(2 * cm, h - 1.55 * cm, w - 2 * cm, h - 1.55 * cm)
    c.setFillColor(GOLD)
    c.setFont(F_BODY_MED, 8)
    title = getattr(doc, "running_title", "Legacy Book")
    c.drawString(2 * cm, h - 1.4 * cm, title.upper())
    c.setFillColor(INK_SOFT)
    c.drawRightString(w - 2 * cm, h - 1.4 * cm, getattr(doc, "running_name", ""))
    # footer page number
    c.setStrokeColor(PAPER_SHADE)
    c.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)
    c.setFillColor(INK_SOFT)
    c.setFont(F_BODY, 8)
    c.drawCentredString(w / 2, 1.05 * cm, f"— {doc.page} —")
    c.restoreState()


# ---------------------------------------------------------------------------
# Custom Flowables
# ---------------------------------------------------------------------------
class FamilyTreeFlowable(Flowable):
    """Draws the simple two-generation family tree described in the brief:

            Father --- Mother
                  |
                 You
               /     \\
            Son     Daughter

    Box positions are computed relative to the flowable's own width, so
    it lays out correctly regardless of page margins.
    """

    def __init__(self, user_name, father, mother, spouse, children, siblings, width=460):
        super().__init__()
        self.width = width
        self.height = 235
        self.user_name = user_name or "You"
        self.father = father or "—"
        self.mother = mother or "—"
        self.spouse = spouse
        self.children = [c.strip() for c in (children or "").split(",") if c.strip()]
        self.siblings = [s.strip() for s in (siblings or "").split(",") if s.strip()]

    def wrap(self, availWidth, availHeight):
        self.width = min(self.width, availWidth)
        return self.width, self.height

    def _box(self, c, cx, cy, label, role, w=120, h=40):
        c.setFillColor(PAPER)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.1)
        c.roundRect(cx - w / 2, cy - h / 2, w, h, 6, stroke=1, fill=1)
        c.setFillColor(NAVY)
        c.setFont(F_BODY_MED, 9.5)
        c.drawCentredString(cx, cy + 4, label[:22])
        c.setFillColor(INK_SOFT)
        c.setFont(F_BODY_ITALIC, 7.5)
        c.drawCentredString(cx, cy - 9, role)

    def _link(self, c, x1, y1, x2, y2):
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.1)
        c.line(x1, y1, x2, y2)

    def draw(self):
        c = self.canv
        w = self.width
        midx = w / 2
        top = self.height - 26

        # Parents row
        father_x, mother_x = midx - 80, midx + 80
        self._box(c, father_x, top, self.father, "Father")
        self._box(c, mother_x, top, self.mother, "Mother")
        self._link(c, father_x + 60, top, mother_x - 60, top)

        # Down to "You"
        you_y = top - 70
        self._link(c, midx, top - 20, midx, you_y + 20)
        you_label = self.user_name
        if self.spouse:
            you_label = f"{self.user_name} & {self.spouse}"
        self._box(c, midx, you_y, you_label, "You" + (" & Spouse" if self.spouse else ""), w=170)

        # Siblings, branching left off the parents' line
        for i, sib in enumerate(self.siblings[:2]):
            sx = father_x - 70 - i * 95
            self._link(c, father_x - 60 if i == 0 else sx + 47, top, sx, top)
            self._box(c, sx, top, sib, "Sibling", w=90)

        # Children row
        kids = self.children[:3] or []
        if kids:
            n = len(kids)
            spread = 200
            start = midx - spread / 2
            step = spread / max(n - 1, 1) if n > 1 else 0
            kids_y = you_y - 70
            for i, kid in enumerate(kids):
                kx = midx if n == 1 else start + step * i
                self._link(c, midx, you_y - 20, kx, kids_y + 20)
                self._box(c, kx, kids_y, kid, "Child", w=110)


class TimelineDot(Flowable):
    """A small gold dot used as the left marker of one timeline row."""

    def __init__(self, size=9):
        super().__init__()
        self.width = size
        self.height = size
        self.size = size

    def draw(self):
        c = self.canv
        c.setFillColor(GOLD)
        c.circle(self.size / 2, self.size / 2, self.size / 2, stroke=0, fill=1)


# ---------------------------------------------------------------------------
# Section builders (return lists of flowables)
# ---------------------------------------------------------------------------
def _divider_page(eyebrow, title, note):
    flow = [
        Spacer(1, 8.5 * cm),
        Paragraph(eyebrow.upper(), STY["DividerEyebrow"]),
        Paragraph(title, STY["DividerTitle"]),
    ]
    if note:
        flow.append(Paragraph(note, STY["DividerNote"]))
    flow.append(NextPageTemplate("content"))
    flow.append(PageBreak())
    return flow


def _biography_section(user, story):
    flow = [
        Paragraph("CHAPTER ONE", STY["SectionKicker"]),
        Paragraph("Biography", STY["SectionHeading"]),
        HRFlowable(width="100%", thickness=0.8, color=PAPER_SHADE, spaceAfter=14),
    ]
    bio = (story.get("biography") or "").strip()
    paragraphs = [p.strip() for p in bio.split("\n") if p.strip()]
    for i, p in enumerate(paragraphs):
        if i == 0 and p:
            first_letter, rest = p[0], p[1:]
            t = Table(
                [[Paragraph(first_letter, STY["DropCapLetter"]), Paragraph(rest, STY["BodyFirst"])]],
                colWidths=[1.15 * cm, None],
            )
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            flow.append(t)
        else:
            flow.append(Paragraph(p, STY["Body"]))
    if not paragraphs:
        flow.append(Paragraph(
            "No biography has been generated yet — return to the Biography "
            "page in the app and click “Generate Biography”.", STY["Body"]))
    return flow


def _timeline_section(story):
    import json
    flow = [
        Paragraph("CHAPTER TWO", STY["SectionKicker"]),
        Paragraph("Timeline", STY["SectionHeading"]),
        HRFlowable(width="100%", thickness=0.8, color=PAPER_SHADE, spaceAfter=14),
    ]
    try:
        events = json.loads(story.get("timeline_json") or "[]")
    except Exception:
        events = []

    if not events:
        flow.append(Paragraph(
            "No timeline has been generated yet — return to the Timeline "
            "page in the app and click “Generate Timeline”.", STY["Body"]))
        return flow

    rows = []
    for e in events:
        year_block = Paragraph(str(e.get("year", "—")), STY["TimelineYear"])
        text_block = [
            Paragraph(e.get("title", ""), STY["TimelineTitle"]),
        ]
        if e.get("detail"):
            text_block.append(Paragraph(e["detail"], STY["TimelineDetail"]))
        rows.append([TimelineDot(), year_block, text_block])

    t = Table(rows, colWidths=[0.5 * cm, 2.1 * cm, None])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LINEBEFORE", (1, 0), (1, -1), 1.3, GOLD_SOFT),
    ]))
    flow.append(t)
    return flow


def _wisdom_section(user, story):
    import json
    flow = [
        Paragraph("CHAPTER THREE", STY["SectionKicker"]),
        Paragraph("Wisdom &amp; Life Lessons", STY["SectionHeading"]),
        HRFlowable(width="100%", thickness=0.8, color=PAPER_SHADE, spaceAfter=14),
    ]
    corrected = story.get("wisdom_corrected") or story.get("wisdom") or ""
    if corrected:
        quote_tbl = Table(
            [[Paragraph(f"“{corrected}”", STY["Quote"])]], colWidths=[None],
        )
        quote_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PAPER_SHADE),
            ("LINEBEFORE", (0, 0), (0, -1), 3, GOLD),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        flow.append(quote_tbl)
        flow.append(Spacer(1, 14))

    try:
        emotions = json.loads(story.get("wisdom_emotions") or "[]")
    except Exception:
        emotions = []
    if emotions:
        em_text = "   ✦   ".join(emotions)
        flow.append(Paragraph(f'<font color="#B8860B">{em_text}</font>', ParagraphStyle(
            "Emotions", fontName=F_BODY_MED, fontSize=10, leading=14,
            textColor=colors.HexColor("#B8860B"), alignment=TA_CENTER, spaceAfter=16,
        )))

    if story.get("life_lesson"):
        lesson_tbl = Table(
            [[Paragraph("LIFE LESSON", ParagraphStyle(
                "LL", fontName=F_BODY_MED, fontSize=8.5, leading=11,
                textColor=GOLD_SOFT, alignment=TA_CENTER))],
             [Paragraph(story["life_lesson"], ParagraphStyle(
                 "LLBody", fontName=F_HEAD_SEMI, fontSize=13, leading=18,
                 textColor=IVORY, alignment=TA_CENTER))]],
            colWidths=[None],
        )
        lesson_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("BOX", (0, 0), (-1, -1), 1, GOLD),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ]))
        flow.append(lesson_tbl)
        flow.append(Spacer(1, 14))

    if story.get("wisdom_summary"):
        flow.append(Paragraph("Wisdom Summary", ParagraphStyle(
            "WS", parent=STY["SectionKicker"], fontSize=10, textColor=NAVY)))
        flow.append(Paragraph(story["wisdom_summary"], STY["Body"]))

    return flow


def _family_section(user, story):
    flow = [
        Paragraph("CHAPTER FOUR", STY["SectionKicker"]),
        Paragraph("Family Tree", STY["SectionHeading"]),
        HRFlowable(width="100%", thickness=0.8, color=PAPER_SHADE, spaceAfter=18),
    ]
    tree = FamilyTreeFlowable(
        user_name=user.get("name"),
        father=story.get("father_name"),
        mother=story.get("mother_name"),
        spouse=story.get("spouse_name"),
        children=story.get("children"),
        siblings=story.get("siblings"),
    )
    flow.append(tree)
    if story.get("family_notes"):
        flow.append(Spacer(1, 10))
        flow.append(Paragraph(story["family_notes"], STY["Body"]))
    return flow


def _photos_section(photos):
    flow = [
        Paragraph("CHAPTER FIVE", STY["SectionKicker"]),
        Paragraph("Photo Keepsakes", STY["SectionHeading"]),
        HRFlowable(width="100%", thickness=0.8, color=PAPER_SHADE, spaceAfter=16),
    ]
    if not photos:
        flow.append(Paragraph(
            "No photographs have been added yet. Upload keepsake photos "
            "from any chapter page to include them here.", STY["Body"]))
        return flow

    cell_w, cell_h = 6.6 * cm, 5.1 * cm
    cells = []
    for p in photos:
        img_path = BASE_DIR / "static" / p["image_path"]
        block = []
        if img_path.exists():
            try:
                block.append(Image(str(img_path), width=cell_w - 0.4 * cm, height=cell_h - 1.4 * cm))
            except Exception:
                block.append(Spacer(1, cell_h - 1.4 * cm))
        else:
            block.append(Spacer(1, cell_h - 1.4 * cm))
        cap = (p["category"] or "").title()
        block.append(Paragraph(cap, STY["Caption"]))
        cells.append(block)

    rows = [cells[i:i + 2] for i in range(0, len(cells), 2)]
    t = Table(rows, colWidths=[cell_w, cell_w])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.6, PAPER_SHADE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, PAPER_SHADE),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]
    t.setStyle(TableStyle(style))
    flow.append(t)
    return flow


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def build_legacy_book(user: dict, story: dict, photos: list, output_path: str):
    """Renders the full Legacy Book PDF to ``output_path``."""
    doc = BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2.1 * cm, bottomMargin=2 * cm,
        title=f"{user.get('name', 'Legacy Book')} — Legacy Book",
        author="Generational Story Preserver",
    )
    doc.running_title = "Legacy Book"
    doc.running_name = user.get("name", "")

    full_frame_navy = Frame(0, 0, A4[0], A4[1], id="navy", showBoundary=0)
    content_frame = Frame(
        2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4.3 * cm, id="content", showBoundary=0,
    )

    def cover_on_page(c, d):
        _draw_cover(c, d, user)

    def divider_on_page(c, d):
        _paint_navy_page(c, d, footer=True)

    def content_on_page(c, d):
        _paint_paper_page(c, d)

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[full_frame_navy], onPage=cover_on_page),
        PageTemplate(id="divider", frames=[full_frame_navy], onPage=divider_on_page),
        PageTemplate(id="content", frames=[content_frame], onPage=content_on_page),
    ])

    story_flow = []

    # ---- Cover ---------------------------------------------------------
    # All cover visuals are drawn by the cover_on_page onPage callback
    # (_draw_cover), which computes every element's position cumulatively
    # so nothing overlaps. This flowable list just needs to occupy page 1
    # and then switch templates for chapter one.
    story_flow.append(Spacer(1, 1))
    story_flow.append(NextPageTemplate("divider"))
    story_flow.append(PageBreak())

    # ---- Section dividers + content -----------------------------------
    story_flow += _divider_page("Chapter One", "Biography", "Every life is a story worth keeping.")
    story_flow += _biography_section(user, story)

    story_flow.append(NextPageTemplate("divider"))
    story_flow.append(PageBreak())
    story_flow += _divider_page("Chapter Two", "Timeline", "The years, in their own order.")
    story_flow += _timeline_section(story)

    story_flow.append(NextPageTemplate("divider"))
    story_flow.append(PageBreak())
    story_flow += _divider_page("Chapter Three", "Wisdom &amp; Life Lessons", "What this life learned, for the ones who come next.")
    story_flow += _wisdom_section(user, story)

    story_flow.append(NextPageTemplate("divider"))
    story_flow.append(PageBreak())
    story_flow += _divider_page("Chapter Four", "Family Tree", "Roots, branches, and the people in between.")
    story_flow += _family_section(user, story)

    story_flow.append(NextPageTemplate("divider"))
    story_flow.append(PageBreak())
    story_flow += _divider_page("Chapter Five", "Photo Keepsakes", "A few frames from a long story.")
    story_flow += _photos_section(photos)

    # ---- Closing navy page ---------------------------------------------
    story_flow.append(NextPageTemplate("divider"))
    story_flow.append(PageBreak())
    story_flow.append(Spacer(1, 9 * cm))
    story_flow.append(Paragraph("END OF THIS CHAPTER", STY["DividerEyebrow"]))
    story_flow.append(Paragraph("The Story Continues", STY["DividerTitle"]))
    story_flow.append(Paragraph(
        "Generated with care by Generational Story Preserver.", STY["DividerNote"]))

    doc.build(story_flow)
    return output_path
