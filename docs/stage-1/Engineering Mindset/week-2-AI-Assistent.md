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

---

## PR-8 — Metadata Catalog & Metadata Filtering

### Objective

After completing PR-7 (Hybrid Search), our RAG system could retrieve information using both semantic (Dense Retrieval) and lexical (BM25) search.

However, every search was still performed across the **entire knowledge base**.

Real-world RAG systems rarely search every document.

Instead, users often restrict searches to:

- Specific files
- Departments
- Projects
- Date ranges
- Authors
- Pages

PR-8 introduces the architectural foundation for that capability.

---

### The Problem

Current architecture:

```
User Question
      │
      ▼
Retrieval Service
      │
      ▼
Dense + Sparse Retrieval
      │
      ▼
Fusion
```

The retrievers have no knowledge of:

- which documents exist
- which documents the user selected
- which metadata belongs to each document

Likewise, the UI has no persistent knowledge of previously indexed documents.

Once indexing completes, the uploaded files are forgotten.

---

### Core Idea

Instead of treating Metadata Filtering as merely "adding filters", we realized that the system is actually missing an entire architectural layer.

That layer is:

> **Metadata Catalog**

This becomes the **source of truth** for the knowledge base.

---

### What is a Metadata Catalog?

A Metadata Catalog stores information **about the corpus**, not the document contents themselves.

It does **NOT** store:

- embeddings
- vectors
- chunks
- BM25 indexes

Instead, it stores metadata describing the uploaded documents.

Example:

```python
{
    "document_id": "doc_001",
    "display_name": "Spring Boot Guide.pdf",
    "source": "/uploads/spring.pdf",
    "uploaded_at": "...",
    "chunk_count": 42
}
```

---

### Why introduce Metadata Catalog?

Without it:

```
UI
 │
 ▼
What documents exist?

❌ No answer.
```

After introducing Metadata Catalog:

```
UI
 │
 ▼
MetadataCatalog.list_documents()

↓

Spring.pdf
Docker.pdf
Java.pdf
```

The UI no longer guesses.

It asks the catalog.

---

### Metadata Catalog Responsibilities

The Metadata Catalog owns only one responsibility:

> Managing document metadata.

Responsibilities:

- Register newly uploaded documents into the catalog
- Persist the metadata catalog to disk
- Load the catalog from storage
- List available documents
- Find document metadata by document ID (future)
- Delete document metadata (future)

The Metadata Catalog does NOT generate metadata.

It simply indexes and persists metadata that already exists on the loaded documents.

It does NOT know:

- Retrieval
- BM25
- FAISS
- Embeddings
- Prompting

This follows the **Single Responsibility Principle (SRP)**.

---

### Metadata Filtering Service

Metadata Filtering is a separate responsibility from retrieval.

Its job is to filter retrieved chunks based on structured metadata supplied by the UI.

Current implementation supports:

- document_id filtering

Future versions can easily extend to:

- page filtering
- author filtering
- department filtering
- date filtering
- tags

Because filtering lives in one dedicated service, RetrievalService and the retrievers remain unchanged as filtering capabilities grow.

---

### Why not store document information inside Vector Store?

Because Vector Store is optimized for:

- vector similarity search

Metadata Catalog is optimized for:

- document management

These are different responsibilities.

Separating them makes the architecture cleaner.

---

### Folder Structure

After discussion, we decided NOT to create a separate `DocumentMetadata` class.

Reason:

It would simply wrap a dictionary and be used by only one class.

That violates the YAGNI principle ("You Aren't Gonna Need It").

Instead:

```
src
│
├── catalog
│     metadata_catalog.py
```

Only one class is needed.

---

### Final Ingestion Architecture

```
            Uploaded Files
                │
                ▼
        Document Loader (Factory)
                │
                ▼
        Assign Document Metadata
        ├── document_id
        └── display_name
                │
                ▼
        MetadataCatalog.register()
        (persist catalog only)
                │
                ▼
            Chunking Engine
                │
                ▼
        Inject Chunk Metadata
        ├── chunk_index
        └── chunk_id
                │
                ▼
            Indexer Service
        ┌───────────────┐
        ▼               ▼
        EmbeddingService  BM25Indexer
        ▼               ▼
        Dense Store     Sparse Store
```

