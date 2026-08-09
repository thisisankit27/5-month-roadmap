# Thinking Like a Senior Engineer.v2

> Week 1 built a RAG pipeline that worked.
> Week 2 asks whether it would survive contact with production.

Three PRs, and not one of them adds a feature a user would ask for by name. PR-7 makes
retrieval work for the queries embeddings are bad at. PR-8 gives the corpus an identity the
system can reason about. PR-9 gives the pipeline permission to refuse.

The question running underneath all three:

> Where does this responsibility actually belong — and what happens when the thing it
> depends on isn't there?

---

## PR-7 Discussion — Hybrid Search Architecture

> **Goal**
> Upgrade an educational RAG system into a production-style retrieval system by introducing
> Hybrid Search, without sacrificing clean architecture or separation of concerns.

### Problem Statement

Retrieval was **dense only**.

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

This works well when the user's wording and the document's wording differ but the *meaning*
matches:

> "How do I reset my password?"

It struggles the moment the characters themselves are the query.

| Query kind | Example | What it actually needs |
| --- | --- | --- |
| Semantic question | "How do I reset my password?" | similarity of meaning |
| Error code | `ORA-00942`, `HHH000104` | exact keyword match |
| Invoice / reference ID | `INV-2026-1001` | exact keyword match |
| Product SKU | catalogue identifiers | exact keyword match |

These queries require **keyword matching, not semantic similarity**. One retrieval mode was
being asked to serve two fundamentally different kinds of question.

> **The engineering problem is not "retrieval quality is low."**
> It is: *a single retrieval strategy is answering two different classes of query.*

------------------------------------------------------------------------

### Core Thoughts — What I Believed Going In

My starting position: *hybrid search is a retrieval change — add a second retriever, merge
the results, done.*

That is wrong, and it is wrong in the way that costs the most time later. **Retrieval can
only query what ingestion has already built.** A sparse retriever with no sparse index is
not a degraded feature, it is a missing one.

So hybrid search changes **both** pipelines:

- the ingestion pipeline, which must now build more than one index
- the retrieval pipeline, which must now query and combine more than one index

### First Architectural Insight

Hybrid Search is not another search algorithm. It is a **second indexing pipeline**.

**Before — one index, one path:**

```text
Document
    │
    ▼
Embedding
    │
    ▼
Dense Index
```

**After — one document, two representations:**

```text
                Document
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   Embedding            Lexical Processing
        │                       │
        ▼                       ▼
  Dense Index          Sparse (Lexical) Index
```

Ingestion becomes responsible for building **multiple indexes**, not one.

------------------------------------------------------------------------

### Design Decision #1 — Separate Index Construction from Retrieval

Index construction and retrieval are two different responsibilities with two different
**lifecycles**:

| | When it runs | How often |
| --- | --- | --- |
| Index Construction | when documents are ingested | once per document |
| Retrieval | when a user asks a question | every request |

Anything whose lifecycle differs this sharply does not belong in the same component.

**Indexing pipeline:**

```text
              Chunks
                 │
                 ▼
              Indexer
                 │
         ┌───────┴───────┐
         ▼               ▼
   DenseIndexer    SparseIndexer
         │               │
         ▼               ▼
   Dense Index     Sparse Index
```

`DenseIndexer` generates embeddings and builds the dense index. `SparseIndexer` builds the
lexical index and prepares the data sparse retrieval will need.

**Retrieval pipeline:**

```text
              Question
                 │
                 ▼
          RetrievalService
                 │
         ┌───────┴───────┐
         ▼               ▼
  DenseRetriever   SparseRetriever
         │               │
         └───────┬───────┘
                 ▼
           FusionService
                 │
                 ▼
         Ranked Documents
```

The RAG pipeline never learns whether retrieval was dense, sparse, or hybrid. It writes one
line and nothing else:

```python
documents = retriever.retrieve(query)
```

> **Engineering Principle**
> Components that run on different lifecycles should not live in the same class.

------------------------------------------------------------------------

### Design Decision #2 — Name the Abstraction After Its Responsibility

The retrieval entry point was first called a **Strategy Selector**. It was renamed to
**RetrievalService**, and the rename was not cosmetic.

