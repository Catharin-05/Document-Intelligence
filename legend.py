"""
Legend extraction: turn the project's legend sheets into plain text a model can use.

    from legend import extract_legend_text
    text = extract_legend_text("drawings.pdf", pages=[1, 2, 3])      # 1-based pdf pages
    Path("legend.txt").write_text(text)

Two kinds of legend content are handled, both from the PDF's own text layer (no OCR):

  1. LISTS / TABLES (abbreviations, symbol legends)
     Words are grouped into visual rows. Gaps inside a row decide the separator:
        small gap  -> one space      ("AIR CONDITIONING")
        medium gap -> two spaces     (code    meaning)
        large gap  -> " | "          (next column of the table)
     so each code stays next to its meaning instead of being scrambled.

  2. ASSEMBLY CELLS (wall / roof / floor types drawn as a section with a label under it)
     The text layer puts the type code ("BR1") far from the layer notes ("BRICK VENEER", "AIR GAP").
     In the drawing, each cell has its label at the bottom and its layer notes above, in the same
     column. So every note is attached to the label below it in its column, giving
        [WALL TYPE BR1]  FIRE RATING: N/A ... | BRICK VENEER | AIR GAP | ...

Pages stored with /Rotate are handled: get_text() returns unrotated coordinates, so every box is
mapped through page.rotation_matrix into the page as displayed (3024 x 2160 for these sheets).
"""
import re
from pathlib import Path

import pymupdf as fitz

LABEL_RE = re.compile(r"\b(WALL|ROOF|FLOOR|CEILING|PARTITION|ASSEMBLY)\s+TYPE\b", re.I)
CODE_RE = re.compile(r"^[A-Z]{1,4}[-]?\d{0,3}[A-Z]{0,2}(\.\d+)?$")


class Box:
    __slots__ = ("x0", "y0", "x1", "y1", "text")

    def __init__(self, x0, y0, x1, y1, text):
        self.x0, self.y0, self.x1, self.y1, self.text = x0, y0, x1, y1, text

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2


def _scaled(page, rect, sx, sy):
    r = fitz.Rect(rect) * page.rotation_matrix
    r.normalize()
    return r.x0 * sx, r.y0 * sy, r.x1 * sx, r.y1 * sy


def page_words(page, width=3024, height=2160):
    sx, sy = width / page.rect.width, height / page.rect.height
    return [Box(*_scaled(page, w[:4], sx, sy), w[4]) for w in page.get_text("words")]


def page_blocks(page, width=3024, height=2160):
    sx, sy = width / page.rect.width, height / page.rect.height
    out = []
    for b in page.get_text("blocks"):
        if b[6] != 0:
            continue
        t = " / ".join(l.strip() for l in b[4].strip().split("\n") if l.strip())
        if t:
            out.append(Box(*_scaled(page, b[:4], sx, sy), t))
    return out


