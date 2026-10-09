# Viva preparation: Smart Academic Document Analyzer

Seventy-nine questions with short answers, written for **this** implementation. Where an answer quotes a number, it comes from
the reference training run described below; **replace those numbers with your own** (run `python -m app.ml.train` and read
`backend/app/ml/artifacts/metrics.json` or the Dashboard) and be ready to say where each one comes from.

## Your numbers (fill in before the viva)

| Quantity | Reference run | Your run |
|---|---|---|
| Documents in the training set (60 per class) | 300 (240 train, 60 test) | |
| Cross-validated macro-F1, each of the 6 candidates | 1.00 for all | |
| Held-out test split: accuracy, macro-F1 | 1.00, 1.00 | |
| Nearest-training-document similarity of the test split | 0.62 | |
| Independent challenge set (25 documents): accuracy, macro-F1 | 0.88, 0.88 | |
| Nearest-training-document similarity of the challenge set | 0.28 | |
| Documents misclassified in the challenge set | 3 | |
| Real-world set (`datasets/real/`) | not evaluated | |

Reference run: Python 3.12, scikit-learn 1.8, spaCy 3.8, random seed 42.

## The five sentences to say first

1. "The system is a classical NLP pipeline: every stage is a technique I can explain and show on screen."
2. "The classifier is trained on **synthetic** documents, so its test-split score is optimistic."
3. "I therefore also evaluated it on an independent, hand-written challenge set, where accuracy was lower."
4. "Only documents from real classes, which I can add under `datasets/real/`, give a true real-world estimate."
5. "Prediction confidence is not accuracy, and the Classification tab keeps the two apart."

---

## A. The project as a whole

**1. What is NLP, and how does this project use it?**
Natural Language Processing is the computational processing of human language. The project applies it to academic
documents: it extracts and cleans text, splits it into sentences and words, reduces words to base forms, weights terms with
TF-IDF, finds named entities, classifies the document type, summarises it, and measures similarity, readability and
vocabulary.

**2. State the problem in one sentence.**
Students and staff handle many documents of different kinds, and the project identifies the type of a document, extracts
its key information, summarises it and compares it automatically, with every step explained.

**3. Walk through the pipeline in order.**
Upload, validate, extract text, clean, split into sentences, tokenise, lemmatise, keep word tokens, case-fold, remove
stop words, TF-IDF keywords, n-grams, named entities, classification, summary, similarity, readability and vocabulary,
store, display or export.

**4. Why classical NLP and machine learning instead of deep learning or a large language model?**
The brief asks for something that runs locally on a student laptop with no GPU or paid API, and for every technique to be
explainable. Linear models on TF-IDF train in seconds, can be inspected (their weights show what they use), need little
data and keep documents private. The price is that they capture wording, not deep meaning.

**5. Describe the architecture.**
A React frontend calls a FastAPI backend over REST. Routers only handle HTTP; services orchestrate; plain functions in
`app/nlp` and `app/ml` do the language work; SQLAlchemy stores documents and saved analyses in SQLite. This separation
makes each technique small and testable.

**6. Which parts did you write and which come from libraries?**
Written here: validation, cleaning rules, heading handling, TF-IDF scoring and the reference IDF, n-gram and entity
aggregation, the summariser, the readability formulas, the vocabulary measures, similarity and comparison, the dataset
generator, the evaluation protocol, the API and the interface. Libraries: NLTK (tokenisers, stop-word list, Porter
stemmer), spaCy (tagger, lemmatiser, NER), scikit-learn (vectoriser, classifiers, metrics), PyMuPDF and python-docx
(file reading), ReportLab and Matplotlib (PDF).

**7. Why FastAPI and React?**
FastAPI gives typed request and response models, automatic interactive documentation at `/docs`, and keeps all NLP in
Python. React with Vite gives a component-based interface that is easy to test; Recharts draws the charts.

## B. Extraction and cleaning

**8. Why do you check file content and not just the extension?**
A renamed file would otherwise pass. The server checks the extension, size, emptiness and the file signature: `%PDF-` for
PDF, a ZIP header for DOCX, and no binary bytes for TXT. File names are sanitised so paths such as `../../x` are stripped.

**9. What happens with a scanned PDF?**
PyMuPDF finds no text layer, so the upload is rejected with `empty_document` and a message that OCR is not supported. OCR
(for example Tesseract) is listed as future work.

