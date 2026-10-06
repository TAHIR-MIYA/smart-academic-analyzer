"""Vocabulary diversity (lexical richness) measures.

Raw type-token ratio falls as a text gets longer, so several measures are reported:
  TTR           types / tokens                       (length dependent)
  Root TTR      types / sqrt(tokens)                 (Guiraud)
  Corrected TTR types / sqrt(2 * tokens)             (Carroll)
  MATTR         mean TTR over a sliding window       (largely length independent)
Tokens are case-folded alphabetic words, stop words included.
"""
import math
from collections import Counter

from app.nlp.pipeline import PreprocessedDocument

MATTR_WINDOW = 50
MIN_RELIABLE_TOKENS = 100
ZIPF_TOP = 30


def mattr(tokens: list[str], window: int = MATTR_WINDOW) -> float:
    """Moving-average type-token ratio; falls back to plain TTR if the text is shorter than the window."""
    n = len(tokens)
    if n == 0:
        return 0.0
    if n <= window:
        return len(set(tokens)) / n
    counts = Counter(tokens[:window])
    total = len(counts)
    for i in range(1, n - window + 1):
        out = tokens[i - 1]
        counts[out] -= 1
        if counts[out] == 0:
            del counts[out]
        counts[tokens[i + window - 1]] += 1
        total += len(counts)
    return total / ((n - window + 1) * window)


def analyse_vocabulary(doc: PreprocessedDocument) -> dict:
    tokens = [r.lower for r in doc.records]
    n = len(tokens)
    freq = Counter(tokens)
    types = len(freq)
    hapax = sum(1 for c in freq.values() if c == 1)
    dis = sum(1 for c in freq.values() if c == 2)
    content = sum(1 for r in doc.records if not r.is_stopword)
    reliable = n >= MIN_RELIABLE_TOKENS

    ttr = types / n
    measures = [
        {"key": "ttr", "name": "Type-Token Ratio (TTR)", "value": round(ttr, 4),
         "description": "Distinct words divided by total words. Falls as documents get longer."},
        {"key": "root_ttr", "name": "Root TTR (Guiraud)", "value": round(types / math.sqrt(n), 3),
         "description": "Distinct words divided by the square root of total words; less sensitive to length."},
        {"key": "corrected_ttr", "name": "Corrected TTR (Carroll)", "value": round(types / math.sqrt(2 * n), 3),
         "description": "Distinct words divided by the square root of twice the total words."},
        {"key": "mattr", "name": f"MATTR (window {MATTR_WINDOW})", "value": round(mattr(tokens), 4),
         "description": "Average TTR over every window of 50 consecutive words; comparable between documents of different length."},
        {"key": "hapax_ratio", "name": "Hapax legomena ratio", "value": round(hapax / types, 4),
         "description": "Share of distinct words that occur exactly once."},
        {"key": "lexical_density", "name": "Lexical density", "value": round(content / n, 4),
         "description": "Share of words that are content words (stop words excluded)."},
    ]
    spectrum = Counter(min(c, 5) for c in freq.values())
    return {
        "reliable": reliable,
        "warning": None if reliable else (
            f"Only {n} words: diversity measures depend strongly on length and are unstable below {MIN_RELIABLE_TOKENS}."),
        "tokens": n,
        "types": types,
        "lemma_types": len({r.lemma for r in doc.records}),
        "hapax_count": hapax,
        "dis_legomena_count": dis,
        "measures": measures,
        "frequency_spectrum": [
            {"occurrences": "5+" if k == 5 else str(k), "count": spectrum.get(k, 0)} for k in range(1, 6)
        ],
        "zipf": [{"rank": i, "word": w, "count": c}
                 for i, (w, c) in enumerate(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:ZIPF_TOP], 1)],
    }
