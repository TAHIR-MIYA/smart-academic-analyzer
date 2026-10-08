"""Checks that required NLP resources are installed, without crashing the app if they are not."""
import logging
from functools import lru_cache
from importlib.util import find_spec

logger = logging.getLogger(__name__)

SPACY_MODEL = "en_core_web_sm"
NLTK_RESOURCES = {"punkt_tab": "tokenizers/punkt_tab", "stopwords": "corpora/stopwords"}


@lru_cache(maxsize=1)
def spacy_load_problem() -> str | None:
    """None if spaCy imports; otherwise why not (not installed, or installed but blocked, e.g. by Windows
    Application Control refusing one of its compiled files). Cached so repeated health checks stay cheap."""
    if find_spec("spacy") is None:
        return "spaCy is not installed"
    try:
        import spacy  # noqa: F401
    except Exception as exc:  # ImportError, OSError from a blocked DLL, ...
        logger.warning("spaCy is installed but cannot be loaded: %s", exc)
        return f"spaCy is installed but cannot be loaded: {exc}"
    return None


def check_nlp_resources() -> dict:
    missing: list[str] = []
    fixes: list[str] = []
    spacy_problem = spacy_load_problem()
    model_ok = find_spec(SPACY_MODEL) is not None
    if spacy_problem:
        missing.append(spacy_problem)
        fixes.append("pip install spacy" if "not installed" in spacy_problem else "see TROUBLESHOOTING.md")
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
        "spacy_problem": spacy_problem,
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
        if spacy_load_problem():  # spaCy itself is unusable, not just the model
            raise NLPResourceError(
                "spaCy is installed but cannot be loaded on this computer, so lemmatisation and entity recognition are unavailable.",
                details={"cause": str(exc), "fix": "see TROUBLESHOOTING.md"},
            ) from exc
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
