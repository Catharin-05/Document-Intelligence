"""
Cheap steps that run BEFORE any model call (stage 0) and keep the prompt small.

  rule_verdict()    obvious junk decided by plain facts (grid bubbles, URLs, bare dimensions)
  LegendIndex       the legend text as a lookup table:
                      .relevant(texts)   only the legend lines whose code appears in this item  (short prompt)
                      .auto_right(...)   every distinct text is a legend code whose meaning is the item's work
"""
import re

CODE_RE = re.compile(r"^[A-Z]{1,4}-?\d{0,3}[A-Z]{0,2}(\.\d+)?$")
TOKEN_RE = re.compile(r"[A-Z0-9][A-Z0-9.\-/]*[A-Z0-9]|[A-Z0-9]")
STOP = {"AND", "THE", "FOR", "WITH", "FROM", "INTO", "ALL", "PER", "NEW", "TO", "OF", "AT", "IN", "ON", "BE", "OR",
        "PROVIDE", "INSTALL", "FURNISH", "FURNISHED", "INSTALLED", "WORK", "ITEM"}


def tokens(text):
    out = set()
    for t in TOKEN_RE.findall((text or "").upper()):
        t = t.strip(".-/")
        if len(t) >= 2 and t not in STOP:
            out.add(t)
            out.add(t.replace("-", ""))
    return out


def stems(text):
    """Lower-case content words reduced to a 5-letter stem, for a loose meaning-overlap test."""
    ws = re.findall(r"[a-z]{4,}", (text or "").lower())
    return {w[:5] for w in ws if w.upper() not in STOP}


# ------------------------------------------------------------------ stage 0: rules
BARE_DIM = re.compile(r"^[\d\s.,'\"/\-\u2013x\u00d7]+$")


def rule_verdict(sig, cfg, texts):
    """Return a verdict dict if plain facts settle the item, else None. Thresholds are deliberately strict."""
    n = sig["n_regions"]
    if sig["frac_url_or_email"] >= cfg["url_frac"]:
        return _v("title_block_or_page_furniture",
                  f"URL/e-mail text only ({sig['frac_url_or_email']:.0%} of regions): title-block or page furniture, not work.")
    if n >= cfg["grid_min_regions"] and sig["frac_look_like_grid_labels"] >= cfg["grid_frac"] \
            and sig["frac_within_12pct_of_sheet_edge"] >= cfg["grid_edge_frac"]:
        return _v("grid_bubble",
                  f"{n} regions, {sig['frac_look_like_grid_labels']:.0%} look like grid labels (1-2 letters / numbers) and "
                  f"{sig['frac_within_12pct_of_sheet_edge']:.0%} sit at the sheet edge: column-line bubbles, not a product or work.")
    # only text with NO letters at all (e.g. 12'-6", 3.5): "12''SD" is a pipe callout (size + SD), so it is NOT caught here
    if texts and all(BARE_DIM.match(t) for t in texts):
        return _v("dimension_or_annotation", "every text is a bare number or dimension with no letters: a measurement, not work.")
    return None


def _v(category, reason):
    return {"verdict": "wrong", "category": category, "reason": "[rule] " + reason, "supporting_regions": [],
            "unsupported_regions": [], "confidence": 0.9, "needs_human_review": False, "decided_by": "rule"}


# ------------------------------------------------------------------ legend lookup
class LegendIndex:
    def __init__(self, text):
        self.abbr = {}   # code -> [(segment, meaning)]
        self.asm = {}    # code -> full assembly line
        for line in (text or "").splitlines():
            line = line.strip()
            if not line or line.startswith("====="):
                continue
            m = re.match(r"^\[[A-Z ]+TYPE ([^\]]+)\]", line)
            if m:
                self.asm[m.group(1).strip().upper()] = line
                continue
            for seg in line.split(" | "):
                m = re.match(r"^(\S+)\s{2,}(\S.*)$", seg.strip())
                if m:
                    self.abbr.setdefault(m.group(1).upper(), []).append((seg.strip(), m.group(2)))

    def relevant(self, *texts, max_lines=40):
        toks = set()
        for t in texts:
            toks |= tokens(t)
        a, s = [], []
        for t in sorted(toks):
            for seg, _ in self.abbr.get(t, []):
                if seg not in a:
                    a.append(seg)
            if t in self.asm and self.asm[t] not in s:
                s.append(self.asm[t])
        parts = []
        if a:
            parts.append("ABBREVIATIONS (code  meaning):\n" + "\n".join(a[:max_lines]))
        if s:
            parts.append("ASSEMBLY TYPES:\n" + "\n".join(s[:max_lines]))
        if not parts:
            return ("(no legend entry matches any code or word in this item's text, so none of its codes is defined "
                    "in the legend sheets)")
        return "\n\n".join(parts)

    def auto_right(self, distinct_texts, item_text):
        """RIGHT without a model when EVERY distinct text is a single code that the legend defines (and is not
        also an assembly type), and a meaning shares a content word with the bid item. Returns a verdict or None."""
        if not distinct_texts or len(distinct_texts) > 6:
            return None
        item_stems = stems(item_text)
        hits = []
        for t in distinct_texts:
            u = t.strip().upper()
            if not CODE_RE.match(u) or u in self.asm or u not in self.abbr:
                return None
            ok = [m for _, m in self.abbr[u] if stems(m) & item_stems]
            if not ok:
                return None
            hits.append(f"{u} = {ok[0]}")
        return {"verdict": "right", "category": "supported",
                "reason": "[legend] every text is a legend code whose defined meaning matches the item: " + "; ".join(hits),
                "supporting_regions": [], "unsupported_regions": [], "confidence": 0.75,
                "needs_human_review": False, "decided_by": "legend"}