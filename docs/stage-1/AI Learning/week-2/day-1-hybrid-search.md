# Hybrid Search

------------------------------------------------------------------------

## Crisp Definition

**Hybrid Search** is an information-retrieval strategy that combines
**lexical/keyword search** (typically BM25 or another sparse retrieval
method) with **semantic/vector search** (dense embeddings) to produce
more relevant search results.

It combines the strengths of:

-   **Sparse / lexical retrieval** → exact words, identifiers, rare
    terms and domain-specific keywords.
-   **Dense / semantic retrieval** → meaning, synonyms, paraphrases and
    conceptual similarity.

## Mental Model

``` text
                           User Query
                               |
                  +------------+------------+
                  |                         |
                  v                         v
          Sparse Retrieval           Dense Retrieval
            (e.g. BM25)              (Embeddings)
                  |                         |
                  v                         v
           Ranked Result A           Ranked Result B
                  \                         /
                   \                       /
                    +------- Fusion ------+
                               |
                               v
                       Final Ranked Results
                               |
                               v
                              LLM
```

## Why Hybrid Search?

Neither sparse nor dense retrieval is perfect.

Consider:

``` text
Query: Spring Boot error HHH000104
```

An exact lexical retriever can strongly match `HHH000104`.

A dense retriever may understand that the query concerns a Hibernate/Spring Boot issue, but an exact error identifier is especially well suited to lexical matching.

Now consider:

``` text
Query: I cannot remember my account credentials
```

Document:

``` text
How to reset a forgotten password
```

The exact words differ, but dense retrieval can recognize their semantic similarity.

Hybrid search gives us **both capabilities**.

### Key Benefits

-   Better retrieval quality across different query types.
-   Handles exact keywords **and** semantic meaning.
-   Particularly useful for heterogeneous enterprise data.
-   Retrieval behavior can be tuned through weighting/fusion strategies.

!!! tip "Important"
    Hybrid search does not automatically guarantee better results. Its effectiveness depends on retrieval quality, fusion strategy, corpus characteristics, and tuning.

------------------------------------------------------------------------

## BM25

### Crisp Definition

**BM25 (Best Matching 25)** is a probabilistic ranking function used by
information-retrieval systems to estimate how relevant a document is to
a search query.

It builds upon ideas from TF-IDF while adding important mechanisms such
as:

1.  Term-frequency saturation
2.  Inverse document frequency
3.  Document-length normalization

------------------------------------------------------------------------

### How BM25 Works

#### Term Frequency (TF)

Term frequency asks:

> How often does the query term occur in this document?

If the query is:

``` text
Spring Boot Security
```

a document containing `Security` several times is generally more likely
to be relevant than one that never mentions it.

However, BM25 introduces **term-frequency saturation**.

``` text
1 occurrence  → significant evidence
2 occurrences → additional evidence
10 → 11 occurrences → comparatively little additional benefit
```

Therefore, repeatedly stuffing a keyword into a document does not cause
its relevance score to increase linearly forever.

------------------------------------------------------------------------

#### Inverse Document Frequency (IDF)

IDF asks:

> How informative is this term across the corpus?

Common words carry little discriminative value.

``` text
"the"        → extremely common → low importance
"application"→ relatively common
"HHH000104"  → rare             → high importance
```

Rare query terms generally contribute more strongly to relevance.

------------------------------------------------------------------------

#### Document-Length Normalization

Long documents naturally contain more words and therefore have more
opportunities to match query terms.

Without normalization, long documents could receive an unfair advantage.

BM25 compensates for document length relative to the average document
length in the corpus.

------------------------------------------------------------------------

### BM25 Intuition

``` text
BM25 Score
    =
Term Frequency contribution
    +
Term rarity / IDF contribution
    +
Document-length normalization
```

You do **not** need to memorize the complete BM25 equation for most
AI-engineering interviews.

You should understand the intuition behind these three components.

------------------------------------------------------------------------

### BM25 Limitations

#### Lexical rather than semantic

BM25 primarily depends on term matching.

``` text
Query:
forgot login credentials

Document:
reset password
```

The concepts are related, but lexical overlap may be weak.

#### Synonyms and paraphrases

BM25 does not inherently understand:

``` text
car ≈ automobile
```

or:

``` text
software engineer ≈ developer
```

#### No user/context awareness by default

BM25 itself does not automatically understand:

-   user history
-   preferences
-   conversational context
-   intent beyond lexical evidence

These capabilities have to be added by the surrounding system.

