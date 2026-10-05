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
