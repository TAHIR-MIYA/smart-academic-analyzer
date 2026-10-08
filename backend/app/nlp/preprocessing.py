"""Steps 3-5: stop-word removal, lemmatisation (spaCy) and stemming (NLTK, comparison only)."""
import logging

from nltk.stem import PorterStemmer

from app.nlp.resources import get_spacy_model

logger = logging.getLogger(__name__)

_stemmer = PorterStemmer()
# Sentences per spaCy Doc: bounds memory on long documents.
_CHUNK_SENTENCES = 200
_SKIPPED_COMPONENTS = {"parser", "ner"}  # not needed for lemmas; skipping them saves time


def stem(word: str) -> str:
    """Porter stemmer: rule-based suffix stripping; the result need not be a real word."""
    return _stemmer.stem(word.lower())


def lemmatize_sentences(sentence_tokens: list[list[str]]) -> list[tuple[str, str]]:
    """Return (lemma, coarse POS tag) for every token, in the same order as the input.

    The tokens come from NLTK; spaCy is used only to tag and lemmatise them. The POS tag
    is needed because the lemma of 'saw' depends on whether it is a noun or a verb, and
    POS tagging needs the whole sentence (including stop words) as context.
    """
    nlp = get_spacy_model()  # raises NLPResourceError (HTTP 503) if spaCy cannot be used
    from spacy.tokens import Doc  # imported here so a spaCy that cannot load never stops the app from starting

    pipeline = [proc for name, proc in nlp.pipeline if name not in _SKIPPED_COMPONENTS]
    results: list[tuple[str, str]] = []

    for start in range(0, len(sentence_tokens), _CHUNK_SENTENCES):
        chunk = sentence_tokens[start : start + _CHUNK_SENTENCES]
        words: list[str] = []
        sent_starts: list[bool] = []
        for sentence in chunk:
            for i, token in enumerate(sentence):
                words.append(token)
                sent_starts.append(i == 0)
        if not words:
            continue
        doc = Doc(nlp.vocab, words=words, sent_starts=sent_starts)
        for proc in pipeline:  # tok2vec -> tagger -> attribute_ruler -> lemmatizer
            doc = proc(doc)
        results.extend((tok.lemma_ or tok.text, tok.pos_) for tok in doc)

    return results
