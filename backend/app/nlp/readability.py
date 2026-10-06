"""Readability formulas implemented from scratch (no library), so every number can be explained.

    Flesch Reading Ease  = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    Flesch-Kincaid Grade = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    Gunning Fog          = 0.4 * ((words / sentences) + 100 * (complex words / words))
    Automated Readability Index = 4.71 * (letters / words) + 0.5 * (words / sentences) - 21.43

Syllables are counted with a vowel-group heuristic, so scores are approximations. The formulas were
designed for continuous English prose; lists, notices and question papers give unreliable values.
"""
import re
import unicodedata

from app.nlp.pipeline import PreprocessedDocument

_WORD_RE = re.compile(r"[^\W\d_]+(?:['-][^\W\d_]+)*")
_VOWEL_GROUPS = re.compile(r"[aeiouy]+")
_ES_KEEP = ("ses", "zes", "xes", "ches", "shes", "ges", "ces")
MIN_RELIABLE_WORDS = 100
MIN_RELIABLE_SENTENCES = 3

FRE_BANDS = [  # (lower bound, description) - the standard Flesch interpretation table
    (90, "Very easy (about 5th grade)"), (80, "Easy (6th grade)"), (70, "Fairly easy (7th grade)"),
    (60, "Plain English (8th-9th grade)"), (50, "Fairly difficult (10th-12th grade)"),
    (30, "Difficult (college level)"), (0, "Very difficult (college graduate)"),
]


def _syllables_in_part(part: str) -> int:
    word = unicodedata.normalize("NFKD", part.lower()).encode("ascii", "ignore").decode()
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    n = len(_VOWEL_GROUPS.findall(word))
    if word.endswith("e") and not word.endswith(("le", "ee", "ye")) and word[-2] not in "aeiou":
        n -= 1                                   # silent final e: 'make'
    elif word.endswith("es") and not word.endswith(_ES_KEEP):
        n -= 1                                   # 'makes'
    elif word.endswith("ed") and not word.endswith(("ted", "ded")):
        n -= 1                                   # 'jumped'
    return max(n, 1)


def count_syllables(word: str) -> int:
    """Approximate syllable count; hyphenated words are counted part by part."""
    return sum(_syllables_in_part(p) for p in re.split(r"[-']", word)) or 1


def _fre_band(score: float) -> str:
    for bound, text in FRE_BANDS:
        if score >= bound:
            return text
    return "Extremely difficult (beyond college graduate)"


def analyse_readability(doc: PreprocessedDocument) -> dict:
    words: list[str] = []
    sentences = 0
    for toks in doc.sentence_tokens:
        sent_words = [t for t in toks if _WORD_RE.fullmatch(t)]
        if sent_words:
            sentences += 1
            words.extend(sent_words)
    n_words = len(words)
    syllables = sum(count_syllables(w) for w in words)
    complex_words = sum(1 for w in words if count_syllables(w) >= 3)
    letters = sum(len(re.sub(r"[-']", "", w)) for w in words)

    wps = n_words / sentences
    spw = syllables / n_words
    fre = 206.835 - 1.015 * wps - 84.6 * spw
    fkgl = 0.39 * wps + 11.8 * spw - 15.59
    fog = 0.4 * (wps + 100 * complex_words / n_words)
    ari = 4.71 * (letters / n_words) + 0.5 * wps - 21.43

    reliable = n_words >= MIN_RELIABLE_WORDS and sentences >= MIN_RELIABLE_SENTENCES
    return {
        "reliable": reliable,
        "warning": None if reliable else (
            f"Only {n_words} words in {sentences} sentence(s): readability formulas need at least "
            f"{MIN_RELIABLE_WORDS} words and {MIN_RELIABLE_SENTENCES} sentences to be meaningful."),
        "counts": {"words": n_words, "sentences": sentences, "syllables": syllables,
                   "complex_words": complex_words, "letters": letters},
        "averages": {"words_per_sentence": round(wps, 2), "syllables_per_word": round(spw, 3),
                     "letters_per_word": round(letters / n_words, 2)},
        "scores": [
            {"name": "Flesch Reading Ease", "value": round(fre, 2), "interpretation": _fre_band(fre),
             "formula": "206.835 - 1.015 x (words/sentences) - 84.6 x (syllables/words); higher = easier"},
            {"name": "Flesch-Kincaid Grade Level", "value": round(fkgl, 2),
             "interpretation": f"About US school grade {max(fkgl, 0):.1f}",
             "formula": "0.39 x (words/sentences) + 11.8 x (syllables/words) - 15.59"},
            {"name": "Gunning Fog Index", "value": round(fog, 2),
             "interpretation": f"About {max(fog, 0):.1f} years of formal education",
             "formula": "0.4 x ((words/sentences) + 100 x (words of 3+ syllables / words))"},
            {"name": "Automated Readability Index", "value": round(ari, 2),
             "interpretation": f"About US school grade {max(ari, 0):.1f}",
             "formula": "4.71 x (letters/words) + 0.5 x (words/sentences) - 21.43"},
        ],
        "reading_level": _fre_band(fre),
        "note": "Syllables are estimated with a vowel-group heuristic, so scores are approximate.",
    }
