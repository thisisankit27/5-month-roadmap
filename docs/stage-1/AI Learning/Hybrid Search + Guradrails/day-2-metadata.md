# Metadata in RAG

## What is Metadata?

### Crisp Definition

**Metadata is data that describes other data.**

It provides additional information about a data object without being the
primary content itself.

Example:

``` text
Document:
"Spring Boot Security Guide"

Content
--------------------------------
...actual document text...

Metadata
--------------------------------
Author      : Ankit
Department  : Engineering
Project     : Knowledge Base
Language    : English
Created On  : 2026-07-22
Tags         : Spring, Security
```

!!!info "Important"
    >Metadata is **not embedded**. It is stored separately
    > alongside the original document.

------------------------------------------------------------------------

## Types of Metadata

### Technical Metadata

-   File type
-   Size
-   Encoding
-   Creation date
-   Last modified

### Business Metadata

-   Department
-   Owner
-   Project
-   Customer
-   Category

### Process Metadata

-   ETL pipeline
-   Data lineage
-   Processing status
-   Version
-   Source system

------------------------------------------------------------------------

## Metadata in RAG

A document stored in a vector database generally contains:

``` text
Document
│
├── Original Text
├── Embedding Vector
├── Metadata
└── Document ID
```

Example:

``` python
Document(
    page_content="Hybrid Search combines sparse and dense retrieval.",
    metadata={
        "author": "Krish Naik",
        "topic": "RAG",
        "level": "Intermediate"
    }
)
```

Only **page_content** is embedded. Metadata remains structured and
queryable.

------------------------------------------------------------------------

## Metadata Filtering

### Definition

Metadata filtering restricts retrieval to documents that satisfy
metadata conditions **before (or alongside)** vector similarity search.

Example:

``` text
Query
    ↓
Filter: author = "Ankit Srivastava"
    ↓
Candidate Documents
    ↓
Vector Search
    ↓
LLM
```

### Benefits

-   **Precise Retrieval** -- Reduces irrelevant results.
-   **Scalability** -- Searches fewer candidate documents.
-   **Cost Optimization** -- Lower computation and inference cost.
-   **Governance & Compliance** -- Enables role-based access, auditing
    and policy enforcement.

### Challenges

-   Inconsistent tagging
-   Missing metadata
-   Poor schema design
-   Indexing overhead
-   Legacy-system limitations

### Best Practices

-   Define a consistent metadata schema.
-   Automate metadata generation during ingestion.
-   Validate metadata quality.
-   Index frequently filtered fields.
-   Store only meaningful metadata.

------------------------------------------------------------------------

## Metadata Indexing

### Definition

Metadata indexing is the process of organizing metadata into efficient
lookup structures so matching documents can be found quickly.

Without indexing:

``` text
Search
 ↓
Scan every document
```

With indexing:

``` text
Search
 ↓
Metadata Index
 ↓
Matching Documents
```

### Simple Analogy

A textbook index lets you jump directly to "Inheritance" instead of
reading every page.

------------------------------------------------------------------------

## Metadata Filtering vs Metadata Indexing

| Metadata Filtering        | Metadata Indexing                    |
|---------------------------|--------------------------------------|
| Restricts search results  | Makes filtering fast                 |
| Happens during query      | Happens during storage/ingestion     |
| Uses metadata conditions  | Organizes metadata for lookup        |

### Easy way to remember

> **Filtering decides WHAT to search.**

> **Indexing decides HOW FAST it can be found.**

------------------------------------------------------------------------

## Vector Index vs Metadata Index

Production RAG systems often maintain **two different indexes**.

``` text
Document
│
├── Embedding
│      ↓
│  Vector Index
│
└── Metadata
       ↓
 Metadata Index
```

-   **Vector Index** → Used for semantic similarity search.
-   **Metadata Index** → Used for structured filtering.

------------------------------------------------------------------------

## Complete RAG Flow

``` text
                User Query
                     │
         ┌───────────┴───────────┐
         │                       │
   Convert query           Extract metadata
   into embedding          filters (if any)
         │                       │
         └───────────┬───────────┘
                     ▼
            Metadata Filtering
                     │
                     ▼
          Candidate Documents/Chunks
                     │
             Vector Similarity Search
          (only within candidates)
                     │
                     ▼
                Top-K Chunks
                     │
                     ▼
                    LLM
```

The **metadata index and vector index are linked through the same underlying records (chunks)**. 

A chunk stored in a vector database typically looks conceptually like this:

```text
Chunk ID: 1024

Text:
"Employees are entitled to 20 days of annual leave..."

Embedding:
[0.12, -0.43, 0.91, ...]

Metadata:
{
    department: "HR",
    year: 2024,
    document: "Employee Handbook",
    language: "en"
}
```

During ingestion:

```text
                    Chunk
                      │
        ┌─────────────┴─────────────┐
        │                           │
Generate Embedding          Store Metadata
        │                           │
        ▼                           ▼
 Vector Index                Metadata Index
        │                           │
        └──────────┬────────────────┘
                   │
             Same Chunk ID (1024)
```

Notice that **both indexes point to the same chunk ID**.

