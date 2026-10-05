"""TF-IDF keyword extraction.

    tf(t, d)  = count(t in d) / total content terms in d
    idf(t)    = ln((1 + N) / (1 + df(t))) + 1          (the 'smooth' IDF used by scikit-learn)
    score     = tf * idf

IDF needs a collection of "documents". Three modes, always reported to the user:
  1. reference_corpus     - df table built from the training dataset (best; created in Module 4)
  2. document_sentences   - each sentence of the uploaded document is treated as a document
  3. term_frequency       - too few sentences for a meaningful IDF; ranking by tf only
"""
import json
import logging
import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from app.nlp.pipeline import PreprocessedDocument

logger = logging.getLogger(__name__)

# Topical keywords are overwhelmingly nouns, proper nouns and adjectives; verbs such as
# 'use' or 'show' are frequent but rarely topical.
KEYWORD_POS = ("NOUN", "PROPN", "ADJ")
MIN_SENTENCES_FOR_IDF = 5
FORMULA = "score = tf x idf;  tf = count / total terms;  idf = ln((1 + N) / (1 + df)) + 1"


def smooth_idf(n_docs: int, df: int) -> float:
    return math.log((1 + n_docs) / (1 + df)) + 1.0


def keyword_sentences(doc: PreprocessedDocument) -> tuple[list[list[str]], tuple[str, ...]]:
    """Per-sentence term lists used for keywords; falls back to all content words if the POS filter empties it."""
    filtered = doc.content_by_sentence(KEYWORD_POS)
    if filtered:
        return filtered, KEYWORD_POS
    return doc.content_by_sentence(None), ()


# ---------------------------------------------------------------------------
# Reference document-frequency table (built from the training dataset)
# ---------------------------------------------------------------------------
@dataclass
class ReferenceIdf:
    n_docs: int
    df: dict[str, int]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"n_docs": self.n_docs, "df": self.df}), encoding="utf-8")


def build_reference_idf(docs: Iterable[PreprocessedDocument]) -> ReferenceIdf:
    df: Counter[str] = Counter()
    n = 0
    for doc in docs:
        sentences, _ = keyword_sentences(doc)
        terms = {t for sent in sentences for t in sent}
        if not terms:
            continue
        df.update(terms)
        n += 1
    return ReferenceIdf(n_docs=n, df=dict(df))


@lru_cache(maxsize=4)
def _load_cached(path_str: str, mtime_ns: int) -> ReferenceIdf | None:
    try:
        raw = json.loads(Path(path_str).read_text(encoding="utf-8"))
        return ReferenceIdf(int(raw["n_docs"]), {str(k): int(v) for k, v in raw["df"].items()})
    except (OSError, ValueError, KeyError, TypeError):
        logger.warning("Reference IDF file %s is unreadable; ignoring it", path_str)
        return None


def load_reference_idf(path: Path) -> ReferenceIdf | None:
    """Return the reference table, or None when it has not been built yet."""
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return None
    ref = _load_cached(str(path), mtime)
    return ref if ref and ref.n_docs > 0 else None


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------
def extract_keywords(
    doc: PreprocessedDocument, reference: ReferenceIdf | None = None, top_k: int = 20
) -> dict:
    sentences, pos_used = keyword_sentences(doc)
    counts: Counter[str] = Counter(t for sent in sentences for t in sent)
    total = sum(counts.values())

    if reference is not None:
        mode = "reference_corpus"
        n_docs = reference.n_docs + 1  # + the uploaded document itself
        description = (
            f"IDF computed over {reference.n_docs} reference documents (the training dataset) "
            "plus this document."
        )

        def idf(term: str) -> float:
            return smooth_idf(n_docs, reference.df.get(term, 0) + 1)

    elif len(sentences) >= MIN_SENTENCES_FOR_IDF:
        mode = "document_sentences"
        n_docs = len(sentences)
        sentence_df: Counter[str] = Counter()
        for sent in sentences:
            sentence_df.update(set(sent))
        description = (
            f"IDF computed over the {n_docs} sentences of this document "
            "(each sentence is treated as one document)."
        )

        def idf(term: str) -> float:
            return smooth_idf(n_docs, sentence_df[term])

    else:
        mode = "term_frequency"
        n_docs = len(sentences)
        description = (
            f"Only {len(sentences)} sentence(s) with content words; at least {MIN_SENTENCES_FOR_IDF} "
            "are needed for a meaningful IDF, so terms are ranked by frequency only."
        )

        def idf(term: str) -> float:
            return 1.0

    scored = []
    for term, count in counts.items():
        tf = count / total
        weight = idf(term)
        scored.append((term, count, tf, weight, tf * weight))
    # Highest score first; ties broken alphabetically so results are deterministic.
    scored.sort(key=lambda row: (-row[4], row[0]))
    best = scored[0][4] if scored else 1.0

    keywords = [
        {
            "term": term,
            "count": count,
            "tf": round(tf, 6),
            "idf": round(weight, 4),
            "score": round(score, 6),
            "relative_score": round(score / best, 4),
        }
        for term, count, tf, weight, score in scored[:top_k]
    ]
    return {
        "idf_mode": mode,
        "idf_description": description,
        "idf_n_documents": n_docs,
        "pos_filter": list(pos_used),
        "formula": FORMULA,
        "total_terms": total,
        "vocabulary_size": len(counts),
        "keywords": keywords,
    }