"StrategySelector" names an *implementation detail* — that internally there is a strategy,
and something selects it. If tomorrow the choice becomes a config lookup, a capability
check, or a fixed default, the name becomes a lie while the class is still correct.

"RetrievalService" names the **responsibility**: retrieve documents. Dense, sparse, or
hybrid is an internal decision the orchestrator is never entitled to know.

> **Engineering Principle**
> Name a class by what it is responsible for, not by how it currently works. Implementations
> change; responsibilities are what you designed around.

------------------------------------------------------------------------

### Design Decision #3 — Fusion Is Not Retrieval

The obvious design gives `HybridRetriever` three jobs: run dense retrieval, run sparse
retrieval, then fuse the two result sets.

That is a Single Responsibility Principle violation waiting to become a God Class. Ranking
and retrieving change for entirely different reasons.

```text
   Dense Retriever      Sparse Retriever
          │                     │
          └──────────┬──────────┘
                     ▼
              Fusion Service
                     │
                     ▼
               Final Ranking
```

| Benefit | Why it follows from the split |
| --- | --- |
| Easier testing | fusion can be tested on fixed result sets, with no index and no query |
| Easier experimentation | swap the ranking algorithm without touching retrieval |
| Room for future algorithms | Reciprocal Rank Fusion (RRF), Weighted Fusion, Relative Score Fusion (RSF), Cross-Encoder re-ranking |
| No God Class | `HybridRetriever` never accumulates ranking logic it can't shed |

> **Engineering Principle**
> Retrieving candidates and ranking candidates are separate concerns. Do not fuse them into
> one class simply because they run next to each other.

------------------------------------------------------------------------

### Design Decision #4 — Configuration Declares Intent; Runtime Verifies Reality

Both indexing and retrieval read the same application configuration, so the two halves can
never disagree about what the system is supposed to be:

```yaml
retrieval:
    dense: true
    sparse: true
```

That is necessary but not sufficient. Configuration expresses **desired capability**, not
**actual capability**. The retriever must still verify which indexes exist.

```text
Configuration says: Hybrid Enabled
            │
            ▼
Sparse index actually present?
            │
            ├── yes ──►  Dense + Sparse ──►  Fusion
            │
            └── no  ──►  Fall back to Dense Retrieval
```

Production systems should **degrade gracefully rather than fail**. A missing sparse index
should cost retrieval quality, not availability.

> **Engineering Principle**
> Configuration is a statement of intent. Never treat it as proof that the resource exists.

------------------------------------------------------------------------

### The Terminology Correction That Changed the Architecture

The design originally referred to a **BM25 Store** and a **BM25 Index**. That naming is
wrong, and it is wrong at the architectural layer where wrong names become permanent.

**BM25 is a ranking algorithm.** It is not a storage format and not an architectural
component. Naming a component after it bakes today's implementation into the structure of
the system.

| Wrong (implementation-named) | Right (responsibility-named) |
| --- | --- |
| BM25 Store | Sparse Index |
| BM25 Index | Lexical Index |
| BM25Retriever | Sparse Retriever |

The payoff is direct: replacing BM25 with **SPLADE**, or any other sparse retrieval
technique, changes one implementation and zero architectural components.

> **Engineering Principle**
> An architecture that survives implementation changes was named at the right level of
> abstraction. If swapping a library forces you to rename a component, the name was wrong.

------------------------------------------------------------------------

### Responsibilities

| Component | Owns | Explicitly does NOT own |
| --- | --- | --- |
| `DenseIndexer` | generating embeddings, constructing dense indexes | retrieval, persistence decisions |
| `SparseIndexer` | lexical indexing, token statistics | ranking, retrieval |
| `RetrievalService` | selecting retrieval strategy, orchestrating retrieval | ranking fusion, prompt generation |
| `DenseRetriever` | dense similarity search | fusion, filtering |
| `SparseRetriever` | lexical retrieval | fusion, filtering |
| `FusionService` | combining multiple retrieval result sets | performing retrieval |

------------------------------------------------------------------------

### Final Architecture

**Ingestion:**

```text
              Loader
                 │
                 ▼
              Chunker
                 │
                 ▼
              Indexer
                 │
         ┌───────┴───────┐
         ▼               ▼
   DenseIndexer    SparseIndexer
         │               │
         ▼               ▼
   Dense Repo      Sparse Repo
```