**10. What does text cleaning do, and why?**
Eleven reported steps: remove soft hyphens and zero-width characters, normalise Unicode, standardise quotes and dashes,
remove control characters, rejoin words hyphenated across lines, remove URLs and e-mail addresses, remove page-number
lines, remove repeated headers and footers, join lines wrapped mid-sentence, and collapse whitespace. PDFs extract with
these artefacts, and they would otherwise become false "words".

**11. What is NFKC normalisation?**
A Unicode normal form (compatibility composition) that maps compatibility characters to plain equivalents. PDFs often
contain the ligature "ﬁ" as one character; NFKC turns it into "fi" so that "financial" is one word.

**12. How reliable is the header and footer removal?**
It is a heuristic: a multi-word line of 12 or more characters with no end punctuation that occurs three or more times is
treated as a running header. It works on repeated page headers but can wrongly remove a legitimate repeated line. That
limitation is stated in the report.

**13. How do you read text files with different encodings?**
UTF-8 (with or without a byte-order mark) first, UTF-16 when its mark is present, and Windows-1252 as a fallback with a
warning.

## C. Tokenisation

**14. What is tokenisation, and what is the difference between sentence and word tokenisation?**
Tokenisation splits text into units. Sentence tokenisation finds sentence boundaries; word tokenisation splits a sentence
into words and punctuation. Every later step (counting, stop words, lemmas) works on these units.

**15. How does the Punkt sentence tokeniser decide where a sentence ends?**
Punkt is unsupervised: it learns from text which tokens are abbreviations ("Dr.", "e.g."), common collocations and
frequent sentence starters, then judges whether each full stop is a boundary. That is why "Dr. Smith teaches NLP." is one
sentence.

**16. Why NLTK tokens but spaCy lemmas? Do they not disagree about word boundaries?**
They would if each tokenised separately. The project tokenises once with NLTK and builds a spaCy document from exactly those
words, so spaCy only tags and lemmatises them and the two stay aligned.

**17. What counts as a word in your pipeline?**
An alphabetic token of two or more letters, possibly with an inner hyphen or apostrophe. Numbers, punctuation and one-letter
tokens are dropped, and the negation clitic "n't" (from "doesn't") is not a word.

