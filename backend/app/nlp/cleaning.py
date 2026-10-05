"""Step 1 of the pipeline: text cleaning.

Every step is a small, separately explainable rule and reports how many times it fired,
so the UI (and the viva) can show exactly what was changed.
"""
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

_INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff"
_PUNCT_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"',
    "\u2013": " - ", "\u2014": " - ", "\u2212": "-",
    "\u2022": "", "\u25cf": "", "\u25aa": "", "\u25e6": "", "\uf0b7": "",
}
_PUNCT_TABLE = {ord(k): v for k, v in _PUNCT_MAP.items()}

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f]")
_DEHYPHEN_RE = re.compile(r"([A-Za-z])-\n([a-z])")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PAGE_NO_RE = re.compile(r"^\s*(?:page\s+)?\d{1,4}(?:\s*(?:of|/)\s*\d{1,4})?\s*$", re.IGNORECASE)
_LINE_JOIN_RE = re.compile(r"(?<![.!?:;\n])\n(?=[a-z])")
_SPACES_RE = re.compile(r"[ \t]+")
_BLANKS_RE = re.compile(r"\n{3,}")

# Header/footer heuristic thresholds (see _remove_repeated_lines)
_MIN_REPEATS = 3
_MIN_LINE_CHARS = 12


@dataclass
class CleaningResult:
    text: str
    operations: list[dict]
    original_length: int
    cleaned_length: int


def _remove_repeated_lines(text: str) -> tuple[str, int]:
    """Drop running headers/footers: multi-word lines without end punctuation that repeat >= 3 times."""
    lines = text.split("\n")
    counts = Counter(line.strip() for line in lines)

    def is_boilerplate(line: str) -> bool:
        s = line.strip()
        return (
            counts[s] >= _MIN_REPEATS
            and len(s) >= _MIN_LINE_CHARS
            and " " in s
            and s[-1] not in ".?!:;,"
        )

    kept = [line for line in lines if not is_boilerplate(line)]
    return "\n".join(kept), len(lines) - len(kept)


def clean_text(text: str) -> CleaningResult:
    original_length = len(text)
    ops: list[dict] = []

    def record(name: str, description: str, count: int) -> None:
        ops.append({"name": name, "description": description, "count": count})

    # 1. Soft hyphens (+ the line break after them) and zero-width characters
    text, n_soft = re.subn("\u00ad\n?", "", text)
    n_invisible = sum(text.count(c) for c in _INVISIBLE)
    text = text.translate({ord(c): None for c in _INVISIBLE})
    record("Invisible characters", "Removed soft hyphens and zero-width characters", n_soft + n_invisible)

    # 2. Unicode normalisation (NFKC): turns ligatures such as 'ﬁ' into 'fi'
    n_norm = sum(1 for ch in text if ord(ch) > 127 and unicodedata.normalize("NFKC", ch) != ch)
    text = unicodedata.normalize("NFKC", text)
    record("Unicode normalisation", "NFKC: ligatures and compatibility characters -> plain letters", n_norm)

    # 3. Typographic punctuation
    n_punct = sum(text.count(c) for c in _PUNCT_MAP)
    text = text.translate(_PUNCT_TABLE)
    record("Typographic punctuation", "Curly quotes, long dashes and bullet symbols standardised", n_punct)

    # 4. Control characters (form feed becomes a paragraph break)
    n_ctrl = len(_CONTROL_RE.findall(text)) + text.count("\x0c")
    text = text.replace("\x0c", "\n\n")
    text = _CONTROL_RE.sub(" ", text).replace("\r\n", "\n").replace("\r", "\n")
    record("Control characters", "Removed non-printable control characters", n_ctrl)

    # Trim trailing blanks on each line so later rules see clean line ends (not reported)
    text = re.sub(r"[ \t]+\n", "\n", text)

    # 5. Hyphenated line breaks: 'informa-\ntion' -> 'information'
    text, n_hyph = _DEHYPHEN_RE.subn(r"\1\2", text)
    record("Hyphenated line breaks", "Rejoined words split across lines with a hyphen", n_hyph)

    # 6-7. URLs and e-mail addresses (noise for topical analysis)
    text, n_url = _URL_RE.subn(" ", text)
    record("URLs", "Removed web addresses", n_url)
    text, n_mail = _EMAIL_RE.subn(" ", text)
    record("E-mail addresses", "Removed e-mail addresses", n_mail)

    # 8. Page-number lines: '12', 'Page 3', 'Page 3 of 10'
    lines = text.split("\n")
    kept = [ln for ln in lines if not _PAGE_NO_RE.match(ln)]
    n_pages = len(lines) - len(kept)
    text = "\n".join(kept)
    record("Page numbers", "Removed lines that contain only a page number", n_pages)

    # 9. Repeated headers/footers
    text, n_rep = _remove_repeated_lines(text)
    record("Repeated headers/footers", "Removed multi-word lines repeated 3+ times (running headers)", n_rep)

    # 10. Soft-wrapped lines: join a line break when the next line starts in lower case
    text, n_join = _LINE_JOIN_RE.subn(" ", text)
    record("Line-wrap joins", "Merged lines broken in the middle of a sentence", n_join)

    # 11. Whitespace
    n_ws = len(re.findall(r"[ \t]{2,}", text)) + len(_BLANKS_RE.findall(text))
    text = _SPACES_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANKS_RE.sub("\n\n", text).strip()
    record("Whitespace", "Collapsed repeated spaces and blank lines", n_ws)

    return CleaningResult(text, ops, original_length, len(text))