**Query:**

```text
              Question
                 │
                 ▼
          RetrievalService
                 │
         ┌───────┴───────┐
         ▼               ▼
  DenseRetriever   SparseRetriever
         │               │
         └───────┬───────┘
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

------------------------------------------------------------------------

### Rejected Alternatives

| Alternative | Why rejected |
| --- | --- |
| Change only the retrieval layer | Sparse indexes must exist before retrieval can use them; ingestion has to change first |
| `HybridRetriever` that retrieves *and* fuses | Merges two reasons to change into one class; becomes a God Class as fusion algorithms multiply |
| Name the component `StrategySelector` | Names an implementation detail rather than a responsibility |
| Name the layer after BM25 | Bakes a ranking algorithm into the architecture; blocks SPLADE and other sparse techniques |
| Trust configuration alone | Config states desired capability, not actual capability; a missing index would crash instead of degrading |

------------------------------------------------------------------------

### Engineering Lessons

1. **Hybrid Search is not a new search method — it is a new indexing pipeline.** The
   retrieval change is the visible half of a two-sided change.
2. **Building indexes and querying indexes are different responsibilities.** Their
   lifecycles differ, so their components should too.
3. **Name classes by responsibility, not implementation.** `RetrievalService` over
   `StrategySelector`.
4. **Fusion is a separate concern.** Do not mix retrieval with ranking.
5. **Configuration defines desired behaviour; the application must still validate runtime
   capability.**
6. **A stable architecture survives implementation changes.** Replacing BM25 with SPLADE
   should change the `SparseRetriever` and nothing above it.

------------------------------------------------------------------------

### Interview Takeaways

**Why isn't dense retrieval sufficient?**

> Dense retrieval matches meaning, which is exactly right for questions like "how do I reset
> my password" where wording differs but the concept matches. It is the wrong tool for exact
> lexical queries — error codes, invoice numbers, SKUs — where the user wants the literal
> token, not something semantically nearby. Those need keyword matching.

**Why does Hybrid Search require ingestion changes?**

> Because retrieval can only query indexes that already exist. A sparse retriever needs a
> sparse index, and that index is built at ingestion time. Hybrid Search is a second
> indexing pipeline first and a second retriever second.

**Why separate indexing from retrieval?**

> They have independent lifecycles. Index construction runs once when documents are
> ingested; retrieval runs on every question. Components with different lifecycles change
> for different reasons and belong in different classes.

**Why introduce a RetrievalService?**

> So the orchestrator depends on one stable contract — `retrieve(query)` — rather than on
> which retrieval strategy is currently in use. Whether the answer came from dense, sparse,
> or hybrid retrieval is an internal decision.

**Why is Fusion a separate service?**

> Retrieving candidates and ranking candidates change for different reasons. Keeping fusion
> separate makes it testable against fixed result sets, lets ranking algorithms be swapped
> independently, and stops `HybridRetriever` from accumulating responsibilities it can never
> give back.

**Why is BM25 an implementation detail rather than an architectural concern?**

> BM25 is a ranking algorithm, not a storage layer. The architectural component is a
> *sparse retriever* over a *sparse index*. Naming it after BM25 would mean that adopting
> SPLADE required renaming architecture instead of replacing one implementation.

**Why should the RAG orchestrator not know which retrieval strategy is used?**

> Because the strategy can change for reasons the orchestrator has no stake in — a config
> flag, a missing index, a new fusion algorithm. If the orchestrator knew, every one of
> those would become an orchestration change.

------------------------------------------------------------------------

### Biggest Takeaway

> **Hybrid Search looked like a retrieval feature. It was an ingestion redesign.**

The lasting result of PR-7 is not that lexical queries work. It is that the system now has a
place to put a *second* way of finding things — and a third, when one is needed — without
the orchestrator, the generation layer, or the UI learning about it.

---

## PR-8 Discussion — Metadata Catalog & Metadata Filtering

### Problem Statement

After PR-7 the system could retrieve semantically **and** lexically. It still searched the
**entire knowledge base** on every question.

```text
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

Real systems rarely search everything. Users restrict searches to specific files,
departments, projects, date ranges, authors, or pages.

The retrievers could not support any of that, because they had no knowledge of:

