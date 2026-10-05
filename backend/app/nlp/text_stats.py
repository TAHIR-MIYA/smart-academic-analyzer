"""Basic document statistics: characters, words, sentences, paragraphs and distributions."""
import re
from collections import Counter

from app.nlp.tokenization import has_word_char, is_word_token

WORDS_PER_MINUTE = 200  # average silent reading speed for adults


def _bucket_sentence_lengths(lengths: list[int]) -> list[dict]:
    edges = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50)]
    buckets = [
        {"range": f"{lo}-{hi}", "count": sum(1 for n in lengths if lo <= n <= hi)} for lo, hi in edges
    ]
    buckets.append({"range": "51+", "count": sum(1 for n in lengths if n > 50)})
    return buckets


def _bucket_word_lengths(word_lengths: list[int], max_len: int = 12) -> list[dict]:
    counts = Counter(min(n, max_len) for n in word_lengths)
    return [
        {"length": f"{n}+" if n == max_len else str(n), "count": counts.get(n, 0)}
        for n in range(2, max_len + 1)
    ]


def compute_statistics(
    raw_text: str, cleaned_text: str, sentences: list[str], sentence_tokens: list[list[str]]
) -> dict:
    sentence_word_counts = [sum(1 for t in toks if has_word_char(t)) for toks in sentence_tokens]
    all_tokens = [t for toks in sentence_tokens for t in toks]
    word_tokens = [t.lower() for t in all_tokens if has_word_char(t)]
    alpha_words = [t for t in all_tokens if is_word_token(t)]

    total_words = len(word_tokens)
    n_sentences = len(sentences)
    paragraphs = [p for p in re.split(r"\n\s*\n", cleaned_text) if p.strip()]
    nonempty = [n for n in sentence_word_counts if n > 0]

    return {
        "characters": len(raw_text),
        "characters_no_spaces": len(re.sub(r"\s", "", raw_text)),
        "words": total_words,
        "unique_words": len(set(word_tokens)),
        "sentences": n_sentences,
        "paragraphs": len(paragraphs),
        "avg_word_length": round(sum(len(w) for w in alpha_words) / len(alpha_words), 2)
        if alpha_words
        else 0.0,
        "avg_sentence_length": round(total_words / n_sentences, 2) if n_sentences else 0.0,
        "longest_sentence_words": max(nonempty) if nonempty else 0,
        "reading_time_minutes": round(total_words / WORDS_PER_MINUTE, 1),
        "sentence_length_distribution": _bucket_sentence_lengths(nonempty),
        "word_length_distribution": _bucket_word_lengths([len(w) for w in alpha_words]),
    }
