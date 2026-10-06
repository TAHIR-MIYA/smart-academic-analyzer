"""Orchestrates the preprocessing pipeline and builds the before/after report.

clean -> sentence split -> word tokenise -> (POS-aware) lemmatise ->
keep word tokens -> case-fold -> remove stop words -> lemmas
"""
import logging
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

from app.nlp import cleaning, tokenization
from app.nlp.preprocessing import lemmatize_sentences, stem
from app.nlp.resources import get_stopwords
from app.nlp.text_stats import compute_statistics
from app.utils.errors import EmptyDocumentError

logger = logging.getLogger(__name__)

SAMPLE_SIZE = 25


@dataclass(frozen=True)
class TokenRecord:
    surface: str  # token exactly as written
    lower: str  # case-folded
    lemma: str  # dictionary form (lower-case)
    pos: str  # coarse part of speech from spaCy
    is_stopword: bool
    sentence_index: int  # which sentence the token came from (n-grams must not cross sentences)


@dataclass
class PreprocessedDocument:
    raw_text: str
    cleaned_text: str
    cleaning: cleaning.CleaningResult
    sentences: list[str]
    raw_tokens: list[str]
    records: list[TokenRecord]
    stats: dict
    truncated: bool
    sentence_tokens: list[list[str]] = field(default_factory=list)  # NLTK tokens per sentence

    # ---- views used by later modules (TF-IDF, n-grams, summariser, ...) ----
    @property
    def content_tokens(self) -> list[str]:
        """Case-folded content words (stop words removed) - before lemmatisation."""
        return [r.lower for r in self.records if not r.is_stopword]

    @property
    def content_lemmas(self) -> list[str]:
        """Final output of the pipeline: lemmas of content words."""
        return [r.lemma for r in self.records if not r.is_stopword]

    @property
    def lemma_text(self) -> str:
        return " ".join(self.content_lemmas)

    def lemma_texts_by_sentence(self) -> list[str]:
        """One string of content lemmas per sentence, aligned with self.sentences ('' if none)."""
        groups: list[list[str]] = [[] for _ in self.sentences]
        for r in self.records:
            if not r.is_stopword:
                groups[r.sentence_index].append(r.lemma)
        return [" ".join(g) for g in groups]

    def content_by_sentence(self, allowed_pos: tuple[str, ...] | None = None) -> list[list[str]]:
        """Content lemmas grouped per sentence (sentences without content words are omitted)."""
        groups: dict[int, list[str]] = {}
        for r in self.records:
            if r.is_stopword or (allowed_pos and r.pos not in allowed_pos):
                continue
            groups.setdefault(r.sentence_index, []).append(r.lemma)
        return [groups[k] for k in sorted(groups)]

    # ---- API reports ----
    def statistics(self) -> dict:
        return self.stats

    def preprocessing_report(self) -> dict:
        words = [r.surface for r in self.records]
        lowered = [r.lower for r in self.records]
        content = self.content_tokens
        lemmas = self.content_lemmas

        def stage(name: str, description: str, tokens: list[str]) -> dict:
            return {
                "name": name,
                "description": description,
                "token_count": len(tokens),
                "unique_count": len(set(tokens)),
                "sample": tokens[:SAMPLE_SIZE],
            }

        stages = [
            stage("1. Tokenisation", "NLTK word_tokenize: words, numbers and punctuation", self.raw_tokens),
            stage("2. Word filtering", "Keep alphabetic tokens (length >= 2); drop punctuation and numbers", words),
            stage("3. Case folding", "Lower-case every token so 'The' and 'the' count as one type", lowered),
            stage("4. Stop-word removal", "Remove high-frequency function words (NLTK list + a few extras)", content),
            stage("5. Lemmatisation", "Replace each word by its dictionary form using spaCy (POS-aware)", lemmas),
        ]

        removed = Counter(r.lower for r in self.records if r.is_stopword)
        n_removed = sum(removed.values())

        # Stemming vs lemmatisation: list frequent words where the two approaches disagree.
        surface_counts = Counter(r.lower for r in self.records if not r.is_stopword)
        first_seen: dict[str, TokenRecord] = {}
        for r in self.records:
            first_seen.setdefault(r.lower, r)
        comparison = []
        for word, _ in surface_counts.most_common():
            rec = first_seen[word]
            stemmed = stem(word)
            if stemmed != rec.lemma:  # the interesting cases: stem and lemma disagree
                comparison.append({"word": word, "stem": stemmed, "lemma": rec.lemma, "pos": rec.pos})
            if len(comparison) >= 15:
                break

        warnings = []
        if self.truncated:
            warnings.append("The document was very long; only the first part was analysed.")

        return {
            "truncated": self.truncated,
            "warnings": warnings,
            "cleaning": {
                "operations": self.cleaning.operations,
                "original_characters": self.cleaning.original_length,
                "cleaned_characters": self.cleaning.cleaned_length,
            },
            "stages": stages,
            "removed_stopwords": [{"term": t, "count": c} for t, c in removed.most_common(10)],
            "stopword_removal_rate": round(n_removed / len(self.records), 4) if self.records else 0.0,
            "top_terms": [{"term": t, "count": c} for t, c in Counter(lemmas).most_common(20)],
            "stem_vs_lemma": comparison,
            "original_sample": self.cleaned_text[:400],
            "processed_sample": " ".join(lemmas[:60]),
            "sentences_sample": self.sentences[:5],
        }


def run_pipeline(text: str, max_chars: int = 500_000) -> PreprocessedDocument:
    truncated = len(text) > max_chars
    if truncated:
        logger.warning("Text truncated from %d to %d characters", len(text), max_chars)
        text = text[:max_chars]

    cleaned = cleaning.clean_text(text)
    sentences = tokenization.split_sentences(cleaned.text)
    sentence_tokens = [tokenization.tokenize_words(s) for s in sentences]
    raw_tokens = [t for toks in sentence_tokens for t in toks]

    lemma_pos = lemmatize_sentences(sentence_tokens)
    if len(lemma_pos) != len(raw_tokens):  # defensive: alignment is essential
        raise RuntimeError("Lemmatiser output is not aligned with the tokens")

    token_sentence = [i for i, toks in enumerate(sentence_tokens) for _ in toks]
    stopwords = get_stopwords()
    records: list[TokenRecord] = []
    for token, (lemma, pos), sent_idx in zip(raw_tokens, lemma_pos, token_sentence):
        if not tokenization.is_word_token(token):
            continue
        lower = token.lower()
        records.append(TokenRecord(token, lower, lemma.lower(), pos, lower in stopwords, sent_idx))

    if not any(not r.is_stopword for r in records):
        raise EmptyDocumentError("The document contains no analysable words after cleaning.")

    stats = compute_statistics(text, cleaned.text, sentences, sentence_tokens)
    logger.info(
        "Pipeline: %d sentences, %d tokens, %d content lemmas",
        len(sentences), len(raw_tokens), sum(1 for r in records if not r.is_stopword),
    )
    return PreprocessedDocument(text, cleaned.text, cleaned, sentences, raw_tokens, records, stats, truncated, sentence_tokens)


@lru_cache(maxsize=16)
def run_pipeline_cached(text: str, max_chars: int = 500_000) -> PreprocessedDocument:
    """Same as run_pipeline, memoised so the Preprocessing and Statistics pages share one run."""
    return run_pipeline(text, max_chars)
