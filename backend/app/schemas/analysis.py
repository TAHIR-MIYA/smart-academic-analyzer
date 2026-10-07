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
    classification: "ClassificationResult | None" = None
    classification_error: str | None = None


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



# ---------------------------------------------------------------------------
# Module 4: classification
# ---------------------------------------------------------------------------
class ClassProbability(BaseModel):
    label: str
    display_name: str
    probability: float


class ExplanationTerm(BaseModel):
    term: str
    contribution: float


class ModelInfo(BaseModel):
    classifier: str
    feature_set: str
    trained_at: str
    n_training_documents: int


class ClassificationResult(BaseModel):
    label: str
    display_name: str
    confidence: float
    is_confident: bool
    confidence_threshold: float
    probabilities: list[ClassProbability]
    explanation: list[ExplanationTerm]
    model: ModelInfo
    disclaimer: str


class ClassificationResponse(ClassificationResult):
    document_id: int | None = None


# ---------------------------------------------------------------------------
# Module 5: summary, readability, vocabulary, similarity
# ---------------------------------------------------------------------------
class SummarySentence(BaseModel):
    index: int
    text: str
    score: float
    relative_score: float
    words: int


class SentenceScore(BaseModel):
    index: int
    score: float
    selected: bool
    words: int


class SummaryResult(BaseModel):
    method: str
    idf_mode: str
    sentences_in_document: int
    sentences_eligible: int
    sentences_selected: int
    compression_ratio: float
    summary: list[SummarySentence]
    summary_text: str
    sentence_scores: list[SentenceScore]
    parameters: dict[str, float | int]
    note: str | None = None


class SummaryResponse(SummaryResult):
    document_id: int | None = None


class ReadabilityScore(BaseModel):
    name: str
    value: float
    interpretation: str
    formula: str


class ReadabilityResult(BaseModel):
    reliable: bool
    warning: str | None = None
    counts: dict[str, int]
    averages: dict[str, float]
    scores: list[ReadabilityScore]
    reading_level: str
    note: str


class ReadabilityResponse(ReadabilityResult):
    document_id: int | None = None


class VocabularyMeasure(BaseModel):
    key: str
    name: str
    value: float
    description: str


class SpectrumBucket(BaseModel):
    occurrences: str
    count: int


class ZipfPoint(BaseModel):
    rank: int
    word: str
    count: int


class VocabularyResult(BaseModel):
    reliable: bool
    warning: str | None = None
    tokens: int
    types: int
    lemma_types: int
    hapax_count: int
    dis_legomena_count: int
    measures: list[VocabularyMeasure]
    frequency_spectrum: list[SpectrumBucket]
    zipf: list[ZipfPoint]


class VocabularyResponse(VocabularyResult):
    document_id: int | None = None


class TopicScore(BaseModel):
    topic: str
    similarity: float


class SharedTerm(BaseModel):
    term: str
    weight: float


class TopicSimilarityResult(BaseModel):
    method: str
    topics_compared: int
    best_topic: str | None
    best_similarity: float
    is_weak_match: bool
    weak_match_threshold: float
    similarities: list[TopicScore]
    matched_terms: list[SharedTerm]
    note: str | None = None


class TopicSimilarityResponse(TopicSimilarityResult):
    document_id: int | None = None


class SentencePair(BaseModel):
    similarity: float
    index_a: int
    sentence_a: str
    index_b: int
    sentence_b: str


class CompareRequest(BaseModel):
    document_a: int
    document_b: int


class DocumentRef(BaseModel):
    id: int
    filename: str


class ComparisonResponse(BaseModel):
    document_a: DocumentRef
    document_b: DocumentRef
    method: str
    cosine_similarity: float
    vocabulary_overlap_jaccard: float
    interpretation: str
    interpretation_note: str
    shared_terms: list[SharedTerm]
    similar_sentence_pairs: list[SentencePair]
    pair_threshold: float
    note: str = (
        "Cosine similarity measures shared wording, not shared subject: two documents about the same "
        "subject but with different content can score low."
    )


class PreviewFull(PreviewResponse):
    summary: SummaryResult | None = None
    readability: ReadabilityResult | None = None
    vocabulary: VocabularyResult | None = None
    topic_similarity: TopicSimilarityResult | None = None
    topic_similarity_error: str | None = None


PreviewFull.model_rebuild()


# ---------------------------------------------------------------------------
# Module 6: saved analysis + dashboard
# ---------------------------------------------------------------------------
class DocumentInfo(BaseModel):
    id: int
    filename: str
    file_type: str
    size_bytes: int
    page_count: int | None
    char_count: int
    word_count: int
    uploaded_at: str
    extraction_warnings: list[str]


class FullAnalysisResponse(BaseModel):
    schema_version: int
    generated_at: str
    app_version: str
    document: DocumentInfo
    preprocessing: PreprocessingResponse
    statistics: TextStatistics
    keywords: KeywordsResult
    ngrams: NgramsResult
    entities: EntitiesResult
    classification: ClassificationResult | None = None
    classification_error: str | None = None
    summary: SummaryResult | None = None
    summary_error: str | None = None
    readability: ReadabilityResult
    vocabulary: VocabularyResult
    topic_similarity: TopicSimilarityResult | None = None
    topic_similarity_error: str | None = None


class ClassCount(BaseModel):
    label: str
    display_name: str
    count: int


class DashboardModelEval(BaseModel):
    name: str
    description: str
    n: int
    accuracy: float
    macro_f1: float


class DashboardModel(BaseModel):
    trained: bool
    trained_at: str | None
    classifier: str | None
    feature_set: str | None
    evaluations: list[DashboardModelEval]
    note: str


class RecentDocument(BaseModel):
    id: int
    filename: str
    file_type: str
    word_count: int
    analyzed: bool
    created_at: str


class DashboardResponse(BaseModel):
    total_documents: int
    analyzed_documents: int
    total_words: int
    by_file_type: dict[str, int]
    class_distribution: list[ClassCount]
    uncertain_predictions: int
    recent_documents: list[RecentDocument]
    model: DashboardModel