#### Corpus-dependent ranking

Document lengths, term frequencies and corpus composition influence BM25
scores.

#### No dense semantic representation

BM25 does not use dense neural embeddings, so it cannot model semantic
relationships in the same way as dense retrieval.

------------------------------------------------------------------------

## Sparse Representations / Sparse Retrieval

### Definition

A **sparse vector** represents text using a very high-dimensional
feature space where only a small number of dimensions have non-zero
values.

Conceptually:

``` text
Vocabulary:

[Java, Spring, Python, Docker, Redis, Kafka, ...]

Document:

"Java Spring Redis"

Sparse representation:

[0.8, 0.9, 0, 0, 0.7, 0, ...]
```

Most dimensions are zero.

Hence:

> **Sparse vector**

Traditional lexical systems may use representations derived from term
statistics such as TF-IDF. Modern sparse retrieval systems can also use
learned sparse representations. BM25 itself is best thought of as a
lexical ranking function rather than simply "a sparse embedding model."

------------------------------------------------------------------------

### Characteristics

-   Very high dimensional
-   Mostly zeros
-   Strong exact-term matching
-   Excellent for rare keywords and identifiers
-   Traditional approaches do not require dense embedding inference

### Common Systems

-   Elasticsearch
-   OpenSearch
-   Apache Solr
-   PostgreSQL Full-Text Search

Some modern vector databases/search engines also support sparse-vector
retrieval directly.

### Strong Use Cases

-   Legal document retrieval
-   Product catalogs and SKUs
-   Error codes
-   Logs and observability
-   Compliance documents
-   Technical terminology
-   Names and identifiers

------------------------------------------------------------------------

## Dense Vectors

### Definition

Dense vectors are generated by **embedding models** and represent
semantic information as fixed-length numerical vectors.

Example:

``` text
"How do I reset my password?"

            ↓
      Embedding Model
            ↓
[0.12, -0.32, 0.81, ..., 0.17]
```

Another sentence:

``` text
"I forgot my login credentials"

            ↓
      Embedding Model
            ↓
[0.11, -0.30, 0.79, ..., 0.20]
```

The vectors can be close in vector space even though the sentences do
not use exactly the same words.

------------------------------------------------------------------------

### Characteristics

-   Fixed dimensionality for a particular embedding model/configuration
-   Usually most dimensions contain non-zero floating-point values
-   Captures semantic relationships
-   Requires an embedding model
-   Similarity can be measured using metrics such as cosine similarity,
    dot product, or Euclidean distance depending on the model/index

### Common Vector Systems

-   Pinecone
-   Weaviate
-   Milvus
-   Qdrant
-   Chroma
-   FAISS

------------------------------------------------------------------------

### Strong Use Cases

-   Semantic search
-   RAG retrieval
-   FAQ matching
-   Knowledge-base search
-   Recommendation and similarity systems
-   Natural-language document discovery

------------------------------------------------------------------------

## Sparse vs Dense Retrieval

| Property | Sparse / Lexical | Dense / Semantic |
|----------|-------------------|------------------|
| **Main strength** | Exact lexical matching | Semantic similarity |
| **Representation** | High-dimensional, mostly zero | Fixed-size dense vector |
| **Meaning awareness** | Limited | Strong |
| **Exact identifiers** | Excellent | Can be weaker |
| **Synonyms/paraphrases** | Weak by default | Strong |
| **Typical examples** | BM25, TF-IDF | Embedding retrieval |
| **ML embedding required** | Not necessarily | Yes |


------------------------------------------------------------------------

### Useful Mental Shortcut

> **Sparse retrieves what you said.**\
> **Dense retrieves what you meant.**

This is an intuition, not an absolute rule.

Another common intuition is:

> Sparse retrieval often contributes **precision for exact lexical
> evidence**, while dense retrieval often improves **semantic recall**.

Again, don't treat this as a mathematical law---performance depends on
the dataset and query distribution.

------------------------------------------------------------------------

## Why Fusion Is Required

Suppose sparse retrieval returns:

``` text
Document A → BM25 score = 12.4
```

Dense retrieval returns:

``` text
Document B → cosine similarity = 0.85
```

Can we simply calculate:

``` text
12.4 + 0.85
```

No.

The scores originate from **different scoring systems and scales**.

A fusion strategy is therefore needed to combine the result lists or
normalize/combine their scores.

------------------------------------------------------------------------

## Reciprocal Rank Fusion (RRF)

### Core Idea

