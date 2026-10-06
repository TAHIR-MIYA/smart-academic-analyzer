"""Feature construction. Two text variants are compared during model selection."""
from sklearn.feature_extraction.text import TfidfVectorizer

from app.nlp.pipeline import PreprocessedDocument

# cleaned_text: stop words KEPT - genre cues such as 'all students', 'attempt any' live in function words.
# lemma_text  : the pipeline output (stop words removed, lemmatised).
FEATURE_SETS = {
    "cleaned_text": lambda doc: doc.cleaned_text,
    "lemma_text": lambda doc: doc.lemma_text,
}


def text_for(doc: PreprocessedDocument, feature_set: str) -> str:
    return FEATURE_SETS[feature_set](doc)


def make_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),   # words and word pairs
        min_df=2,             # ignore terms seen in only one training document
        sublinear_tf=True,    # 1 + log(tf): damps very frequent terms
        strip_accents="unicode",
    )
