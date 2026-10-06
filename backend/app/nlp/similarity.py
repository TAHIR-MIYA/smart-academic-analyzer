"""Cosine similarity between TF-IDF vectors: document <-> topic profiles and document <-> document.

    cosine(a, b) = (a . b) / (|a| |b|)      0 = no shared terms, 1 = identical term profile

IDF is computed over the topic profiles plus the document(s) being analysed, so terms that appear in
every profile ('system', 'data') are down-weighted and distinctive vocabulary dominates.
"""
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.nlp.pipeline import PreprocessedDocument, run_pipeline
from app.utils.errors import NLPResourceError

logger = logging.getLogger(__name__)

WEAK_MATCH_THRESHOLD = 0.10   # rule of thumb, not a calibrated value
PAIR_THRESHOLD = 0.5          # minimum cosine for two sentences to be reported as similar
MIN_PAIR_TERMS = 4            # ignore very short sentences when matching sentences
MAX_SENTENCES_FOR_PAIRS = 300
TOP_PAIRS = 5
TOP_TERMS = 8


@dataclass(frozen=True)
class TopicProfile:
    name: str
    lemma_text: str


def _vectorizer() -> TfidfVectorizer:
    # Inputs are already lower-cased, space-separated lemmas, so split on whitespace only.
    return TfidfVectorizer(token_pattern=r"\S+", lowercase=False, sublinear_tf=True)


def _topic_name(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


@lru_cache(maxsize=4)
def _build_topics(signature: tuple, directory: str) -> list[TopicProfile]:
    profiles = []
    for name, _mtime in signature:
        path = Path(directory) / name
        try:
            text = path.read_text(encoding="utf-8")
            profiles.append(TopicProfile(_topic_name(path), run_pipeline(text).lemma_text))
        except Exception as exc:  # one bad profile must not disable the feature
            logger.warning("Skipping topic profile %s: %s", path, exc)
    return profiles


def load_topics(directory: Path) -> list[TopicProfile]:
    directory = Path(directory)
    files = sorted(directory.glob("*.txt")) if directory.is_dir() else []
    if not files:
        raise NLPResourceError(
            f"No topic profile files (.txt) found in {directory}.",
            details={"fix": "python -m datasets.build_topics"},
        )
    signature = tuple((p.name, p.stat().st_mtime_ns) for p in files)
    profiles = _build_topics(signature, str(directory))
    if not profiles:
        raise NLPResourceError("No usable topic profiles could be read.", details={"fix": "python -m datasets.build_topics"})
    return profiles


def _top_shared_terms(vec_a, vec_b, names, k: int = TOP_TERMS) -> list[dict]:
    product = vec_a.multiply(vec_b).tocoo()
    ranked = sorted(zip(product.col, product.data), key=lambda kv: -kv[1])[:k]
    return [{"term": str(names[j]), "weight": round(float(v), 4)} for j, v in ranked if v > 0]


def topic_similarity(doc: PreprocessedDocument, topics: list[TopicProfile]) -> dict:
    corpus = [t.lemma_text for t in topics] + [doc.lemma_text]
    vec = _vectorizer()
    matrix = vec.fit_transform(corpus)
    sims = cosine_similarity(matrix[-1], matrix[:-1])[0]
    ranked = sorted(zip(topics, sims), key=lambda ts: (-ts[1], ts[0].name))
    best_topic, best_sim = ranked[0]
    best_idx = topics.index(best_topic)
    weak = bool(best_sim < WEAK_MATCH_THRESHOLD)
    return {
        "method": f"Cosine similarity of TF-IDF vectors; IDF computed over {len(corpus)} documents "
                  f"({len(topics)} topic profiles + this document)",
        "topics_compared": len(topics),
        "best_topic": None if weak else best_topic.name,
        "best_similarity": round(float(best_sim), 4),
        "is_weak_match": weak,
        "weak_match_threshold": WEAK_MATCH_THRESHOLD,
        "similarities": [{"topic": t.name, "similarity": round(float(s), 4)} for t, s in ranked],
        "matched_terms": _top_shared_terms(matrix[-1], matrix[best_idx], vec.get_feature_names_out()),
        "note": "Weak match: no topic profile resembles this document." if weak else None,
    }


def _band(cos: float) -> str:
    if cos >= 0.9:
        return "Near-identical content"
    if cos >= 0.7:
        return "Very similar content"
    if cos >= 0.4:
        return "Related content"
    if cos >= 0.2:
        return "Loosely related"
    return "Mostly unrelated"


def compare_documents(a: PreprocessedDocument, b: PreprocessedDocument, topics: list[TopicProfile]) -> dict:
    corpus = [t.lemma_text for t in topics] + [a.lemma_text, b.lemma_text]
    vec = _vectorizer()
    matrix = vec.fit_transform(corpus)
    va, vb = matrix[-2], matrix[-1]
    cosine = float(cosine_similarity(va, vb)[0][0])

    set_a, set_b = set(a.content_lemmas), set(b.content_lemmas)
    jaccard = len(set_a & set_b) / len(set_a | set_b) if (set_a | set_b) else 0.0

    # Sentence-level matches: the most useful signal for copied passages.
    def prepare(doc):
        items = [(i, s, t) for i, (s, t) in enumerate(zip(doc.sentences, doc.lemma_texts_by_sentence()))
                 if len(t.split()) >= MIN_PAIR_TERMS]
        return items[:MAX_SENTENCES_FOR_PAIRS]

    items_a, items_b = prepare(a), prepare(b)
    pairs = []
    if items_a and items_b:
        sa = vec.transform([t for _, _, t in items_a])
        sb = vec.transform([t for _, _, t in items_b])
        sim = cosine_similarity(sa, sb)
        flat = sorted(((sim[i][j], i, j) for i in range(sim.shape[0]) for j in range(sim.shape[1])
                       if sim[i][j] >= PAIR_THRESHOLD), key=lambda x: -x[0])
        used_a, used_b = set(), set()
        for s, i, j in flat:  # each sentence appears in at most one reported pair
            if i in used_a or j in used_b:
                continue
            used_a.add(i)
            used_b.add(j)
            pairs.append({"similarity": round(float(s), 4), "index_a": items_a[i][0], "sentence_a": items_a[i][1][:300],
                          "index_b": items_b[j][0], "sentence_b": items_b[j][1][:300]})
            if len(pairs) >= TOP_PAIRS:
                break

    return {
        "method": f"Cosine similarity of TF-IDF vectors; IDF computed over {len(corpus)} documents "
                  f"({len(topics)} topic profiles + the two documents)",
        "cosine_similarity": round(cosine, 4),
        "vocabulary_overlap_jaccard": round(jaccard, 4),
        "interpretation": _band(cosine),
        "interpretation_note": "Interpretation bands are rule-of-thumb values, not calibrated thresholds.",
        "shared_terms": _top_shared_terms(va, vb, vec.get_feature_names_out(), 10),
        "similar_sentence_pairs": pairs,
        "pair_threshold": PAIR_THRESHOLD,
    }
