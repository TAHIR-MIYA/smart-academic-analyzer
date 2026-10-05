from pydantic import BaseModel, Field


class CleaningOperation(BaseModel):
    name: str
    description: str
    count: int


class CleaningReport(BaseModel):
    operations: list[CleaningOperation]
    original_characters: int
    cleaned_characters: int


class StageReport(BaseModel):
    name: str
    description: str
    token_count: int
    unique_count: int
    sample: list[str]


class TermCount(BaseModel):
    term: str
    count: int


class StemLemmaRow(BaseModel):
    word: str
    stem: str
    lemma: str
    pos: str


class PreprocessingResponse(BaseModel):
    document_id: int | None = None
    truncated: bool
    warnings: list[str]
    cleaning: CleaningReport
    stages: list[StageReport]
    removed_stopwords: list[TermCount]
    stopword_removal_rate: float
    top_terms: list[TermCount]
    stem_vs_lemma: list[StemLemmaRow]
    original_sample: str
    processed_sample: str
    sentences_sample: list[str]


class SentenceBucket(BaseModel):
    range: str
    count: int


class WordLengthBucket(BaseModel):
    length: str
    count: int


class TextStatistics(BaseModel):
    characters: int
    characters_no_spaces: int
    words: int
    unique_words: int
    sentences: int
    paragraphs: int
    avg_word_length: float
    avg_sentence_length: float
    longest_sentence_words: int
    reading_time_minutes: float
    sentence_length_distribution: list[SentenceBucket]
    word_length_distribution: list[WordLengthBucket]


class StatisticsResponse(BaseModel):
    document_id: int | None = None
    statistics: TextStatistics


class PreviewRequest(BaseModel):
    text: str = Field(min_length=20, max_length=50_000)


class PreviewResponse(BaseModel):
    preprocessing: PreprocessingResponse
    statistics: TextStatistics
    keywords: "KeywordsResult"
    ngrams: "NgramsResult"
    entities: "EntitiesResult"


# ---------------------------------------------------------------------------
# Module 3: keywords, n-grams, entities
# ---------------------------------------------------------------------------
class KeywordItem(BaseModel):
    term: str
    count: int
    tf: float
    idf: float
    score: float
    relative_score: float


class KeywordsResult(BaseModel):
    idf_mode: str
    idf_description: str
    idf_n_documents: int
    pos_filter: list[str]
    formula: str
    total_terms: int
    vocabulary_size: int
    keywords: list[KeywordItem]


class KeywordsResponse(KeywordsResult):
    document_id: int | None = None


class NgramItem(BaseModel):
    ngram: str
    count: int


class NgramLevel(BaseModel):
    n: int
    label: str
    total: int
    distinct: int
    top: list[NgramItem]


class NgramsResult(BaseModel):
    levels: list[NgramLevel]
    note: str


class NgramsResponse(NgramsResult):
    document_id: int | None = None


class EntityItem(BaseModel):
    text: str
    count: int


class EntityGroup(BaseModel):
    label: str
    description: str
    total: int
    unique: int
    top: list[EntityItem]


class EntitiesResult(BaseModel):
    model: str
    total_entities: int
    unique_entities: int
    groups: list[EntityGroup]


class EntitiesResponse(EntitiesResult):
    document_id: int | None = None


PreviewResponse.model_rebuild()
