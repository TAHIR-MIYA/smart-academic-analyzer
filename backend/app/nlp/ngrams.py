"""Unigram, bigram and trigram frequency analysis (NLTK's ngrams helper).

N-grams are built from content lemmas (stop words removed) and never cross a sentence
boundary. Because stop words are removed first, two words may be adjacent in the n-gram
that were separated by a function word in the original text - a deliberate simplification
that surfaces topical phrases such as 'language processing'.
"""
from collections import Counter

from nltk.util import ngrams

from app.nlp.pipeline import PreprocessedDocument

LEVELS = {1: "Unigrams", 2: "Bigrams", 3: "Trigrams"}


def analyse_ngrams(doc: PreprocessedDocument, top_k: int = 15) -> dict:
    sentences = doc.content_by_sentence(None)
    levels = []
    for n, label in LEVELS.items():
        counter: Counter[tuple[str, ...]] = Counter()
        for sent in sentences:
            if len(sent) >= n:
                counter.update(ngrams(sent, n))
        # Counter keeps first-seen order and sorted() is stable, so ties resolve by first occurrence.
        ranked = sorted(counter.items(), key=lambda kv: -kv[1])
        levels.append(
            {
                "n": n,
                "label": label,
                "total": sum(counter.values()),
                "distinct": len(counter),
                "top": [{"ngram": " ".join(gram), "count": c} for gram, c in ranked[:top_k]],
            }
        )
    return {
        "levels": levels,
        "note": "Built from lemmatised content words within sentences (stop words removed first).",
    }