RRF largely ignores the raw scores and instead uses the **rank
position** of each document.

> A document that ranks highly across multiple retrieval methods is
> likely to be relevant.

A common form is:

``` text
RRF(d) = Σ 1 / (k + rank(d))
```

where:

-   `d` = document
-   `rank(d)` = its position in a result list
-   `k` = a constant that reduces the impact of very small rank
    differences

------------------------------------------------------------------------

### Example

Sparse results:

``` text
1. Doc A
2. Doc B
3. Doc C
```

Dense results:

``` text
1. Doc B
2. Doc D
3. Doc A
```

Doc A and Doc B appear near the top of **both lists**.

RRF therefore gives them strong combined rankings.

------------------------------------------------------------------------

### Why RRF Is Popular

-   Doesn't require BM25 and vector scores to share the same scale.
-   Simple.
-   Robust.
-   Requires relatively little score calibration.
-   Works well as a strong baseline for hybrid retrieval.

### Limitation

RRF mainly uses **rank positions**, so it discards much of the magnitude
information contained in the original retrieval scores.

------------------------------------------------------------------------

## Linear Combination / Weighted Scoring

### Core Idea

After making scores comparable (for example through normalization where
appropriate), combine them using configurable weights.

Conceptually:

``` text
Final Score =
α × Dense Score
+
(1 - α) × Sparse Score
```

Example:

``` text
α = 0.7

70% influence → Dense
30% influence → Sparse
```

------------------------------------------------------------------------

### Why Use It?

Useful when you know one retrieval method should carry greater influence
for your particular application.

Example:

A natural-language FAQ system may favor semantic retrieval.

A product-code search system may favor lexical retrieval.

### Limitation

Weights require tuning and raw scores often need
normalization/calibration before meaningful combination.

------------------------------------------------------------------------

## Relative Score Fusion (RSF)

### Core Idea

Instead of directly comparing raw scores from unrelated retrieval
systems, scores are normalized relative to the results produced by each
retrieval method and then combined.

Conceptually:

``` text
Sparse scores
      ↓
Normalize relative to sparse result range

Dense scores
      ↓
Normalize relative to dense result range

      ↓
Weighted combination
```

This preserves more score information than purely rank-based fusion.

### Trade-off

RSF can use score magnitude information, but it is more sensitive to
score distributions and normalization behavior than RRF.

------------------------------------------------------------------------

## RRF vs Weighted Fusion vs RSF

| Strategy | Main Idea | Strength | Limitation |
|----------|-----------|----------|------------|
| **RRF** | Combine ranks | Simple, robust, scale-independent | Loses much raw-score magnitude |
| **Weighted Scoring** | Combine comparable scores with weights | Explicit control | Requires tuning/calibration |
| **RSF** | Normalize scores relative to each result list and combine | Retains score information | Sensitive to normalization/distribution |


------------------------------------------------------------------------

## Complete Hybrid Search Pipeline

``` text
User Query
    |
    +-------------------------+
    |                         |
    v                         v
Sparse Retriever        Dense Retriever
(BM25 / sparse)          (Embeddings)
    |                         |
    v                         v
Top-K Sparse            Top-K Dense
Results                 Results
    |                         |
    +------------+------------+
                 |
                 v
            Fusion Layer
         (RRF / RSF / Weighted)
                 |
                 v
        Final Ranked Documents
                 |
          [Optional Reranker]
                 |
                 v
             Top Context
                 |
                 v
                 LLM
```

### Important distinction

**Fusion** combines outputs from different retrieval systems.

A **reranker** is an optional later stage that takes candidate documents
and scores/orders them again using a stronger relevance model or another
ranking strategy.

They are related, but **fusion ≠ reranking**.

------------------------------------------------------------------------

## When Does BM25 Win?

BM25 is especially strong when queries contain:

### Exact identifiers

``` text
ERR_CONNECTION_REFUSED
```

### Product codes

``` text
SM-S928B
```

### API/class/method names

``` text
ConcurrentHashMap.computeIfAbsent
```

### Rare terminology

``` text
pneumonoultramicroscopicsilicovolcanoconiosis
```

### Names, legal clauses, ticket numbers and error codes

In these situations, exact lexical evidence can be more valuable than
broad semantic similarity.

------------------------------------------------------------------------

## Why Isn't Vector Search Alone Enough?

Dense retrieval is powerful, but it can:

-   miss exact identifiers
-   underweight rare lexical matches
-   retrieve semantically related but factually irrelevant chunks
-   behave differently depending on embedding-model quality/domain
-   struggle with certain acronyms, codes, numbers, names and domain
    terminology

