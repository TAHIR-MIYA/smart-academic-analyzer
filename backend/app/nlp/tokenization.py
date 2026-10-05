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


def split_sentences(text: str) -> list[str]:
    try:
        sentences = sent_tokenize(text)
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