---

### Why Metadata Catalog comes BEFORE Chunking

Originally we considered letting the Metadata Catalog generate document metadata.

After further architectural discussion, we realized that metadata should be created as early as possible.

The Document Loader is the first component that knows:

- which uploaded file produced the documents
- the display name
- the logical identity of the document

Therefore the loader assigns:

- document_id
- display_name

The Metadata Catalog simply persists that information.

Chunking then inherits the document metadata and only contributes chunk-specific metadata:

- chunk_index
- chunk_id

This keeps every layer responsible only for metadata it owns.

---

### Chunk Metadata

Every chunk now carries:

```python
{
    "document_id": "...",
    "display_name": "...",
    "chunk_index": ...,
    "chunk_id": ...
}
```

This metadata is reused throughout the entire pipeline.

---

### Retrieval Architecture

```
                    UI
                     │
                     ▼
         Multi Select Documents
            (display_name)
                     │
                     ▼
          Selected document_ids
                     │
                     ▼
                  rag.py
                     │
                     ▼
            RetrievalService
                     │
            ┌────────┴────────┐
            ▼                 ▼
      DenseRetriever    SparseRetriever
            |                 |
            ▼                 ▼
 Raw Dense Results         Raw Sparse Results
            └────────┬────────┘
                     ▼
            MetadataFilteringService
                     ▼
              FusionService
                     ▼
              Ranked Documents
                     ▼
           GenerationService
                     ▼
                LLM Response
```

Notice:

Generation Service never changes.

Only Retrieval becomes filter-aware.

This is exactly what good layered architecture should achieve.

---

### Why UI should NOT send filenames

Initially, we discussed filtering by filename.

Later we changed the design.

The UI displays:

```
Spring Boot Guide.pdf
```

But sends:

```python
filters = {
    "document_ids": [
        "doc_001",
        "doc_002"
    ]
}
```

Reason:

Filenames are not guaranteed to be unique.

Example:

```
HR/Policy.pdf

Finance/Policy.pdf
```

Using filenames would introduce ambiguity.

Document IDs never do.

---

### UI Responsibility

The UI is responsible for:

Displaying

```
☑ Spring Boot Guide.pdf
☑ Docker Guide.pdf
☐ Java Notes.pdf
```

When the user clicks Ask:

```
display_name

↓

document_id

↓

filters

↓

Retrieval Service
```

The backend never depends on filenames.

---

### Retrieval Interface

Before:

```python
retrieve(query, top_k)
```

After:

```python
retrieve(
    query,
    top_k,
    filters
)
```

The RetrievalService orchestrates retrieval but does not implement filtering itself.

Instead, it delegates metadata filtering to the dedicated MetadataFilteringService before passing the filtered results to Fusion.

---

### Why Metadata Filtering became its own service

During implementation we considered three designs:

Option A

Question

↓

Filter

↓

Retriever

Option B

Question

↓

Retriever

↓

Filter

Option C (Chosen)

Dense Retriever

↓

Metadata Filtering

Sparse Retriever

↓

Metadata Filtering

↓

Fusion

Rather than embedding filtering logic inside each retriever, we extracted a dedicated MetadataFilteringService.

Benefits:

- RetrievalService remains an orchestrator.
- DenseRetriever and SparseRetriever focus only on retrieval.
- Metadata filtering has a single implementation (DRY).
- Future metadata filters (pages, authors, departments, tags) require changes in only one place.

This follows the Single Responsibility Principle.

---

### Dynamic Filtering Groundwork

PR-8 intentionally does NOT implement natural language filtering.

Example:

```
Search only Spring.pdf
```

Instead, the UI sends structured filters.

Later, an LLM can translate natural language into:

```python
{
    "document_ids": [
        "doc_001"
    ]
}
```

This is exactly why the roadmap says:

> Self-query Preparation

and not

> Self-query Retrieval

---

### Architecture Principles Learned

#### Metadata ≠ Retrieval

Metadata management deserves its own layer.

---

#### Storage has different purposes

Dense Store

↓