Hybrid search provides another retrieval signal to compensate for these
weaknesses.

------------------------------------------------------------------------

## Interview Q&A

### What is Hybrid Search?

**Answer:**

Hybrid search combines lexical retrieval, such as BM25, with dense
semantic retrieval using embeddings. Lexical search is strong at exact
terms and rare identifiers, while dense retrieval captures semantic
similarity and paraphrases. Their result sets are combined using a
fusion strategy such as Reciprocal Rank Fusion or normalized weighted
scoring to produce a stronger final ranking.

------------------------------------------------------------------------

### Why not use only vector search for RAG?

**Answer:**

Vector search is excellent for semantic similarity, but it can perform
poorly for exact identifiers, rare terms, error codes, product IDs,
names or domain-specific keywords. Lexical search handles these cases
well. Hybrid retrieval combines both signals and therefore tends to be
more robust across different query types.

------------------------------------------------------------------------

### What is BM25?

**Answer:**

BM25 is a probabilistic lexical ranking function used to estimate
document relevance for a query. Its ranking behavior primarily considers
term frequency with saturation, inverse document frequency and
document-length normalization.

------------------------------------------------------------------------

### How is BM25 different from TF-IDF?

**Answer:**

Both use term-frequency and inverse-document-frequency ideas, but BM25
improves ranking behavior through term-frequency saturation and explicit
document-length normalization. This prevents repeated terms and long
documents from receiving disproportionately high relevance simply
because of frequency or size.

------------------------------------------------------------------------

### What is term-frequency saturation?

**Answer:**

The first few occurrences of a query term provide useful relevance
evidence, but repeatedly adding the same term should not increase
relevance indefinitely. BM25 therefore makes the contribution from term
frequency grow more slowly as occurrences increase.

------------------------------------------------------------------------

### Why does BM25 use document-length normalization?

**Answer:**

Long documents naturally contain more terms and therefore have more
opportunities to match a query. Length normalization prevents them from
receiving an unfair ranking advantage solely because they contain more
words.

------------------------------------------------------------------------

### What is the difference between sparse and dense vectors?

**Answer:**

Sparse representations typically have a very large number of dimensions
with most values equal to zero and are commonly associated with lexical
features or terms. Dense vectors are fixed-size numerical
representations generated by embedding models, with information
distributed across their dimensions to capture semantic relationships.

------------------------------------------------------------------------

### Give an example where dense retrieval beats BM25.

**Answer:**

Query:

``` text
I forgot my login credentials
```

Document:

``` text
How to reset your password
```

There is limited lexical overlap, but their meanings are closely
related. Dense embeddings can place them close together in vector space
and retrieve the document.

------------------------------------------------------------------------

### Give an example where BM25 beats dense retrieval.

**Answer:**

If the query contains an exact error code such as:

``` text
ORA-00942
```

a lexical retriever can strongly match documents containing that exact
identifier. Dense semantic retrieval may not reliably give that rare
identifier enough importance.

------------------------------------------------------------------------

### Why can't we directly add BM25 and cosine-similarity scores?

**Answer:**

Because the scores come from different retrieval systems and generally
exist on different scales with different interpretations. A BM25 score
such as `12.4` and cosine similarity such as `0.85` are not directly
comparable. We need rank fusion or appropriate score
normalization/calibration before combining them.

------------------------------------------------------------------------

### What is Reciprocal Rank Fusion?

**Answer:**

RRF combines multiple ranked result lists using each document's rank
rather than its raw retrieval score. Documents appearing near the top of
multiple result lists receive higher combined scores. This makes RRF
useful when retrieval systems produce scores on incompatible scales.

------------------------------------------------------------------------

### Why is RRF commonly used for Hybrid Search?

**Answer:**

It is simple, robust and largely score-scale independent. BM25 and dense
retrieval can produce very different score distributions, but RRF only
needs their ranking positions, avoiding complicated score calibration.

------------------------------------------------------------------------

### What is the limitation of RRF?

**Answer:**

Because RRF primarily operates on rank positions, it discards much of
the information contained in raw score magnitudes. Two documents with
very different relevance scores can still have adjacent ranks.

------------------------------------------------------------------------

### What is weighted fusion?

**Answer:**

Weighted fusion combines retrieval signals by assigning each method a
configurable influence, such as 70% dense and 30% sparse. Scores
generally need to be made comparable first, and the weights should be
tuned against the application's retrieval requirements.

