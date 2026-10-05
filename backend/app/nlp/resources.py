"""Checks that required NLP resources are installed, without crashing the app if they are not."""
import logging
from importlib.util import find_spec

logger = logging.getLogger(__name__)

SPACY_MODEL = "en_core_web_sm"
NLTK_RESOURCES = {"punkt_tab": "tokenizers/punkt_tab", "stopwords": "corpora/stopwords"}


def check_nlp_resources() -> dict:
    missing: list[str] = []
    fixes: list[str] = []

    spacy_ok = find_spec("spacy") is not None
    model_ok = find_spec(SPACY_MODEL) is not None
    if not spacy_ok:
        missing.append("spacy")
        fixes.append("pip install spacy")
    elif not model_ok:
        missing.append(f"spacy model {SPACY_MODEL}")
        fixes.append(f"python -m spacy download {SPACY_MODEL}")

    nltk_data: dict[str, bool] = {}
    if find_spec("nltk") is None:
        missing.append("nltk")
        fixes.append("pip install nltk")
    else:
        import nltk

        for name, path in NLTK_RESOURCES.items():
            try:
                nltk.data.find(path)
                nltk_data[name] = True
            except LookupError:
                nltk_data[name] = False
                missing.append(f"nltk data '{name}'")
        if not all(nltk_data.values()):
            fixes.append("python -m scripts.setup_nlp")

    ready = not missing
    if not ready:
        logger.warning("NLP resources missing: %s", ", ".join(missing))
    return {
        "ready": ready,
        "spacy_model": SPACY_MODEL,
        "nltk_data": nltk_data,
        "missing": missing,
        "fix": sorted(set(fixes)),
    }


# ---------------------------------------------------------------------------
# Cached loaders. lru_cache does not cache exceptions, so installing a missing
# resource while the server runs is picked up on the next request.
# ---------------------------------------------------------------------------
from functools import lru_cache  # noqa: E402

from app.utils.errors import NLPResourceError  # noqa: E402

# Small additions to NLTK's English list: tokens that carry no topical meaning in papers.
EXTRA_STOPWORDS = frozenset(
    {"et", "al", "fig", "eg", "ie", "etc", "also", "may", "might", "would", "could", "shall", "us"}
)


@lru_cache(maxsize=1)
def get_spacy_model():
    """Load spaCy once (about 1-2 s) and share it across requests and modules."""
    try:
        import spacy

        nlp = spacy.load(SPACY_MODEL)
    except (ImportError, OSError) as exc:
        raise NLPResourceError(
            f"The spaCy model '{SPACY_MODEL}' is not installed.",
            details={"fix": "python -m scripts.setup_nlp"},
        ) from exc
    logger.info("Loaded spaCy model %s (pipeline: %s)", SPACY_MODEL, nlp.pipe_names)
    return nlp


@lru_cache(maxsize=1)
def get_stopwords() -> frozenset[str]:
    try:
        from nltk.corpus import stopwords

        words = set(stopwords.words("english"))
    except (ImportError, LookupError) as exc:
        raise NLPResourceError(
            "NLTK stop-word data is not installed.",
            details={"fix": "python -m scripts.setup_nlp"},
        ) from exc
    return frozenset(words | EXTRA_STOPWORDS)