---

### During query time

Suppose the user asks:

> "Vacation policy for HR employees in 2024"

The system extracts

```text
Semantic query:
"Vacation policy"

Metadata filter:
department = HR
year = 2024
```

Now the metadata index is queried first.

```text
Metadata Index

department=HR
year=2024

↓ returns

Chunk IDs

1024
2056
3901
4812
...
```

It does **not** return embeddings. It returns the **identifiers** of chunks satisfying the filter.

---

### Then comes vector search

The vector engine receives something like

```text
Query Embedding

Search only among:

1024
2056
3901
4812
```

Instead of searching every embedding in the database, it only computes similarity against the embeddings of those chunk IDs.

Conceptually:

```text
Query Embedding
       │
       ▼
Vector Index

Search Space =
{1024,2056,3901,4812}

↓

Similarity

1024 → 0.94
3901 → 0.89
2056 → 0.82
4812 → 0.77
```

Return Top-K:

```text
1024
3901
2056
```

---

### Is the metadata index "mapped" to the vector index?

Yes, although "mapped" isn't usually the term used. A better way to think about it is:

```text
Chunk
   │
   ├── Embedding
   ├── Metadata
   └── Chunk ID
```

Both indexes know about the **same Chunk ID**.

So the flow is:

```text
Metadata Filter
       │
       ▼
Candidate Chunk IDs
       │
       ▼
Vector Search
(using embeddings of only those IDs)
       │
       ▼
Top-K Chunks
       │
       ▼
LLM
```

---

## How real vector databases implement this

Databases like **Pinecone**, **Weaviate**, **Qdrant**, **Milvus**, and **Chroma** don't usually execute two completely separate queries internally.

Instead, when you issue a query like:

```python
vector_db.search(
    query_embedding=...,
    filter={
        "department": "HR",
        "year": 2024
    },
    top_k=5
)
```

the engine internally does something equivalent to:

1. Apply the metadata filter to determine the eligible chunk IDs.
2. Restrict the ANN (Approximate Nearest Neighbor) search to those IDs.
3. Compute vector similarity only within that filtered subset.
4. Return the top-k matching chunks.

So yes—the metadata index effectively **gates** which vectors are eligible for similarity search by using the shared chunk identifiers. This tight integration is what makes filtered vector search both efficient and accurate.

------------------------------------------------------------------------

## Interview Q&A

###. What is metadata?

Metadata is data that describes other data and provides context such as
author, source, language, department or creation date.

------------------------------------------------------------------------

### Is metadata embedded?

No. Only the document content is converted into embeddings. Metadata is
stored separately for filtering and retrieval.

------------------------------------------------------------------------

### Why use metadata filtering in RAG?

To reduce the search space, improve retrieval precision, reduce
computation cost and enforce business or security constraints.

------------------------------------------------------------------------

### Give examples of metadata.

-   Author
-   Source
-   Department
-   Language
-   Customer
-   Project
-   Tags
-   Access Level

------------------------------------------------------------------------

### What is metadata indexing?

Metadata indexing organizes metadata into indexes so matching documents
can be found quickly without scanning the full dataset.

------------------------------------------------------------------------

### Filtering vs indexing?

Filtering decides **what** documents to search.

Indexing determines **how quickly** those documents can be found.

------------------------------------------------------------------------

### Why is metadata useful in enterprise RAG?

It enables tenant isolation, access control, governance, compliance and
faster retrieval.

------------------------------------------------------------------------

### What happens if metadata is inconsistent?

Filtering becomes unreliable, relevant documents may be missed and
retrieval quality decreases.

------------------------------------------------------------------------

### Does metadata improve semantic understanding?

No. Semantic understanding comes from embeddings. Metadata provides
structured constraints.

------------------------------------------------------------------------

### Where is metadata stored?

Alongside the original document text, embedding vector and document ID.

------------------------------------------------------------------------

## Common Interview Traps

❌ Metadata is embedded.

✔ Only document content is embedded.

------------------------------------------------------------------------

❌ Metadata filtering and vector search are the same.

✔ Metadata filtering uses structured fields. Vector search compares
embeddings.

------------------------------------------------------------------------

❌ Indexing always refers to embeddings.

✔ Production systems often maintain both vector indexes and metadata
indexes.

------------------------------------------------------------------------

❌ Metadata always improves search.

✔ Only when it is accurate and consistently maintained.

------------------------------------------------------------------------

## Remember These Forever

1.  Metadata = **data about data**.
2.  Metadata is **not embedded**.
3.  Metadata filtering reduces the candidate search space.
4.  Metadata indexing makes filtering efficient.
5.  Filtering decides **what** to search.
6.  Indexing decides **how fast** it can be found.
7.  Enterprise RAG relies heavily on metadata for security, governance
    and multi-tenant retrieval.

------------------------------------------------------------------------

# Stage 1 · Week 2 Checklist

- Explain metadata.
- Explain metadata filtering.
- Explain metadata indexing.
- Explain filtering vs indexing.
- Explain vector index vs metadata index.
- Explain why metadata is not embedded.
- Draw the metadata-aware RAG pipeline from memory.
