"""Step 2: sentence and word tokenisation using NLTK (Punkt + Treebank-style word tokeniser)."""
import re

from nltk.tokenize import sent_tokenize, word_tokenize

from app.utils.errors import NLPResourceError

# A 'word token' is alphabetic (Unicode letters), optionally with inner hyphens/apostrophes.
_WORD_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*")
_HAS_WORDCHAR_RE = re.compile(r"\w")
MIN_WORD_LENGTH = 2
# Treebank-style tokenisers split "doesn't" into "does" + "n't"; the clitic is not a word.
_CLITIC_TOKENS = {"n't"}


_END_PUNCT = (".", "!", "?", ":", ";", ",")
_SMALL_WORDS = {"of", "and", "the", "in", "for", "to", "a", "an", "on", "with", "or", "vs", "by"}
_MAX_HEADING_WORDS = 8


def _is_heading(line: str, previous: str | None, following: str | None, previous_was_heading: bool) -> bool:
    """A short, unpunctuated line standing alone between sentences: 'Introduction', '3.1 System Design'."""
    s = line.strip()
    words = s.split()
    if not words or s.endswith(_END_PUNCT) or len(words) > _MAX_HEADING_WORDS:
        return False
    prev = (previous or "").strip()
    nxt = (following or "").strip()
    starts_unit = previous is None or not prev or prev.endswith((".", "!", "?", ":", ";")) or previous_was_heading
    ends_unit = following is None or not nxt or nxt[0].isupper() or nxt[0].isdigit() or nxt[0] in "-*\u2022"
    if not (starts_unit and ends_unit):
        return False
    title_like = all(w[0].isupper() or not w[0].isalpha() or w.lower() in _SMALL_WORDS for w in words)
    return title_like or len(words) <= 3


def mark_headings(text: str) -> str:
    """Add a full stop to heading lines so the sentence splitter does not glue them to the next sentence.

    Without this, 'PROBLEM STATEMENT\\nThe existing system ...' would become ONE sentence.
    Wrapped fragments such as 'The system was implemented using' are not treated as headings
    because they are not title-like and the line before them does not end a sentence.
    """
    lines = text.split("\n")
    out: list[str] = []
    was_heading = False
    for i, line in enumerate(lines):
        previous = lines[i - 1] if i > 0 else None
        following = lines[i + 1] if i + 1 < len(lines) else None
        was_heading = _is_heading(line, previous, following, was_heading)
        out.append(line.rstrip() + "." if was_heading else line)
    return "\n".join(out)


def split_sentences(text: str) -> list[str]:
    try:
        sentences = sent_tokenize(mark_headings(text))
    except LookupError as exc:
        raise NLPResourceError(
            "NLTK 'punkt_tab' tokenizer data is not installed.",
            details={"fix": "python -m scripts.setup_nlp"},
        ) from exc
    return [" ".join(s.split()) for s in sentences if s.strip()]


def tokenize_words(sentence: str) -> list[str]:
    try:
        # preserve_line=True: the sentence is already split, do not split it again.
        return word_tokenize(sentence, preserve_line=True)
    except LookupError as exc:
        raise NLPResourceError(
            "NLTK 'punkt_tab' tokenizer data is not installed.",
            details={"fix": "python -m scripts.setup_nlp"},
        ) from exc


def is_word_token(token: str) -> bool:
    """True for alphabetic tokens of length >= 2 (drops punctuation, numbers, 1-letter tokens)."""
    if token.lower() in _CLITIC_TOKENS:
        return False
    return len(token) >= MIN_WORD_LENGTH and _WORD_RE.fullmatch(token) is not None


def has_word_char(token: str) -> bool:
    """True if the token contains any letter/digit (used for plain word counts, numbers included)."""
    return _HAS_WORDCHAR_RE.search(token) is not None