- which documents exist
- which documents the user selected
- which metadata belongs to which document

And the UI was worse off: once indexing completed, **the uploaded files were forgotten**.
Nothing in the system could answer "what is in the knowledge base?"

> **The engineering problem is not "we need filters."**
> It is: *the system has no representation of its own corpus.*

------------------------------------------------------------------------

### Core Thoughts — What I Believed Going In

The framing I started with was *add a filter argument to retrieval*. That treats a missing
architectural layer as a missing parameter.

The real conclusion was that an entire layer was absent:

> **Metadata Catalog** — the source of truth for the knowledge base.

Without it, the UI asks "what documents exist?" and there is no component whose job it is to
answer. With it, the UI stops guessing and starts asking:

```text
UI  ──►  MetadataCatalog.list_documents()
                    │
                    ▼
            Spring.pdf
            Docker.pdf
            Java.pdf
```

------------------------------------------------------------------------

### Design Decision #1 — What a Metadata Catalog Is (and Is Not)

A Metadata Catalog stores information **about the corpus**, never the contents of the
documents themselves.

| Stores | Does not store |
| --- | --- |
| document identity and display name | embeddings |
| source path and upload time | vectors |
| chunk counts and corpus-level facts | chunks |
| | sparse/BM25 indexes |

```python
{
    "document_id": "doc_001",
    "display_name": "Spring Boot Guide.pdf",
    "source": "/uploads/spring.pdf",
    "uploaded_at": "...",
    "chunk_count": 42
}
```

Its responsibilities are narrow and finite:

- register newly uploaded documents into the catalog
- persist the catalog to disk
- load the catalog from storage
- list available documents
- find document metadata by document ID *(future)*
- delete document metadata *(future)*

Critically, the catalog **does not generate metadata**. It indexes and persists metadata that
already exists on the loaded documents. It knows nothing about retrieval, BM25, FAISS,
embeddings, or prompting.

> **Engineering Principle**
> A component that persists a fact and a component that produces that fact are two
> responsibilities. Conflating them is how storage layers grow business logic.

------------------------------------------------------------------------

### Design Decision #2 — Metadata Does Not Belong in the Vector Store

The tempting shortcut is to keep document information inside the vector store, since it is
already storing something per chunk.

| | Optimised for |
| --- | --- |
| Vector Store | vector similarity search |
| Metadata Catalog | document / corpus management |

These are different responsibilities with different access patterns. Separating them keeps
each storage engine focused on what it is good at, and keeps corpus management alive even if
the vector store is rebuilt or swapped.

------------------------------------------------------------------------

### Design Decision #3 — No `DocumentMetadata` Class

A dedicated `DocumentMetadata` type was considered and rejected.

It would have wrapped a dictionary, added no behaviour, and been used by exactly one class.
That is **YAGNI** — "You Aren't Gonna Need It" — abstraction added for its own sake.

```text
src
│
├── catalog
│     metadata_catalog.py
```

One class was enough.

> **Engineering Principle**
> An abstraction with one caller and no behaviour is not an abstraction. It is indirection.

------------------------------------------------------------------------

### Design Decision #4 — Metadata Is Assigned as Early as Possible

The first proposal let the Metadata Catalog *generate* document metadata. That is the wrong
owner.

The **Document Loader** is the first component that knows:

- which uploaded file produced these documents
- the display name
- the logical identity of the document

So the loader assigns `document_id` and `display_name`. The catalog persists what the loader
already established. Chunking then inherits document metadata and contributes only what it
owns — `chunk_index` and `chunk_id`.

```text
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
                  │
          ┌───────┴───────┐
          ▼               ▼
   EmbeddingService   BM25Indexer
          │               │
          ▼               ▼
    Dense Store      Sparse Store
```

Every chunk now carries:

```python
{
    "document_id": "...",
    "display_name": "...",
    "chunk_index": ...,
    "chunk_id": ...
}
```

That metadata is reused unchanged for the rest of the pipeline.

> **Engineering Principle**
> Metadata should be created by the layer that first *knows* it, and every layer downstream
> should only add what it uniquely owns.

------------------------------------------------------------------------

### Design Decision #5 — The UI Speaks Display Names; the Backend Speaks IDs

Filtering by filename was the first design. It was replaced, for a reason that is a
one-example argument:

```text
HR/Policy.pdf
Finance/Policy.pdf
```

**Filenames are not guaranteed to be unique.** Document IDs are.

So the UI displays one thing and sends another:

```text
☑ Spring Boot Guide.pdf
☑ Docker Guide.pdf
☐ Java Notes.pdf

        display_name
             │
             ▼
        document_id
             │
             ▼
          filters
             │
             ▼
     Retrieval Service
```

```python
filters = {
    "document_ids": ["doc_001", "doc_002"]
}
```

The backend never depends on filenames.

> **Engineering Principle**
> Human-readable labels are a presentation concern. Identity is a backend concern. Never let
> the two be the same value.

------------------------------------------------------------------------

### Design Decision #6 — Filtering Is Its Own Service

Three designs were considered:

| Option | Shape | Verdict |
| --- | --- | --- |
| **A** | Question → Filter → Retriever | rejected |
| **B** | Question → Retriever → Filter | rejected |
| **C** | Each retriever's results → Metadata Filtering → Fusion | **chosen** |

Rather than embedding filtering logic inside each retriever, a dedicated
`MetadataFilteringService` was extracted.

```text
   Dense Retriever          Sparse Retriever
          │                        │
          ▼                        ▼
  Metadata Filtering       Metadata Filtering
          │                        │
          └───────────┬────────────┘
                      ▼
                FusionService
```

| Benefit | Why |
| --- | --- |
| `RetrievalService` stays an orchestrator | it delegates filtering instead of implementing it |
| Retrievers stay focused | `DenseRetriever` and `SparseRetriever` only retrieve |
| Filtering has one implementation | DRY — the rule is not duplicated per retriever |
| Future filters are cheap | pages, authors, departments, tags change exactly one file |

The retrieval contract grew by one argument, and nothing else in the system moved:

```python
# Before
retrieve(query, top_k)

# After
retrieve(query, top_k, filters)
```

------------------------------------------------------------------------

### Retrieval Architecture

```text
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
              │                 │
              ▼                 ▼
      Raw Dense Results   Raw Sparse Results
              └────────┬────────┘
                       ▼
           MetadataFilteringService
                       │
                       ▼
                 FusionService
                       │
                       ▼
                Ranked Documents
                       │
                       ▼
              GenerationService
                       │
                       ▼
                 LLM Response
```

**`GenerationService` never changes. Only retrieval becomes filter-aware.** That is precisely
what a layered architecture is supposed to buy you.

------------------------------------------------------------------------

### What This PR Deliberately Did *Not* Do

PR-8 does **not** implement natural-language filtering. A query like:

```text
Search only Spring.pdf
```

is not interpreted. The UI sends structured filters, and that is the whole scope.

Later, an LLM can translate natural language into exactly the structure that already exists:

```python
{"document_ids": ["doc_001"]}
```

This is why the roadmap says **Self-query Preparation** and not **Self-query Retrieval**.
The groundwork is the deliverable; the interpretation layer is a separate PR.

> **Engineering Principle**
> Building the structured contract first is what makes the natural-language layer a small
> change later. Reversing the order makes both hard.

------------------------------------------------------------------------

### Rejected Alternatives

| Alternative | Why rejected |
| --- | --- |
| Store document info inside the Vector Store | Vector stores are optimised for similarity search, not corpus management |
| A `DocumentMetadata` class | Wraps a dict, adds no behaviour, has one caller — YAGNI |
| Metadata Catalog generates metadata | The loader is the first component that knows document identity; the catalog should only persist |
| Filter by filename | Filenames are not unique (`HR/Policy.pdf` vs `Finance/Policy.pdf`) |
| Filtering inside each retriever | Duplicates the rule per retriever; every new filter type changes multiple files |
| Filter before retrieval (Option A) | Filtering is a decision about *retrieved candidates*, not a pre-retrieval step |
| Natural-language filters in PR-8 | Structured filters must exist before anything can translate into them |

------------------------------------------------------------------------

### Architecture Principles Learned

**Metadata is not retrieval.** Metadata management deserves its own layer, with its own
persistence and its own lifecycle.

**Storage engines have different purposes.**

| Store | Purpose |
| --- | --- |
| Dense Store | similarity search |
| Sparse Store | keyword search |
| Metadata Catalog | corpus management |

