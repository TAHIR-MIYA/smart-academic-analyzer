"""Extractive summarisation: pick the most informative existing sentences (no text is generated).

    sentence score = (sum of TF-IDF weights of the distinct content terms in the sentence) / sqrt(number of those terms)
    first eligible sentence gets a +25 % position bonus (introductions state the topic)
    selection = highest scores first, skipping sentences that mostly repeat an already selected one
    output   = selected sentences in their ORIGINAL order

Why divide by the square root of the length: dividing by the length itself favours very short sentences,
not dividing favours very long ones; the square root is a common compromise.
"""
import math

from app.nlp.pipeline import PreprocessedDocument
from app.nlp.tfidf import KEYWORD_POS
from app.utils.errors import EmptyDocumentError

MIN_WORDS = 5            # shorter 'sentences' are usually headings or fragments
MAX_WORDS = 60           # longer ones are usually extraction errors (e.g. a whole table row)
POSITION_BONUS = 0.25
REDUNDANCY_THRESHOLD = 0.6   # Jaccard overlap of term sets above which a sentence counts as a repeat
DEFAULT_RATIO = 0.25
MAX_DEFAULT_SENTENCES = 8
SCORE_CHART_LIMIT = 200


def _sentence_terms(doc: PreprocessedDocument) -> list[set[str]]:
    """Distinct scored terms per sentence (same POS filter as keyword extraction)."""
    def collect(allowed):
        out: list[set[str]] = [set() for _ in doc.sentences]
        for r in doc.records:
            if not r.is_stopword and (allowed is None or r.pos in allowed):
                out[r.sentence_index].add(r.lemma)
        return out

    terms = collect(KEYWORD_POS)
    return terms if any(terms) else collect(None)


def summarize(
    doc: PreprocessedDocument,
    weights: dict[str, float],
    idf_mode: str,
    num_sentences: int | None = None,
    position_bonus: float = POSITION_BONUS,
    redundancy_threshold: float = REDUNDANCY_THRESHOLD,
) -> dict:
    sentence_terms = _sentence_terms(doc)
    word_counts = [len(s.split()) for s in doc.sentences]
    eligible = [i for i, n in enumerate(word_counts) if MIN_WORDS <= n <= MAX_WORDS and sentence_terms[i]]
    if not eligible:
        raise EmptyDocumentError("The document has no sentences suitable for summarisation.")

    raw: dict[int, float] = {}
    for i in eligible:
        terms = sentence_terms[i]
        raw[i] = sum(weights.get(t, 0.0) for t in terms) / math.sqrt(len(terms))
    raw[eligible[0]] *= 1.0 + position_bonus
    best = max(raw.values()) or 1.0

    if num_sentences is None:
        target = min(max(round(DEFAULT_RATIO * len(doc.sentences)), 1), MAX_DEFAULT_SENTENCES)
    else:
        target = num_sentences
    target = min(target, len(eligible))

    selected: list[int] = []
    for i in sorted(eligible, key=lambda k: (-raw[k], k)):
        if len(selected) >= target:
            break
        redundant = any(
            len(sentence_terms[i] & sentence_terms[j]) / len(sentence_terms[i] | sentence_terms[j]) > redundancy_threshold
            for j in selected
        )
        if not redundant:
            selected.append(i)
    selected.sort()

    summary = [
        {"index": i, "text": doc.sentences[i], "score": round(raw[i], 6),
         "relative_score": round(raw[i] / best, 4), "words": word_counts[i]}
        for i in selected
    ]
    total_words = sum(word_counts) or 1
    note = None
    if len(selected) == len(eligible):
        note = "The document is short: every eligible sentence is in the summary."
    return {
        "method": "TF-IDF sentence scoring with position bonus and redundancy filter",
        "idf_mode": idf_mode,
        "sentences_in_document": len(doc.sentences),
        "sentences_eligible": len(eligible),
        "sentences_selected": len(selected),
        "compression_ratio": round(sum(s["words"] for s in summary) / total_words, 4),
        "summary": summary,
        "summary_text": " ".join(s["text"] for s in summary),
        "sentence_scores": [
            {"index": i, "score": round(raw.get(i, 0.0), 6), "selected": i in selected, "words": word_counts[i]}
            for i in range(min(len(doc.sentences), SCORE_CHART_LIMIT))
        ],
        "parameters": {"position_bonus": position_bonus, "redundancy_threshold": redundancy_threshold,
                       "min_words": MIN_WORDS, "max_words": MAX_WORDS},
        "note": note,
    }