# ------------------------------------------------------------------ rows (lists / tables)
def rows_to_text(words, small=12, large=60):
    """Visual rows, gaps decide the separators. words: list[Box]."""
    if not words:
        return ""
    words = sorted(words, key=lambda w: (w.cy, w.x0))
    heights = sorted(w.y1 - w.y0 for w in words)
    tol = max(3.0, heights[len(heights) // 2] * 0.5)
    rows, cur = [], [words[0]]
    for w in words[1:]:
        if abs(w.cy - cur[0].cy) <= tol:  # compare with the row's first word, so rows cannot drift
            cur.append(w)
        else:
            rows.append(cur)
            cur = [w]
    rows.append(cur)
    lines = []
    for r in rows:
        r.sort(key=lambda w: w.x0)
        s = r[0].text
        for a, b in zip(r, r[1:]):
            gap = b.x0 - a.x1
            s += (" | " if gap > large else "  " if gap > small else " ") + b.text
        lines.append(s.strip())
    return "\n".join(l for l in lines if l)


# ------------------------------------------------------------------ assembly cells
def find_labels(blocks):
    """[(label_box, code)] for blocks like 'WALL TYPE:' (+ 'BR1' in the same or the block below)."""
    labels = []
    for b in blocks:
        if not LABEL_RE.search(b.text):
            continue
        parts = [p.strip() for p in b.text.split("/")]
        code = next((p for p in parts if p and not LABEL_RE.search(p) and CODE_RE.match(p)), None)
        if not code:  # code is its own block directly under the label
            below = [c for c in blocks if c is not b and CODE_RE.match(c.text)
                     and 0 <= c.y0 - b.y1 <= 40 and abs(c.cx - b.cx) <= 60]
            if below:
                code = min(below, key=lambda c: c.y0 - b.y1).text
        if code:
            labels.append((b, code))
    return labels


def assembly_cells(blocks, labels):
    """Attach every block to the label below it, in its column. Returns (cells, leftover blocks)."""
    labels = sorted(labels, key=lambda lc: (round(lc[0].y0 / 60), lc[0].x0))
    # typical width of one cell = median spacing between neighbouring labels in the same row
    gaps = []
    for l, _ in labels:
        nxt = [m.x0 - l.x0 for m, _ in labels if abs(m.y0 - l.y0) < 60 and m.x0 > l.x0]
        if nxt:
            gaps.append(min(nxt))
    gaps.sort()
    cell_w = gaps[len(gaps) // 2] if gaps else 700
    cells = {id(l): [] for l, _ in labels}
    used = set()
    for i, (lab, code) in enumerate(labels):
        same_row = [l for l, _ in labels if abs(l.y0 - lab.y0) < 60 and l.x0 > lab.x0]
        left = lab.x0 - 45
        right = (min(l.x0 for l in same_row) - 45) if same_row else lab.x0 - 45 + cell_w
        above_labels = [l.y1 for l, _ in labels if l.y1 < lab.y0 - 20 and l.x0 < right and l.x0 > left - 400]
        top = max(above_labels) if above_labels else 0
        for b in blocks:
            if id(b) in used or b is lab:
                continue
            if b.x0 >= left and b.x0 < right and top <= b.cy <= lab.y1 + 55:
                if any(b is l for l, _ in labels):
                    continue
                if CODE_RE.match(b.text) and 0 <= b.y0 - lab.y1 <= 40 and abs(b.cx - lab.cx) <= 60:
                    used.add(id(b))  # the code block itself
                    continue
                cells[id(lab)].append(b)
                used.add(id(b))
    leftover = [b for b in blocks if id(b) not in used and not any(b is l for l, _ in labels)]
    return [(lab, code, cells[id(lab)]) for lab, code in labels], leftover


def cells_to_text(cells):
    out = []
    for lab, code, bl in sorted(cells, key=lambda c: (round(c[0].y0 / 60), c[0].x0)):
        kind = LABEL_RE.search(lab.text)
        head = f"[{kind.group(0).upper() if kind else 'TYPE'} {code}]"
        notes = [b.text for b in sorted(bl, key=lambda b: (b.y0, b.x0))]
        out.append(head + "  " + " | ".join(notes))
    return "\n".join(out)


# ------------------------------------------------------------------ public API
def extract_page(page, width=3024, height=2160):
    blocks = page_blocks(page, width, height)
    labels = find_labels(blocks)
    parts = []
    if len(labels) >= 2:
        cells, left = assembly_cells(blocks, labels)
        parts.append("ASSEMBLY TYPES (each line = one type; its layers/notes follow it):\n" + cells_to_text(cells))
        left_ids = {id(b) for b in left}
        words = [w for w in page_words(page, width, height)
                 if any(b.x0 - 1 <= w.x0 and w.x1 <= b.x1 + 1 and b.y0 - 1 <= w.y0 and w.y1 <= b.y1 + 1 for b in left)]
        rest = rows_to_text(words)
        if rest:
            parts.append("OTHER TEXT ON THIS SHEET:\n" + rest)
    else:
        parts.append(rows_to_text(page_words(page, width, height)))
    return "\n\n".join(parts)


def extract_legend_text(pdf, pages=None, sheets=None, width=3024, height=2160):
    """
    pdf    path or open pymupdf document
    pages  1-based page numbers of the legend sheets  (or)
    sheets list of (sheet_number, sheet_name, page_number) tuples, to print proper headings
    """
    doc = fitz.open(pdf) if isinstance(pdf, (str, Path)) else pdf
    if sheets is None:
        sheets = [(f"page {p}", "", p) for p in pages or []]
    out = []
    for sn, name, pn in sheets:
        out.append(f"===== LEGEND SHEET {sn} {name} (pdf page {pn}) =====\n" + extract_page(doc[pn - 1], width, height))
    return "\n\n".join(out)