Different storage, different responsibility.

**Stable IDs are fundamental.** Everything operates on `document_id`; filenames are for
humans only.

**Filtering is business logic, not storage.** A vector store's job is returning *similar*
documents. Deciding which of those are *eligible* is an application rule. Keeping that rule
out of the storage engine is what lets the storage engine be replaced.

**Layered architecture pays off exactly here.** Metadata filtering extended the retrieval
layer only:

```text
UI  →  RAG  →  Retrieval  →  Fusion  →  Generation
                   ▲
                   └── the only layer PR-8 touched
```

------------------------------------------------------------------------

### What the Catalog Unlocks

The Metadata Catalog makes each of these a small change rather than a redesign: deleting
documents, updating documents, page/author/department filtering, self-query retrieval,
corpus statistics, a knowledge-base dashboard, and incremental indexing.

------------------------------------------------------------------------

### Interview Takeaways

**Why introduce a Metadata Catalog instead of storing everything in the Vector Store?**

> Vector stores are optimised for similarity search; catalogs are optimised for corpus
> management. Separating them follows the Single Responsibility Principle and keeps retrieval
> independent of document management — the catalog survives a vector store rebuild or swap.

**Why should the UI send document IDs instead of filenames?**

> Filenames are not guaranteed to be unique — `HR/Policy.pdf` and `Finance/Policy.pdf` are
> two documents with one name. Document IDs are stable and unique, so filtering is never
> ambiguous. The display name stays a presentation concern.

**Why does the Metadata Catalog run before chunking?**

> Chunking needs a stable `document_id` so every chunk it produces can inherit correct
> document metadata. Assign identity at the loader, persist it in the catalog, and every
> downstream stage adds only the metadata it owns.

**Why isn't filtering implemented inside each retriever, or inside RetrievalService?**

> Inside each retriever it would be duplicated, so every new filter type — pages, authors,
> departments, tags — would change several files. Inside `RetrievalService` it would turn an
> orchestrator into an implementer. A dedicated `MetadataFilteringService` gives the rule one
> home, leaves retrievers focused on retrieval, and keeps `RetrievalService` coordinating.

**Why does the Metadata Catalog not generate metadata?**

> Because the Document Loader is the first component that knows which uploaded file produced
> which documents, and what the document should be called. Producing a fact and persisting a
> fact are different responsibilities.

------------------------------------------------------------------------

### Biggest Takeaway

> **Metadata filtering is not a retrieval feature. It is a corpus management problem.**

The lasting result of PR-8 is a system that knows what it contains. Filters were the visible
outcome; the source of truth was the actual deliverable — and it is the reason deletion,
dashboards, and self-query retrieval are now incremental rather than architectural work.

---

## PR-9 Discussion — Validation Pipeline (Guardrails)

### Problem Statement

Up to PR-8, the pipeline was built around one assumption: **every request should be
processed.** Retrieve, generate, return.

Production AI systems must also answer a prior question:

> Should this request continue through the pipeline at all?

An empty question, a prompt injection attempt, an empty retrieval result, or an empty model
response are all cases where continuing costs money, latency, or safety, and produces
nothing worth returning.

The naive fix is a scatter of `if` checks in `rag.py`, the services, and the UI. PR-9 rejects
that and makes guardrails **first-class architectural components**.

------------------------------------------------------------------------

### The Architectural Shift

**Before:**

```text
Question
    │
    ▼
Retrieval
    │
    ▼
Generation
```

**After:**

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

The pipeline now validates **before**, **during**, and **after** generation.

------------------------------------------------------------------------

### Design Decision #1 — A Guardrail Answers One Question

A guardrail is **not** responsible for talking to the user. It does not render an error, pick
a message colour, or decide what Streamlit shows. It answers exactly one question:

> "Should this request continue?"

| Answer | What happens |
| --- | --- |
| No | return a structured response explaining why |
| Yes | the pipeline proceeds normally |

This is what keeps validation independent of the UI. The same guardrail works behind a
Streamlit page, an HTTP API, or a batch job.

> **Engineering Principle**
> A validator decides; it does not present. The moment a validator formats output for a
> specific UI, it stops being reusable.

------------------------------------------------------------------------

