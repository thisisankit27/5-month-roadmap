# Thinking Like a Senior Engineer.v2

## PR-7 Discussion — Hybrid Search Architecture

> Stage 1 · Week 2
>
> Goal: Upgrade our educational RAG system into a production-style retrieval system by introducing Hybrid Search while preserving clean architecture and separation of concerns.

---

### Problem Statement

Our current retrieval pipeline only supports **dense semantic retrieval**.

Current flow:

```text
Question
    │
    ▼
EmbeddingService
    │
    ▼
VectorStore.search()
    │
    ▼
Top-K Chunks
```

This works well for semantic questions like:

> "How do I reset my password?"

However, it struggles with exact lexical queries such as:

- ORA-00942
- HHH000104
- INV-2026-1001
- Product SKUs
- Error Codes

These queries require **keyword matching**, not semantic similarity.

Therefore we need to introduce **Hybrid Search**.

---

### Initial Thoughts

At first it seemed that only the retrieval logic needed to change.

After discussion, we realized this is incorrect.

Hybrid Search changes **both**:

- the ingestion pipeline
- the retrieval pipeline

because sparse indexes must already exist before retrieval can use them.

---

### First Architectural Insight

Hybrid Search is not merely another search algorithm.

It introduces a second indexing pipeline.

Current architecture:

```text
Document
    │
    ▼
Embedding
    │
    ▼
Dense Index
```

Target architecture:

```text
Document
        │
        ├───────────────┐
        ▼               ▼
Embedding         Lexical Processing
        │               │
        ▼               ▼
Dense Index      Sparse (Lexical) Index
```

The ingestion pipeline therefore becomes responsible for building **multiple indexes**.

---

### Design Decision #1

Separate **Index Construction** from **Retrieval**.

These are two different responsibilities.

Index Construction happens once when documents are ingested.

Retrieval happens every time a user asks a question.

These lifecycles are independent.

---

#### Proposed Architecture

##### Indexing Pipeline

```text
Chunks
    │
    ▼
Indexer
    │
    ├─────────────┐
    ▼             ▼
DenseIndexer   SparseIndexer
```

Responsibilities:

DenseIndexer

- Generate embeddings
- Build dense index

SparseIndexer

- Build lexical index
- Prepare data for sparse retrieval

---

##### Retrieval Pipeline

```text
Question
      │
      ▼
RetrievalService
      │
 ┌────┴───────────┐
 ▼                ▼
DenseRetriever  SparseRetriever
      │              │
      └──────┬───────┘
             ▼
      FusionService
             ▼
      Ranked Documents
```

The RAG pipeline should never know whether retrieval is:

- Dense
- Sparse
- Hybrid

It simply calls:

```python
documents = retriever.retrieve(query)
```

---

### Design Decision #2

Introduce a **RetrievalService** abstraction.

Initially referred to as a "Strategy Selector".

We renamed it because classes should be named by **their responsibility**, not by their implementation.

The RetrievalService is responsible for retrieving documents.

Internally it may choose:

- Dense Retrieval
- Sparse Retrieval
- Hybrid Retrieval

The orchestrator should never know which strategy is being used.

---

### Design Decision #3

Separate Fusion from Retrieval.

Initially it seemed reasonable for HybridRetriever to:

- perform dense retrieval
- perform sparse retrieval
- fuse results

This violates the Single Responsibility Principle.

Instead:

```text
Dense Retriever

Sparse Retriever

↓

Fusion Service

↓

Final Ranking
```

Benefits:

- Easier testing
- Easier experimentation
- Supports future fusion algorithms
- Prevents HybridRetriever becoming a God Class

Future fusion algorithms may include:

- Reciprocal Rank Fusion (RRF)
- Weighted Fusion
- Relative Score Fusion (RSF)
- Cross Encoder Re-ranking

---

### Design Decision #4

Configuration should be the Single Source of Truth.

Both indexing and retrieval should read from the same application configuration.

Example:

```yaml
retrieval:
    dense: true
    sparse: true
```

This prevents inconsistent behavior between ingestion and retrieval.

However...

Configuration represents **desired capability**.

The retriever must also verify which indexes actually exist.

Example:

```text
Configuration

↓

Hybrid Enabled

↓

Sparse Index Missing

↓

Fallback to Dense Retrieval
```

Production systems should degrade gracefully rather than fail.

---

### Important Terminology Correction

Initially we referred to:

> BM25 Store

or

> BM25 Index

This is not the most accurate terminology.

BM25 is a **ranking algorithm**.

The architecture should instead refer to:

- Sparse Index
- Lexical Index
- Sparse Retriever

This keeps the architecture open for future algorithms such as:

- SPLADE
- Other sparse retrieval techniques

Only the implementation changes.

The architecture remains stable.

---

### Responsibilities

#### DenseIndexer

Responsible for:

- generating embeddings
- constructing dense indexes

Not responsible for:

- retrieval
- persistence decisions

---

#### SparseIndexer

Responsible for:

- lexical indexing
- token statistics

Not responsible for:

- ranking
- retrieval

---

#### RetrievalService

Responsible for:

- selecting retrieval strategy
- orchestrating retrieval

Not responsible for:

- ranking fusion
- prompt generation

---

#### DenseRetriever

Responsible for:

- dense similarity search

---

#### SparseRetriever

Responsible for:

- lexical retrieval

---

#### FusionService

Responsible for:

- combining multiple retrieval result sets

Not responsible for:

- performing retrieval

---

### Final Target Architecture

#### Ingestion

```text
Loader
    │
    ▼
Chunker
    │
    ▼
Indexer
    │
 ┌──┴─────────────┐
 ▼                ▼
Dense         Sparse
Indexer       Indexer
 │                │
 ▼                ▼
Dense Repo    Sparse Repo
```

---

#### Query Pipeline

```text
Question
      │
      ▼
RetrievalService
      │
 ┌────┴──────────┐
 ▼               ▼
Dense        Sparse
Retriever    Retriever
      │
      ▼
FusionService
      │
      ▼
Retrieved Chunks
      │
      ▼
GenerationService
      │
      ▼
LLM
```

---

### Engineering Lessons

Hybrid Search is **not** just a new search method.

It introduces an entirely new indexing pipeline.

---

Building indexes and querying indexes are different responsibilities.

Separate them.

---

Name classes by their responsibility, not their implementation.

Prefer:

- RetrievalService

over

- StrategySelector

---

Fusion is a separate concern.

Do not mix retrieval and ranking.

---

Configuration should define desired behavior.

The application should still validate runtime capabilities.

---

A stable architecture should survive implementation changes.

Replacing BM25 with SPLADE should not require changing the architecture.

Only the SparseRetriever implementation changes.

---

### Interview Takeaways

You should now be able to answer:

- Why isn't dense retrieval sufficient?
- Why does Hybrid Search require ingestion changes?
- Why separate indexing from retrieval?
- Why introduce a RetrievalService?
- Why is Fusion a separate service?
- Why is BM25 considered an implementation detail rather than an architectural concern?
- Why should the RAG orchestrator not know which retrieval strategy is being used?