Similarity Search

Sparse Store

↓

Keyword Search

Metadata Catalog

↓

Corpus Management

Different storage.

Different responsibility.

---

#### UI and Backend should speak different languages

UI:

```
Spring Boot Guide.pdf
```

Backend:

```
doc_001
```

This separation avoids ambiguity.

---

#### Stable IDs are fundamental

Everything should operate using:

```
document_id
```

instead of filenames.

---

#### Layered Architecture

UI

↓

RAG

↓

Retrieval

↓

Fusion

↓

Generation

Metadata filtering extends only the Retrieval layer.

Everything else remains unchanged.

---

#### Filtering is Business Logic

Metadata filtering is not a storage concern.

Vector Stores retrieve similar documents.

Metadata Filtering decides which retrieved documents are eligible.

Separating these concerns keeps storage engines independent of application rules.

---

### Future Possibilities

The Metadata Catalog enables future features with minimal changes:

- Delete documents
- Update documents
- Metadata filtering
- Page filtering
- Author filtering
- Department filtering
- Self-query retrieval
- Corpus statistics
- Knowledge base dashboard
- Incremental indexing

---

### Interview Questions

#### Why introduce a Metadata Catalog instead of storing everything inside the Vector Store?

Vector Stores are optimized for similarity search.

Metadata Catalogs are optimized for corpus management.

Separating them follows the Single Responsibility Principle and keeps retrieval independent from document management.

---

#### Why should the UI send document IDs instead of filenames?

Filenames are not guaranteed to be unique.

Document IDs are stable and unique, preventing ambiguity during filtering.

---

#### Why does Metadata Catalog execute before Chunking?

Chunking requires a stable `document_id` so every generated chunk can inherit the correct metadata.

---

#### Why should filtering happen inside each retriever instead of RetrievalService?

Each retriever knows how filtering applies to its own storage mechanism.

RetrievalService should remain an orchestrator and not contain storage-specific logic.

---

### Key Takeaways

- Metadata filtering is fundamentally a **corpus management** problem.
- Introduced **Metadata Catalog** as the source of truth for document metadata.
- Distinguished **display_name** (UI) from **document_id** (backend).
- Established a clean ingestion pipeline where metadata is assigned before chunking.
- Metadata Catalog became a persistence layer for document metadata rather than a metadata generator.
- Extended retrieval through structured filters without modifying Generation or Fusion.
- Introduced MetadataFilteringService to centralize all metadata-based filtering and keep RetrievalService focused on orchestration.
- Designed the system to naturally support future self-query retrieval and advanced metadata-based search.

---

## PR-9 — Validation Pipeline (Guardrails)

### Objective

Until PR-8, our RAG pipeline focused solely on retrieving relevant information.

However, production AI systems must also decide **whether a request should continue through the pipeline at all**.

PR-9 introduces a **Validation Pipeline**, allowing every stage of the request lifecycle to validate its inputs and terminate processing early when necessary.

Instead of treating guardrails as isolated checks, they become first-class architectural components.

---

### Architectural Shift

Before PR-9, the request flow was:

```text
Question
    │
    ▼
Retrieval
    │
    ▼
Generation
```

After PR-9:

```text
Question
    │
    ▼
Input Guardrails
    │
    ▼
Retrieval
    │
    ▼
Context Guardrails
    │
    ▼
Generation
    │
    ▼
Output Guardrails
    │
    ▼
Response
```

The pipeline now validates requests **before**, **during**, and **after** generation.

---

### Design Philosophy

A guardrail is **not** responsible for interacting with the user.

Instead, each guardrail answers a single question:

> "Should this request continue?"

If the answer is **No**, the guardrail returns a structured response explaining why.

If the answer is **Yes**, the pipeline proceeds normally.

This keeps validation independent from the UI.

---

### Early Exit Pipeline

Every stage has permission to terminate the request.

```text
Question
    │
    ▼
Input Guardrails
    │
    ├── Validation Failed?
    │        │
    │        └── Return Response
    │
    ▼
Retrieval
    │
    ▼
Context Guardrails
    │
    ├── Validation Failed?
    │        │
    │        └── Return Response
    │
    ▼
Generation
    │
    ▼
Output Guardrails
    │
    ├── Validation Failed?
    │        │
    │        └── Return Response
    │
    ▼
Final Response
```

