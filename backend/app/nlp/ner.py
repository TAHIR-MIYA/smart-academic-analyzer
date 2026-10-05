"""Named Entity Recognition with spaCy's pretrained statistical model (en_core_web_sm).

The model is a CNN trained on OntoNotes (news, web, broadcast text). It is not trained on
academic documents, so labels are sometimes wrong for technical terms - see Limitations.
"""
import logging
from collections import Counter, defaultdict
from functools import lru_cache

import spacy

from app.nlp.resources import SPACY_MODEL, get_spacy_model

logger = logging.getLogger(__name__)

CHUNK_CHARS = 50_000
TOP_PER_LABEL = 10


def _chunks(text: str, max_chars: int = CHUNK_CHARS) -> list[str]:
    """Split on paragraph boundaries into pieces of at most ~max_chars (keeps memory bounded)."""
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for para in text.split("\n\n"):
        if current and size + len(para) > max_chars:
            pieces.append("\n\n".join(current))
            current, size = [], 0
        # A single paragraph longer than the limit is split hard.
        while len(para) > max_chars:
            pieces.append(para[:max_chars])
            para = para[max_chars:]
        current.append(para)
        size += len(para) + 2
    if current:
        pieces.append("\n\n".join(current))
    return [p for p in pieces if p.strip()]


def extract_entities(text: str, top_per_label: int = TOP_PER_LABEL) -> dict:
    nlp = get_spacy_model()
    by_label: dict[str, Counter] = defaultdict(Counter)  # label -> Counter of lower-case key
    casing: dict[tuple[str, str], Counter] = defaultdict(Counter)  # (label, key) -> surface forms

    for doc in nlp.pipe(_chunks(text), disable=["parser", "lemmatizer"]):
        for ent in doc.ents:
            surface = " ".join(ent.text.split())
            if len(surface) < 2 or not any(ch.isalnum() for ch in surface):
                continue
            key = surface.lower()
            by_label[ent.label_][key] += 1
            casing[(ent.label_, key)][surface] += 1

    groups = []
    for label, counter in by_label.items():
        top = [
            {"text": casing[(label, key)].most_common(1)[0][0], "count": count}
            for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:top_per_label]
        ]
        groups.append(
            {
                "label": label,
                "description": spacy.explain(label) or label,
                "total": sum(counter.values()),
                "unique": len(counter),
                "top": top,
            }
        )
    groups.sort(key=lambda g: (-g["total"], g["label"]))
    return {
        "model": SPACY_MODEL,
        "total_entities": sum(g["total"] for g in groups),
        "unique_entities": sum(g["unique"] for g in groups),
        "groups": groups,
    }


@lru_cache(maxsize=16)
def extract_entities_cached(text: str) -> dict:
    return extract_entities(text)