**18. Why did you add heading handling to sentence splitting?**
A heading on its own line has no full stop, so the splitter glued it to the next sentence ("PROBLEM STATEMENT The existing
system..."). Short, title-like lines standing between sentences now get a full stop first. A side effect is that headings
count as short sentences.

## D. Stop words, stemming and lemmatisation

**19. What are stop words, and why remove them?**
Very frequent function words such as "the" and "of". They carry little topical meaning, so for keywords, n-grams and
summarisation removing them lets content words stand out. The list is NLTK's English list plus a few extras such as "et",
"al" and "fig".

**20. If stop words are useless, why does the classifier keep them?**
For document **type** the function words are the signal: "all students" and "hereby informed" mark a notice, "attempt any"
a question paper. Removing them would discard genre cues. Honest caveat: cross-validation could not separate the two
variants on this data, so I cannot claim an empirical advantage.

**21. Explain stemming versus lemmatisation.**
A stemmer cuts endings by rules, so the result may not be a word: Porter turns "studying" into "studi". A lemmatiser returns
the dictionary form using the word's part of speech: "studying" becomes "study". The Preprocessing tab shows this contrast
for real words from the document.

**22. Why does the pipeline use lemmatisation?**
Its output is readable, and it merges inflected forms correctly ("models", "model"). It costs more time, because it needs
part-of-speech tags, but the benefit is cleaner keywords.

**23. How does spaCy lemmatise?**
The English lemmatiser is rule based: it looks up lemma rules and exception tables keyed by the word's part of speech, which
the tagger provides. That is why the tagger must run first.

**24. Why is part of speech needed for lemmatising?**
The same spelling can have different lemmas: "saw" is "see" as a verb and "saw" as a noun; "meeting" is a noun or a form of
"meet". Tagging needs the whole sentence, which is why stop words are tagged and lemmatised too and only then removed.

## E. TF-IDF

**25. Explain TF-IDF and give the formula you implemented.**
It scores a term high if it is frequent in this document (TF) but not present in most comparison documents (IDF). Here
`tf = count / total terms`, `idf = ln((1 + N) / (1 + df)) + 1`, `score = tf x idf`. A test checks this IDF equals
scikit-learn's smoothed IDF.

**26. Why the logarithm, and why add 1 twice?**
The logarithm stops very rare terms from dominating. The `1 +` terms smooth the ratio so a term seen in no document does not
divide by zero, and the final `+ 1` keeps weights positive so even a term present in every document keeps some weight.

**27. A single document has no collection. Where does IDF come from?**
Three modes, always reported on the Keywords tab. After training, document frequencies from the training set are used
(`reference_corpus`). Otherwise each sentence is treated as a document (`document_sentences`, needs at least five
sentences). For very short documents only term frequency is used (`term_frequency`).

**28. Why do keywords use only nouns, proper nouns and adjectives?**
Verbs such as "use" and "show" are frequent but rarely topical. The filter is stated in every response.

**29. What are the limits of TF-IDF?**
It is a bag-of-words model: no word order, no synonyms, no meaning. On a short document most terms occur once, so scores
tie, as seen on a one-page exam paper.

**30. TF-IDF in the classifier differs from the keyword one. How?**
The classifier uses scikit-learn's `TfidfVectorizer` with word unigrams and bigrams, `min_df=2`, sublinear term frequency
(`1 + log tf`) and L2 normalisation, so every document is a unit-length vector.

## F. N-grams

**31. What are n-grams and why are they useful?**
Sequences of n consecutive words. Bigrams and trigrams capture phrases such as "natural language processing" that single
words cannot. The cost is sparsity: most longer n-grams occur once.

**32. How exactly do you build them, and what is the caveat?**
From lemmatised content words, within a sentence only, using NLTK's `ngrams`. Because stop words are removed first, two words
separated by a function word in the original can become neighbours. This surfaces topical phrases but is a simplification.

**33. Why does the classifier use unigrams and bigrams?**
Phrases such as "maximum marks" and "hereby informed" are far more distinctive than their single words.

## G. Named entity recognition

**34. What is NER and how does spaCy do it?**
It locates names of people, organisations, places, dates and so on, and labels them. spaCy's small English model combines a
convolutional token encoder with a transition-based tagger and was trained on the OntoNotes corpus of news and web text.

**35. How accurate is it on academic documents?**
I have not measured it, and I do not claim a figure. I did observe errors: on an Engineering Physics paper "Max" and "Q.1
Attempt" were labelled PERSON, "Write Bragg's" a place and "2 marks" money. The model was trained on different text.

**36. How would you improve it?**
Fine-tune on annotated academic text, add domain labels such as course or department, or add rules with spaCy's
`EntityRuler` for patterns like "Q.1".

**37. How are entities counted?**
Case-insensitively per label, showing the most common spelling, grouped by label with counts and top examples.

## H. Classification

**38. Why logistic regression?**
It outputs probabilities, is linear (so its weights can be read), and performs well on sparse TF-IDF features. I compared it
with a linear SVM and Naive Bayes.

**39. How does it produce probabilities for five classes?**
Multinomial logistic regression computes one linear score per class and passes them through softmax so they sum to one.
`C=10` sets a weak regularisation strength.

**40. Why is the SVM calibrated?**
`LinearSVC` finds a maximum-margin boundary but gives no probabilities. Wrapping it in `CalibratedClassifierCV` (sigmoid
calibration) adds them so all candidates can be compared and used the same way.

**41. How does Naive Bayes work?**
It applies Bayes' theorem assuming words are independent given the class, and multiplies word likelihoods with additive
smoothing (`alpha = 0.1`) so unseen words do not zero the probability.

**42. Explain your train/test split.**
The generated data is split 80/20, stratified so each class keeps its share, with a fixed seed. The test part is used once,
after the model is chosen. Using it for choices would make its score optimistic.

**43. What is cross-validation and how did you use it?**
Training data is divided into five stratified folds; each fold is held out in turn and the model is trained on the rest. The
average macro-F1 over folds compares candidates. It runs on the **training part only**, never on the test part.

**44. Define precision, recall, F1 and macro averaging.**
For a class: precision = TP / (TP + FP), the share of predictions of that class that were right; recall = TP / (TP + FN), the
share of true members found; F1 = 2PR / (P + R), their harmonic mean. Macro averaging takes the plain mean over classes, so
each class counts equally.

**45. How do you read the confusion matrix?**
Rows are the true class, columns the predicted class, so the diagonal is correct and off-diagonal cells are errors. In the
challenge set one question paper was predicted as study material.

**46. What is "prediction confidence"? Is it accuracy?**
It is the model's highest class probability for this one document. It is not accuracy and need not be calibrated. Accuracy
is a measured rate over many documents. Predictions below 0.5 are flagged uncertain.

**47. Why is the test-split accuracy 100%, and is that believable?**
It is believable and not impressive. The data comes from templates, so test documents resemble training documents; the
measured average similarity to the nearest training document is about 0.62. A score on data this similar to training says
little about real performance.

**48. All six candidate models had cross-validated F1 of 1.00. What does that mean?**
Cross-validation could not tell the models apart on this data, so logistic regression was chosen by a fixed tie rule
(within 0.005 of the best, first in a stated order), not by merit. The Classification tab says so.

**49. What does 88% on the challenge set tell you?**
It is more independent evidence: the documents are hand-written in different layouts and their average similarity to
training is only about 0.28. But there are only 25, so each error costs four points, and the assistant that helped build the
project wrote them after seeing the generator, so they are not real-world data.

**50. How did you guard against data leakage?**
A fixed split, model selection on the training part only, the test part scored once, identical documents rejected at
generation, and `mean_max_similarity_to_train` reported to quantify resemblance. One honest note: the reference IDF used for
keywords is built from all 300 documents; it is unsupervised and not used by the classifier.

**51. What did the strongest features reveal?**
Genuine cues ("hereby informed", "maximum marks", "assignment") and generator artefacts ("in practice", "step") for study
material. The second kind will not appear in real study notes, which is a sign of over-fitting to the templates.

**52. What are overfitting and underfitting? Is the model overfitted?**
Overfitting is memorising training data so that new data performs worse; underfitting is being too simple to learn the
pattern. Training accuracy of 1.0 shows only that the model fits what it saw. The drop on the challenge set and the template
phrases among its features suggest some over-fitting to the synthetic style.

**53. How do you explain a single prediction?**
For logistic regression, each term's contribution is its learned weight for the predicted class times its TF-IDF value in the
document. The largest positive contributions are shown.

**54. A document that is none of the five types: what happens?**
It is forced into one of the five, and a low confidence is the only warning. An "Other" class is future work.

**55. What would you do with 1000 real labelled documents?**
Split properly into train, validation and test, tune hyper-parameters by cross-validation, do error analysis on the
mistakes, and calibrate the probabilities.

## I. Summarisation

**56. Extractive versus abstractive summarisation?**
Extractive selects existing sentences; abstractive writes new ones. This project is extractive, so nothing is invented and
every summary sentence is traceable to the source.

**57. Describe your summarisation algorithm.**
Each sentence scores the sum of the TF-IDF weights of its distinct content words divided by the square root of their number;
the first usable sentence gets a 25% bonus; a sentence whose set of content words overlaps one already chosen by more than 0.6
(Jaccard overlap) is skipped; sentences under 5 or over 60 words are ignored; the chosen sentences appear in original order. This follows the
classic idea of ranking sentences by word significance (Luhn, 1958).

**58. Why divide by the square root of the length?**
Dividing by the length favours very short sentences; not dividing favours very long ones. The square root is a compromise and
is my design choice, not a published constant.

**59. How did you evaluate the summaries?**
I did not score them automatically: ROUGE needs human-written reference summaries, which I do not have. Quality was judged by
reading examples, and the interface says so.

## J. Similarity

**60. What is cosine similarity and why not Euclidean distance?**
It is the cosine of the angle between two vectors, `a . b / (|a| |b|)`. It compares direction, not length, so a long document
and a short one on the same topic score as similar; Euclidean distance would punish the difference in length.

**61. How does document-to-topic similarity work?**
There are ten topic profiles (plain text files in `datasets/topics`). The document and the profiles are vectorised with
TF-IDF over the profiles plus the document, and the cosine to each profile is shown. If the best score is below 0.10 the page
reports "no strong match". The threshold is a rule of thumb.

**62. What is the weakness of document-to-document similarity?**
It measures shared wording, not shared subject. DBMS lecture notes and a DBMS assignment scored only 0.06 against each other.
The comparison therefore also lists near-copied sentence pairs (cosine of at least 0.5), which is what matters for copying.

**63. How would you capture meaning instead of wording?**
Use sentence or document embeddings from a pretrained transformer and compare those vectors; this is future work because of
the laptop and no-download constraints.

## K. Readability and vocabulary

**64. State the Flesch Reading Ease formula and what it means.**
`206.835 - 1.015 x (words / sentences) - 84.6 x (syllables / words)`. Higher means easier: 60 to 70 is plain English, 30 to 50
is college level. The project also computes Flesch-Kincaid grade, Gunning Fog and ARI.

**65. How do you count syllables and how good is it?**
By counting vowel groups with rules for silent endings. On a test list of twenty words it got nineteen right; it fails on words
like "science". Scores are therefore approximate, and short or non-prose documents are flagged unreliable.

**66. Why is plain type-token ratio a poor measure, and what do you use instead?**
TTR falls as a text gets longer, so documents of different length cannot be compared. The project also reports Root TTR,
Corrected TTR and MATTR (the average TTR over a sliding window of 50 words), which is largely length independent. It also
shows Zipf's law: word frequency falls roughly in proportion to rank.

## L. Engineering

**67. How do you handle errors?**
Every failure has a stable code and message: scanned PDF (422), password-protected PDF (422), unsupported type (415), too
large (413), missing model (503), missing language data (503). Optional sections such as classification fail softly: that
section is empty with its reason and the rest of the analysis is still produced. Even a spaCy that Windows blocks does not
stop the application from starting.

**68. Why SQLite and SQLAlchemy, and how would you move to MySQL?**
SQLite needs no server for a student machine. SQLAlchemy hides the database: changing `DATABASE_URL` is enough. Long text uses
`LONGTEXT` on MySQL and results are stored in a JSON column, which both databases support.

**69. How did you test it?**
Backend: pytest unit tests for every NLP function (several with hand-computed expected values), API tests, and an end-to-end
training test. Frontend: Vitest tests simulating user actions, plus a contract test that renders every tab with real backend
responses. I also deliberately broke code to confirm the tests fail when they should.

**70. How is the work reproducible?**
Fixed seeds, a deterministic dataset generator, a determinism test for training, and `metrics.json` records the library
versions and all results.

**71. What about privacy and security?**
Everything runs locally, no document or text is sent anywhere, only the extracted text is stored, uploads are validated by
content, file names are sanitised, text is escaped before it enters the PDF, and cross-origin access is limited to the
frontend's address.

**72. How fast is it?**
On the development machine, preprocessing a 270,000-character text took about three seconds, entity recognition on 250,000
characters about 2.6 seconds, and training the whole classifier about 10 to 25 seconds. These are indicative figures from one
machine.

## M. Limitations and future work

**73. What are the main limitations?**
Synthetic training data; entity recognition not trained on academic text; no OCR; English only; approximate syllable counts;
similarity is lexical; summaries not scored automatically; five fixed classes.

**74. What would you do next?**
Collect real labelled documents; add OCR; use transformer embeddings for similarity; fine-tune entity recognition; add an
"Other" class and calibrated probabilities; try graph-based summarisation (TextRank) and measure it with ROUGE; add user
accounts and a background job queue for large files; deploy on MySQL.

## N. The difficult questions

**75. "100% accuracy sounds like cheating. Did you train on the test data?"**
No. The split is made before training, the model is selected using cross-validation on the training part only, and the test
part is scored once. The score is high because the synthetic data is easy, and I measured that: similarity to training is
about 0.62. That is why I also report the lower challenge-set result.

**76. "Which accuracy figure should I believe?"**
None of them as a real-world claim. The test split is optimistic, the challenge set is better but small and not real. The
only honest real-world number comes from real documents in `datasets/real/`, which the system supports and reports.

**77. "Why not BERT or ChatGPT?"**
The aim was explainable, local, classical NLP that I can defend technique by technique. Large models would be stronger on
meaning but cannot be explained at this level, need heavy resources or an external service, and would send documents away.

**78. "What does each tab on the screen prove?"**
Preprocessing shows every cleaning and normalisation step with counts; Keywords and Statistics show the formulas and their
inputs; Classification separates one prediction from measured performance; Summary shows how sentences were scored.

**79. "What is the single biggest weakness?"**
The training data. Everything else is explained and measured, but the classifier has only seen template-generated documents.

---

## Five-minute demonstration plan

1. Dashboard: show the counts, then the **Classifier results** panel and say aloud which sets are optimistic.
2. Upload a PDF; point at the real progress bar; open the document.
3. **Preprocessing**: the cleaning counts, then the "studying / studi / study" row.
4. **Keywords**: where the IDF comes from; then the trigram "natural language processing".
5. **Classification**: the prediction and its confidence; scroll to the confusion matrix and the three challenge-set mistakes.
6. **Summary**: change the number of sentences. **Export**: open the PDF and show the separate evaluation section.
7. Optionally paste text into `/docs` -> `POST /api/analysis/preview` to show the pipeline live.