### Design Decision #2 — Every Stage May Terminate the Request

Guardrails are not advisory. Each one has the authority to end the request.

```text
Question
    │
    ▼
Input Guardrails
    │
    ├── Validation Failed? ──►  Return Response
    │
    ▼
Retrieval
    │
    ▼
Context Guardrails
    │
    ├── Validation Failed? ──►  Return Response
    │
    ▼
Generation
    │
    ▼
Output Guardrails
    │
    ├── Validation Failed? ──►  Return Response
    │
    ▼
Final Response
```

This is the **Early Exit Pattern**, and the orchestrator (`rag.py`) does nothing more than
coordinate the stages.

------------------------------------------------------------------------

### Design Decision #3 — One Response Contract, Not Two

The obvious design introduces a separate `GuardrailResult` type alongside
`GenerationResponse`. It was rejected.

Every stage returns the **same** object:

```text
GenerationResponse
```

Whether generation succeeds, validation fails, or context is missing, the caller receives one
type. No `isinstance` checks, no union types, no branching in the UI on which shape came
back.

`GenerationResponse` therefore evolved from *"the result of a successful generation"* into
*"the result of the entire request lifecycle"*, gaining three fields:

| Field | Meaning |
| --- | --- |
| `success` | did the request complete normally |
| `reason` | machine-readable cause when it did not |
| `message` | human-readable explanation |

```text
Successful request              Blocked request
────────────────────            ─────────────────────────────────
success = true                  success = false
answer  = "..."                 reason  = "EMPTY_QUERY"
                                message = "Please enter a question."
```

> **Engineering Principle**
> A stable API contract is worth more than an expressive one. One return type that covers
> every outcome beats several precise types the caller must discriminate between.

------------------------------------------------------------------------

### The Three Validation Layers

Validation responsibilities naturally occur at different stages, each asking a different
question:

| Stage | Runs | Responsibility |
| --- | --- | --- |
| Input | before retrieval | Is the question valid? |
| Context | after retrieval | Is the retrieved knowledge sufficient? |
| Output | after generation | Is the generated response acceptable? |

**Input Guardrails** prevent invalid requests from entering the pipeline at all.

- Today: Empty Question, Prompt Injection Detection
- Later: maximum length, language detection, PII detection, profanity, rate limiting

**Context Guardrails** decide whether retrieval produced enough to generate from.

- Today: Empty Retrieval
- Later: semantic relevance validation, confidence threshold, a helper LLM for context
  verification

**Output Guardrails** validate generated responses before the user ever sees them.

- Today: Empty Response
- Later: groundedness verification, safety classification, hallucination detection, citation
  verification

Separating these keeps each validator focused on one responsibility — and makes it obvious
where a new check belongs.

------------------------------------------------------------------------

### Design Decision #4 — Validation Lives Outside the Services

`GenerationService` is responsible for **generation**. `RetrievalService` is responsible for
**retrieval**. Neither should decide whether processing continues.

If a service could halt the pipeline, it would own two responsibilities: doing its job, and
policing the request. Guardrails keep the second one out.

`rag.py` becomes the orchestration layer and owns only sequencing:

1. run Input Guardrails
2. coordinate Retrieval
3. run Context Guardrails
4. coordinate Generation
5. run Output Guardrails
6. return the final response

Business logic stays distributed across specialised services; `rag.py` holds none of it.

> **Engineering Principle**
> Orchestration is a responsibility in its own right. A class that coordinates should not
> also compute.

------------------------------------------------------------------------

### Extensibility — The Real Test

Adding a new validator requires exactly three things:

1. implement the validator
2. register it in the corresponding guardrail
3. *nothing else*

No change to Retrieval. No change to Generation. No change to the orchestration order. That
is the Open/Closed Principle stated as a diff size.

------------------------------------------------------------------------

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

------------------------------------------------------------------------

### Rejected Alternatives

| Alternative | Why rejected |
| --- | --- |
| A separate `GuardrailResult` type | Forces every caller to discriminate between return types; destroys a stable API contract |
| Validation inside `RetrievalService` / `GenerationService` | Gives each service a second responsibility — doing its job and policing the request |
| Guardrails that render user-facing errors | Couples validation to the UI; the same guardrail could not serve an API or a batch job |
| A single validation step before the pipeline | Context and output problems only become visible *after* retrieval and generation |