The orchestrator (`rag.py`) simply coordinates these stages.

---

### Single Response Contract

One important architectural decision was to **avoid multiple response types**.

Instead of introducing a separate `GuardrailResult`, every stage returns the same object:

```text
GenerationResponse
```

Whether:

- generation succeeds,
- validation fails,
- context is missing,

the caller always receives a `GenerationResponse`.

This keeps the API contract stable.

---

### GenerationResponse Evolution

Originally, `GenerationResponse` only represented successful generations.

PR-9 evolves it into the response object for the **entire request lifecycle**.

Additional fields:

- success
- reason
- message

Example:

Successful request:

```text
success = true
answer = "..."
```

Blocked request:

```text
success = false
reason = "EMPTY_QUERY"
message = "Please enter a question."
```

---

### Validation Layers

#### Input Guardrails

Executed before retrieval.

Purpose:

- Prevent invalid requests from entering the pipeline.

Current validators:

- Empty Question
- Prompt Injection Detection

Future ideas:

- Maximum length
- Language detection
- PII detection
- Profanity
- Rate limiting

---

#### Context Guardrails

Executed after retrieval.

Purpose:

Determine whether retrieved information is sufficient for generation.

Current validators:

- Empty Retrieval

Future ideas:

- Semantic relevance validation
- Confidence threshold
- Helper LLM for context verification

---

#### Output Guardrails

Executed after generation.

Purpose:

Validate generated responses before presenting them to the user.

Current validators:

- Empty Response

Future ideas:

- Groundedness verification
- Safety classification
- Hallucination detection
- Citation verification

---

### Why Separate Guardrails?

Validation responsibilities naturally occur at different stages.

| Stage | Responsibility |
|---------|----------------|
| Input | Is the question valid? |
| Context | Is the retrieved knowledge sufficient? |
| Output | Is the generated response acceptable? |

Separating these concerns keeps every validator focused on one responsibility.

---

### Why Validation Happens Outside Services

GenerationService is responsible for **generation only**.

RetrievalService is responsible for **retrieval only**.

Neither service should decide whether processing should stop.

Validation belongs to dedicated guardrail components, keeping every service focused on a single responsibility.

---

### Orchestration Responsibility

`rag.py` now acts as the orchestration layer.

Responsibilities:

- Run Input Guardrails
- Coordinate Retrieval
- Run Context Guardrails
- Coordinate Generation
- Run Output Guardrails
- Return the final response

Business logic remains distributed across specialized services.

---

### Extensibility

One major goal of PR-9 was extensibility.

Adding a new validator requires only:

1. Implement validator.
2. Register it in the corresponding guardrail.
3. No changes to Retrieval or Generation.

The overall pipeline remains unchanged.

---

### Key Learnings

This PR introduced several production-oriented software engineering concepts:

- Validation Pipeline
- Early Exit Pattern
- Stable Response Contracts
- Separation of Concerns
- Orchestration Layer
- Pipeline Architecture
- Layered Validation
- Guardrail Design
- Production AI Request Lifecycle

---

### Final Architecture

```text
                User Question
                      │
                      ▼
            Input Guardrails
         ├── Empty Query
         └── Prompt Injection
                      │
                      ▼
            Retrieval Service
                      │
                      ▼
           Context Guardrails
         ├── Empty Retrieval
         └── Relevance (Future)
                      │
                      ▼
           Generation Service
                      │
                      ▼
            Output Guardrails
         ├── Empty Response
         ├── Safety (Future)
         └── Groundedness (Future)
                      │
                      ▼
            GenerationResponse
                      │
                      ▼
                 Streamlit UI
```

---

### Outcome

PR-9 transformed the application from a simple RAG pipeline into a structured AI request-processing pipeline.

Instead of blindly retrieving and generating, the application now validates every stage of the request lifecycle before allowing execution to continue.

This architecture closely mirrors how production AI systems coordinate validation, retrieval, generation, and response handling while maintaining a clean separation of responsibilities.