------------------------------------------------------------------------

### What is Relative Score Fusion?

**Answer:**

Relative Score Fusion normalizes scores relative to the score
distribution or range within each retrieval result set before combining
them. Unlike RRF, it retains information about score magnitude while
avoiding direct comparison of unrelated raw score scales.

------------------------------------------------------------------------

### Fusion vs reranking --- what's the difference?

**Answer:**

Fusion combines candidate results produced by multiple retrieval
systems, such as BM25 and dense vector retrieval. Reranking happens
after candidate retrieval/fusion and uses another ranking
mechanism---often a stronger model---to reorder candidates according to
query-document relevance.

------------------------------------------------------------------------

### Does Hybrid Search always outperform dense search?

**Answer:**

No. Hybrid search provides additional retrieval signals, but performance
depends on the dataset, queries, retriever configuration, fusion method
and tuning. Retrieval quality should be evaluated using representative
queries and relevance judgments rather than assuming hybrid is
automatically superior.

------------------------------------------------------------------------

### Explain Hybrid Search in one minute.

**Answer:**

In traditional keyword search, algorithms such as BM25 retrieve
documents based primarily on lexical overlap, which is very effective
for exact keywords, names and identifiers but does not inherently
understand semantic similarity. Dense retrieval converts queries and
documents into embeddings, allowing semantically similar text to match
even when the wording differs, but it can be weaker for exact lexical
signals such as error codes. Hybrid search runs both retrieval
strategies and combines their result lists using techniques such as
Reciprocal Rank Fusion or normalized weighted scoring. This gives a RAG
system both lexical precision and semantic retrieval capability.

------------------------------------------------------------------------

## Common Interview Traps

### ❌ "BM25 is semantic search."

Incorrect.

BM25 is primarily a **lexical ranking algorithm**.

------------------------------------------------------------------------

### ❌ "Sparse vectors are always BM25 vectors."

Too broad.

BM25 is a lexical ranking function. Sparse representations can come from
TF-IDF, learned sparse retrieval models, or other sparse techniques.

------------------------------------------------------------------------

### ❌ "Dense vectors always have 768 dimensions."

Incorrect.

Dimension depends on the embedding model/configuration.

Examples can include:

``` text
384
768
1024
1536
3072
...
```

------------------------------------------------------------------------

### ❌ "Hybrid Search means RRF."

Incorrect.

RRF is **one fusion strategy**.

Other approaches include weighted/linear score combination and
relative-score normalization/fusion.

------------------------------------------------------------------------

### ❌ "Dense = recall and sparse = precision, always."

Treat this as an intuition, not a law.

Actual precision and recall depend on the dataset, queries and retrieval
configuration.

------------------------------------------------------------------------

### ❌ "Fusion and reranking are the same."

Incorrect.

``` text
Retrievers → Fusion → Candidate Set → Optional Reranker
```

------------------------------------------------------------------------

## What You Should Remember Forever

If you revisit only one section, remember this:

- **Hybrid Search = Lexical/Sparse Retrieval + Dense/Semantic Retrieval + Fusion**
- **BM25 = term-frequency saturation + IDF + document-length normalization**
- **Sparse retrieval is excellent at exact lexical evidence.**
- **Dense retrieval captures semantic relationships and paraphrases.**
- **Sparse retrieves what you said; dense retrieves what you meant.** Use that as intuition—not an absolute rule.
- Raw BM25 and dense similarity scores generally cannot simply be added because their scales are unrelated.
- **RRF solves this by combining ranks instead of raw scores.**
- Weighted/relative-score approaches preserve more score information but require normalization and/or tuning.
- **Fusion ≠ reranking.**
- Hybrid retrieval is particularly valuable in RAG systems containing both natural-language content and exact terminology/identifiers.


------------------------------------------------------------------------

## Stage 1 --- Week 2 Checkpoint

Before moving beyond Hybrid Search, you should be able to explain
without notes:

- What Hybrid Search is
- Why dense retrieval alone can fail
- How BM25 works conceptually
- TF saturation
- IDF
- Document-length normalization
- Sparse vs dense representations
- Where BM25 wins
- Where dense retrieval wins
- Why fusion is necessary
- RRF
- Weighted fusion
- Relative Score Fusion
- Fusion vs reranking
- A complete Hybrid RAG retrieval pipeline

If you can explain these confidently, your Hybrid Search foundation is
strong enough to move to the next Week 2 topic: **Metadata Filtering &
Indexing**.