------------------------------------------------------------------------

### Engineering Lessons

1. **Deciding whether to process a request is itself a responsibility.** It deserves
   components, not scattered `if` statements.
2. **A validator decides; it does not present.** That separation is what keeps guardrails
   UI-independent.
3. **Early Exit is a pipeline pattern.** Every stage gets the authority to end the request
   and return a complete response.
4. **One response contract beats several precise ones.** `GenerationResponse` covers success,
   rejection, and failure alike.
5. **Validation concerns are stage-specific.** Input, context, and output ask three different
   questions and must not be collapsed into one check.
6. **Extensibility is measured by diff size.** A new validator touches one file and one
   registration.

------------------------------------------------------------------------

### Interview Takeaways

**Why are guardrails architectural components rather than checks inside the services?**

> Because "should this request continue" is a separate responsibility from retrieval and
> generation. If `GenerationService` could halt the pipeline it would own two reasons to
> change. Guardrails keep validation policy in dedicated components and leave each service
> focused on one transformation.

**Why does everything return `GenerationResponse` instead of a dedicated guardrail type?**

> To keep the API contract stable. Whether the request succeeded, was blocked at input, or
> failed on missing context, the caller receives one type with `success`, `reason`, and
> `message`. The UI never branches on which shape came back.

**Why three guardrail layers instead of one?**

> They answer different questions at different times. Input validation asks whether the
> question is valid, and can run before any cost is incurred. Context validation asks whether
> retrieval produced enough to answer from — knowable only after retrieval. Output validation
> asks whether the generated answer is acceptable — knowable only after generation.

**Why shouldn't a guardrail talk to the user?**

> Because it would couple validation to one interface. A guardrail returns a structured
> decision; whichever front end is attached decides how to display it. The same guardrail
> then works behind Streamlit, an HTTP API, or a batch job.

**How much changes when you add a new validator?**

> One new validator implementation and one registration in the relevant guardrail. Retrieval,
> Generation, and the orchestration order are untouched — that is the Open/Closed Principle
> expressed as a diff.

------------------------------------------------------------------------

### Biggest Takeaway

> **PR-9 turned a RAG pipeline into a request-processing pipeline.**

Instead of blindly retrieving and generating, the application now validates every stage of
the request lifecycle before allowing execution to continue — while maintaining a clean
separation of responsibilities. That is much closer to how production AI systems actually
coordinate validation, retrieval, generation, and response handling.

---

## Self-Check

Answer these without looking. If any is shaky, the corresponding section above is the fix.

1. Why does adding a sparse retriever force a change to the *ingestion* pipeline?
2. What is wrong with the name `StrategySelector`, and what is right about `RetrievalService`?
3. Why is BM25 an implementation detail rather than an architectural component?
4. Configuration says hybrid retrieval is enabled, but the sparse index is missing. What
   should happen, and why?
5. What does a Metadata Catalog store, and what does it deliberately not store?
6. Why does the Document Loader assign `document_id` rather than the Metadata Catalog?
7. Give the one-line argument against filtering by filename.
8. Why was `MetadataFilteringService` extracted instead of filtering inside each retriever?
9. Why does the roadmap say "Self-query Preparation" rather than "Self-query Retrieval"?
10. Why does a blocked request return `GenerationResponse` instead of a `GuardrailResult`?
11. Why can't context validation happen at the same time as input validation?
12. Name the one thing each of PR-7, PR-8, and PR-9 changed about *where a responsibility
    lives* — not about what the user sees.

---

### Where Week 2 Left the Architecture

```text
Question
   │
   ▼ Input Guardrails      ← PR-9
   │
   ▼ RetrievalService      ← PR-7 (dense + sparse + fusion)
   │      └── MetadataFilteringService   ← PR-8
   │
   ▼ Context Guardrails    ← PR-9
   │
   ▼ GenerationService
   │
   ▼ Output Guardrails     ← PR-9
   │
   ▼ GenerationResponse
```

Three PRs, zero new features in the product sense, and a pipeline that can now be extended at
every stage without editing the stages around it.

---

**Next:** PR-10 — LCEL composition in the generation layer, and the question of what a
framework should and should not be allowed to own.
