# Thinking Like a Senior Engineer.v1

> These notes are not about AI or LangChain.
>
> They are lessons learned while designing the Knowledge Assistant project — an attempt to
> learn *how experienced engineers think* before writing code.

Week 1 builds the ingestion half of a RAG system: load, chunk, embed, and prepare for
storage. Almost none of the difficulty turned out to be in the libraries. It was in
answering one question over and over, at every layer:

> Who owns this responsibility — and how much has to change when the requirements change?

---

## Principle 1 — Design Before Code

Before writing anything, four questions:

- What problem am I solving?
- What responsibilities exist?
- Which components should own those responsibilities?
- Can this design scale in the future?

> **Engineering Principle**
> Good software is designed first and implemented second.

---

## PR-1 Discussion — Project Foundation

### Goal

Create a clean project foundation.

Not a RAG system. Not a polished SaaS. Simply a project that another engineer can clone and
immediately understand.

That is a deliberately small goal, and treating it as a real deliverable — rather than
scaffolding to rush through — is what made every later PR cheap.

------------------------------------------------------------------------

### Why Separate Modules Instead of Everything in `app.py`?

**My answer at the time:** Separation of Concerns. The architecture should be plug-and-play.
Each module exposes a contract, so implementations can change without affecting other
modules.

```text
Today                Tomorrow
─────                ────────
FAISS      ──────►   Qdrant
```

Only the implementation changes. The rest of the application is unaffected.

**The sharper version of the same answer** — the one that belongs in an interview:

> Each module has a single responsibility and exposes a clear contract. That allows
> implementations to be replaced — FAISS to Qdrant — without touching the orchestration
> layer, because the application depends on abstractions rather than concrete
> implementations.

Same idea. The second version names the mechanism instead of describing the feeling.

------------------------------------------------------------------------

### If We Replace FAISS with Qdrant, How Many Files Change?

**My initial answer:** two files — `embeddings.py` and `vectorstore.py`.

**The correction:** only `vectorstore.py`.

The embedding model has no knowledge of where vectors are stored. Its responsibility is
exactly one transformation:

```text
Text  ──►  Embedding Vector
```

Storage is somebody else's problem. Once that boundary is real, swapping the vector database
cannot reach into embedding code, because embedding code was never told the database exists.

Including `embeddings.py` in the answer was the tell: I had assumed a coupling that the
design did not actually require.

> **Engineering Principle**
> Never let one module know unnecessary implementation details about another. The number of
> files a change touches is a direct measurement of how well the boundaries were drawn.

------------------------------------------------------------------------

### Why Many Small Pull Requests Instead of One Huge PR?

**My answer:** easier collaboration, manageable reviews, better testing, incremental
delivery, quicker feedback, sprint-based development.

**The lesson underneath it** — imagine a bug appears:

| | 7000 changed lines | `PR-09 — Introduced Guardrails` |
| --- | --- | --- |
| Review | practically impossible | a single reviewable idea |
| Rollback | reverts everything | reverts one capability |
| Debug | which of 40 changes did it? | the surface is already named |

> **Engineering Principle**
> Each PR should represent one engineering milestone — not simply "more code."

------------------------------------------------------------------------

### Module Responsibilities

The initial design:

```text
loaders.py       →  Load documents
splitter.py      →  Split documents
embeddings.py    →  Generate embeddings
vectorstore.py   →  Store and retrieve vectors
rag.py           →  Orchestrate everything
```

The discussion that followed surfaced something the file list hides: **uploading documents
and answering questions are two completely different workflows**, and they share almost
nothing but data types.

**Workflow 1 — Knowledge Ingestion:**

```text
PDF
 │
 ▼
Loader
 │
 ▼
Splitter
 │
 ▼
Embeddings
 │
 ▼
Vector Store
```

**Workflow 2 — Question Answering:**

```text
Question
 │
 ▼
Retriever
 │
 ▼
Prompt
 │
 ▼
LLM
 │
 ▼
Answer
```

Recognising this early is what later allowed indexing and retrieval to evolve on independent
lifecycles instead of tangling.

------------------------------------------------------------------------

### The Extensibility Problem in `loaders.py`

Today `loaders.py` supports PDF. Tomorrow it needs PDF, Word, Markdown, Website, and
PowerPoint.

Should the code keep growing this?

```python
if pdf:
    ...
elif docx:
    ...
elif md:
    ...
elif website:
    ...
```

No. Every new format edits the same block for an unrelated reason, and the block is reachable
from anywhere that loads a file.

**My initial idea:** a parent class, child classes, and Inversion of Control — with the
frontend determining the appropriate loader and passing it to the backend.

**The correction:** the frontend should never know backend implementation details.

The frontend uploads `resume.pdf`. That is the entirety of what it knows. The backend decides
everything else:

```text
Uploaded File
      │
      ▼
  Extension
      │
      ▼
LoaderFactory
      │
      ▼
  PdfLoader
      │
      ▼
   load()
```

**Better design:**

```text
                   Uploaded File
                         │
                         ▼
                   LoaderFactory
                         │
                         ▼
                  DocumentLoader
                         ▲
        ┌────────────────┼────────────────┐
        │                │                │
   PdfLoader        DocxLoader        WebLoader
```

The frontend knows one verb: **upload**. Everything else is backend responsibility.

------------------------------------------------------------------------

### Design Principles Accidentally Learned

Without setting out to study design patterns, this one discussion produced:

- Separation of Concerns
- Single Responsibility Principle
- Dependency Inversion thinking
- Open/Closed Principle
- Polymorphism
- Factory Pattern (conceptually)

> **Engineering Principle**
> Don't memorize design patterns. Build enough projects and you'll rediscover them yourself.
> Learning the official names afterwards turns memorization into recognition.

------------------------------------------------------------------------

### Interview Takeaways

**Why use a Factory instead of writing `if extension == "pdf"` everywhere?**

> A Factory centralizes object creation. Adding support for a new document type means
> creating a new implementation and registering it, rather than modifying multiple parts of
> the application. That is the Open/Closed Principle in practice.

**Why separate modules instead of one `app.py`?**

> Each module has a single responsibility and exposes a clear contract, so implementations
> can be replaced without affecting the orchestration layer. The application depends on
> abstractions, not concrete implementations.

**Why should the frontend not choose the loader?**

> Because that would make the UI depend on backend implementation details. The frontend's
> only knowledge should be that a file was uploaded; deciding *how* to read it is a backend
> responsibility that changes far more often.

------------------------------------------------------------------------

### Open Questions Carried into PR-2

Three questions were left deliberately unanswered, to be reasoned about before any code was
written:

1. What methods should the parent `Loader` define — only `load()`, or more?
2. Should `LoaderFactory` return `PdfLoader` or `Loader`? Why?
3. When `ExcelLoader` is added tomorrow, how many existing files should require modification?

If the answer to (3) is *"one registration point"* or close to it, the architecture is
becoming extensible.

------------------------------------------------------------------------

### Biggest Takeaway

> **"If the requirements change tomorrow, how much of my code will I need to rewrite?"**

The best software is not the one that works today. The best software is the one that is
easiest to change tomorrow.

---

## PR-2 Discussion — Designing an Extensible Loader Architecture

> These answers come from engineering principles — **SOLID**, Separation of Concerns, the
> Open/Closed Principle — rather than from what makes the code "work."

### Question 1 — What Methods Should the Parent `Loader` Define?

**Initial thought:** every loader only needs one method.

```python
load()
```

After all, a PDF loader loads PDFs, a Word loader loads Word documents, a Markdown loader
loads Markdown files — and all of them ultimately return LangChain `Document` objects.

**That instinct was correct, and it is worth knowing *why* it was correct.**

The parent class should define **only the behaviour every loader is guaranteed to support**.
For this project, that is exactly `load()`.

```text
Loader
│
├── load()
│
├── PdfLoader
├── DocxLoader
├── MarkdownLoader
└── WebLoader
```

Every child knows **how** to load its own document type. The parent guarantees only **that**
it can be loaded.

#### Why Not Define More Methods?

Suppose the parent also declared:

```python
validate()
extract_images()
extract_tables()
```

The problem appears immediately:

| Loader | The method that makes no sense |
| --- | --- |
| `WebLoader` | `extract_images()` — may not support image extraction |
| `MarkdownLoader` | `extract_tables()` — may contain no tables |
| `TxtLoader` | `validate()` — may require no validation |

Every child is now forced to implement methods that are meaningless for it — usually as an
empty body or a raised exception, both of which are lies about the contract.

That is a violation of the **Interface Segregation Principle**.

> **Engineering Principle**
> A parent class should define only the common contract shared by every implementation. If
> every loader can guarantee exactly one operation, then one operation is enough — don't
> force child classes to implement methods they don't need.

------------------------------------------------------------------------

### Question 2 — Should `LoaderFactory` Return `PdfLoader` or `Loader`?

The Factory should always return the **parent type**, `Loader`.

#### ❌ Returning Concrete Classes

```text
                Uploaded File
                      │
                      ▼
              LoaderFactory.create()
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
     PdfLoader               DocxLoader
          │                       │
          ▼                       ▼
     Client Code            Client Code
```

The client now has to know every implementation:

```python
if isinstance(loader, PdfLoader):
    loader.load()

elif isinstance(loader, DocxLoader):
    loader.load()
```

Note how absurd this is: **both branches call the same method.** The type check buys nothing
and costs a client edit for every new loader ever added.

#### ✔ Returning the Parent Type

```text
                Uploaded File
                      │
                      ▼
              LoaderFactory.create()
                      │
                      ▼
                 Loader (reference)
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
 PdfLoader      DocxLoader      ExcelLoader
      │               │                │
      └───────────────┴────────────────┘
                      │
                      ▼
                   load()
```

The client never learns the actual implementation:

```python
loader = LoaderFactory.create(file)
documents = loader.load()
```

#### Why This Matters

Suppose `PdfLoader` is replaced by, or joined by, `BetterPdfLoader`.

| Does it change? | Answer |
| --- | --- |
| Client code | No |
| The Factory | Only enough to know about the new loader — or not even that, with auto-registration |

This is what **programming to abstractions rather than implementations** actually buys.

> **Engineering Principle**
> Depend on abstractions, not concrete classes. That is the core of the **Dependency
> Inversion Principle**.

------------------------------------------------------------------------

### Question 3 — Adding `ExcelLoader`: How Many Files Should Change?

As close to **one** as possible.

If adding a new document type required editing `loader.py`, `rag.py`, `app.py`,
`splitter.py`, and `embeddings.py`, the architecture would be tightly coupled — and the
coupling would compound with every format added.

Instead, adding a feature should be:

1. create a new implementation (`ExcelLoader`)
2. register it with the Factory

Everything else continues working.

```text
Before                     Tomorrow
──────                     ────────
Loader                     Loader
│                          │
├── PdfLoader              ├── PdfLoader
├── DocxLoader             ├── DocxLoader
└── MarkdownLoader         ├── MarkdownLoader
                           └── ExcelLoader
```

#### Why This Is Valuable

Imagine six months out, with the product supporting PDF, Word, Markdown, PowerPoint, Excel,
CSV, HTML, and websites. If each of those eight formats had required changing five existing
files, the project would already be unmaintainable.

Instead, every new format should be:

> **Add a class. Register it. Done.**

> **Engineering Principle — Open/Closed**
> Software entities should be **open for extension** but **closed for modification**. We
> extend the application by adding new classes, not by constantly modifying existing ones.

#### Visual Architecture

```text
                 Uploaded File
                       │
                       ▼
                 LoaderFactory
                       │
                       ▼
                Loader (abstract)
                       ▲
       ┌───────────┬───┴───────┬───────────┐
       │           │           │           │
  PdfLoader   DocxLoader  MarkdownLoader  ExcelLoader
```

The application communicates only with the parent type. Every concrete loader is hidden
behind the Factory.

------------------------------------------------------------------------

### Interview Takeaways

**Why should the parent `Loader` expose only `load()`?**

> Because it should define only the behaviour common to every loader. Adding extra methods
> forces child classes to implement responsibilities they may not support — a `WebLoader`
> with `extract_images()`, a `MarkdownLoader` with `extract_tables()` — which violates the
> Interface Segregation Principle.

**Why should the Factory return `Loader` instead of `PdfLoader`?**

> Because client code should depend on abstractions rather than concrete implementations.
> Returning the concrete type pushes `isinstance` checks into the client and forces a client
> edit for every new loader, even though every branch calls the same method.

**How many files should change when adding `ExcelLoader`?**

> One new class, plus one registration in the Factory — or even zero registration with
> auto-discovery. Everything else should continue working without modification.

------------------------------------------------------------------------

### Biggest Takeaway

> **The goal of good architecture is not to reduce the amount of code.**
> It is to reduce the amount of *existing* code that must change when requirements evolve.

The easiest code to maintain is the code you don't have to touch.

---

## PR-3 Discussion — Chunking Engine

> The engineering discussions, design decisions, interview answers, and architectural
> reasoning behind the Chunking Engine.

### Pipeline Evolution

**After PR-2:**

```text
PDF
 │
 ▼
Loader
 │
 ▼
List<Document>
```

**After PR-3:**

```text
PDF
 │
 ▼
Loader
 │
 ▼
List<Document>
 │
 ▼
Chunking Engine
 │
 ▼
List<Document> (Chunks)
```

Notice what did **not** happen: the pipeline grew, and `app.py` was never modified.
`ingestion.py` absorbs each additional stage.

------------------------------------------------------------------------

### Should `app.py` Know About Chunking?

No. `app.py` should remain completely unaware of the internal pipeline. It calls one thing:

```python
documents = ingest_documents(uploaded_files)
```

Meanwhile the pipeline behind that call keeps growing:

```text
Today        Tomorrow        Later           Eventually
─────        ────────        ─────           ──────────
Load         Load            Load            Load
             ↓               ↓               ↓
             Chunk           Chunk           Chunk
                             ↓               ↓
                             Embed           Embed
                                             ↓
                                             Vector Store
```

**The caller never changes.** That is one of the biggest responsibilities of an orchestration
layer.

------------------------------------------------------------------------

### Why Have an Ingestion Pipeline at All?

Think of it as a workflow orchestrator with a very clear division of knowledge:

```text
app.py           "I have files."
   │
   ▼
ingestion.py     "I know exactly how to process them."
```

The orchestration layer coordinates all stages while keeping the UI completely decoupled from
implementation details.

------------------------------------------------------------------------

### Should Chunking Use the Strategy Pattern?

**Initial thought:** yes — introduce an abstract `Splitter` so different splitting algorithms
could be swapped without affecting the rest of the application.

```text
Splitter (abstract)
        ▲
        │
RecursiveSplitter
```

Possible future strategies: `RecursiveCharacterTextSplitter`, `MarkdownHeaderTextSplitter`,
`PythonCodeTextSplitter`, `HTMLHeaderTextSplitter`, `SemanticChunker`. All share the same
goal — `List<Document> → Chunks` — and differ only in algorithm. Textbook Strategy Pattern.

**Why not do it today?** The project supports exactly one splitter,
`RecursiveCharacterTextSplitter`. There is no runtime decision to make. Adding the
abstraction now would add complexity without solving an existing problem.

So PR-3 kept it direct:

```text
splitter.py  →  split_documents(documents)
```

Later, when multiple chunking algorithms genuinely exist, refactor to Strategy.

> **Engineering Principle**
> Design for extension. Implement for today's requirements.

*(This deferral did not last long — see the next section, where a real requirement made
Strategy necessary within the same PR.)*

#### Factory vs Strategy

| | Question it answers | Example |
| --- | --- | --- |
| **Factory** | *Which object should I create?* | `UploadedFile → LoaderFactory → PdfLoader` |
| **Strategy** | *Which algorithm should I execute?* | `Documents → Chunk Strategy → Recursive Splitter` |

Factory creates objects. Strategy chooses algorithms.

------------------------------------------------------------------------

### Why `RecursiveCharacterTextSplitter`?

Many developers assume it simply splits by character count. It actually tries to preserve
**semantic boundaries**, falling back through separators in order:

```text
Paragraph  (\n\n)
    │  fails to fit?
    ▼
Line       (\n)
    │  fails to fit?
    ▼
Space      (" ")
    │  fails to fit?
    ▼
Character
```

It only moves to a smaller boundary when a larger one fails, which minimises broken sentences
and incomplete thoughts.

------------------------------------------------------------------------

### Why Not Split by Pages?

Page splitting looks attractive because a page usually contains related information. But
**pages are presentation boundaries, not semantic boundaries**.

```text
Page 17                             Page 18
────────────────────────────        ────────────────────────────
Spring Boot provides dependency ──► ...Injection and IoC...
```

One logical concept now spans two chunks, and retrieval quality drops. The problem cuts both
ways:

- one page may contain many unrelated topics
- one topic may span multiple pages

Therefore page boundaries should not define chunk boundaries.

------------------------------------------------------------------------

### Why Chunk at All?

Embedding an entire document produces a single semantic representation of the whole thing.

| Problem | Consequence |
| --- | --- |
| Retrieval becomes coarse | you get "the document", not "the answer" |
| Embedding is an average of meanings | specific topics get washed out |
| Context window may overflow | the whole document must be sent to the LLM |
| Higher token cost | you pay for text the question never needed |
| Lower answer precision | the model has to find the answer inside noise |

Chunking replaces *retrieve the entire book* with *retrieve the relevant sections*, producing
smaller prompts, lower token usage, better retrieval precision, and more focused answers.

------------------------------------------------------------------------

### Why Overlap?

Consider a concept that lands exactly on a boundary:

```text
Chunk 1                              Chunk 2
──────────────────────────────       ──────────────────────────────
Spring Boot provides dependency      injection, allowing loose coupling...
```

"Dependency injection" has been split in half. Similarity search may fail to match either
chunk, because neither one contains the concept.

Overlap duplicates a small portion of adjacent chunks:

```text
Chunk 1                              Chunk 2
──────────────────────────────       ──────────────────────────────
...dependency injection              dependency injection allows...
```

Now either chunk carries enough context to be retrieved. Overlap preserves semantic
continuity across chunk boundaries.

------------------------------------------------------------------------

### How Should Chunk Size Be Chosen?

There is no universally correct value. Chunk size is a balance of competing pressures:

| Factor | Pushes chunks smaller | Pushes chunks larger |
| --- | --- | --- |
| LLM context window | smaller prompts fit more chunks | — |
| Retrieval precision | more precise matches | — |
| Context preservation | — | fewer truncated ideas |
| Token cost | lower prompt cost | — |
| Embedding model | some models favour short text | others preserve context better when longer |

And the documents themselves change the answer entirely:

| Document type | Split after |
| --- | --- |
| Python code | classes, methods, functions — never inside a method |
| Markdown | headings, sections |
| HTML | DOM sections, headers |
| Plain text | `RecursiveCharacterTextSplitter` is generally suitable |

------------------------------------------------------------------------

### Metadata Survives Chunking

**Before chunking:**

```python
Document(
    page_content="...",
    metadata={
        "source": "...",
        "page": 5
    }
)
```

**After chunking:**

```python
Document(
    page_content="Smaller chunk...",
    metadata={
        "source": "...",
        "page": 5
    }
)
```

The **`Document` type does not change**. Only `page_content` becomes smaller; metadata is
inherited.

Metadata can also become richer over time:

```json
{
  "source": "spring.pdf",
  "page": 5,
  "chunk": 3,
  "section": "Dependency Injection",
  "language": "en"
}
```

which is what later enables filtering, tracing, debugging, citation, and advanced retrieval.

------------------------------------------------------------------------

### The Pipeline Carries One Type

Throughout the pipeline the same `Document` object flows forward. Only its contents evolve:

```text
Document
   │
   ▼
Loaded Document
   │
   ▼
Chunked Document
   │
   ▼
Embedded Document
   │
   ▼
Stored Vector
```

Keeping the type consistent is what makes each downstream stage simple — no stage has to
translate between shapes before it can do its own work.

> **Engineering Principle**
> A stable data contract between pipeline stages is worth more than a perfectly specialised
> type at each stage.

------------------------------------------------------------------------

### Interview Takeaways

**Why `RecursiveCharacterTextSplitter`?**

> It preserves semantic boundaries by recursively trying progressively smaller separators —
> paragraph, line, space, character — before falling back to raw character splitting. That
> produces more meaningful chunks than fixed-size splitting.

**Why overlap?**

> Overlap duplicates context near chunk boundaries into adjacent chunks, so a concept split
> across a boundary still appears whole in at least one chunk and remains retrievable.

**How do you choose chunk size?**

> It is a tradeoff between retrieval precision, context preservation, embedding quality, the
> LLM context window, token cost, and the structure of the underlying documents. There is no
> universally optimal value.

**Why not chunk by page?**

> Pages are presentation boundaries, not semantic ones. A single topic can span two pages and
> a single page can hold several unrelated topics, so page boundaries systematically cut
> concepts in half.

------------------------------------------------------------------------

### Biggest Takeaway

> **A production RAG pipeline is not about LangChain APIs. It is about information flowing
> through well-separated stages.**

```text
Upload  →  Load  →  Chunk  →  Embed  →  Store  →  Retrieve  →  Generate
```

Each stage should have a single responsibility and expose a stable interface to the next.

---

## PR-3 Deep Dive — Design Patterns That Emerged

> The engineering decisions behind introducing the **Strategy Pattern** and **Flyweight
> Pattern** in the ingestion pipeline.
>
> The goal is **not** to memorize design patterns. It is to understand **why** they naturally
> emerge while solving software engineering problems.

### Project Evolution

```text
PR-1                PR-2                        PR-3
────                ────                        ────
User                User                        User
 │                   │                           │
 ▼                   ▼                           ▼
UI                 Upload                      Upload
                     │                           │
                     ▼                           ▼
              Loader Factory                  Loader
                     │                           │
                     ▼                           ▼
                 PdfLoader                   Documents
                     │                           │
                     ▼                           ▼
                 Documents                  Chunk Service
                                                 │
                                                 ▼
                                            Chunk Strategy
                                                 │
                                                 ▼
                                              Chunks
```

| PR | Introduced |
| --- | --- |
| PR-2 | Factory Pattern, Polymorphism, Abstract Classes |
| PR-3 | Strategy Pattern, Flyweight Pattern, better Separation of Concerns |

------------------------------------------------------------------------

### Why the Strategy Pattern Became Necessary

Initially the project supported only PDFs, and one splitter was enough:

```text
PDF  →  RecursiveCharacterTextSplitter
```

Then the requirement changed: the application should support PDF, Markdown, Python, HTML, and
TXT. Should every file use `RecursiveCharacterTextSplitter`?

No. **Different document types require different chunking algorithms.**

| Document type | Preferred chunking |
| --- | --- |
| PDF | `RecursiveCharacterTextSplitter` |
| Markdown | `MarkdownHeaderTextSplitter` |
| Python | `PythonCodeTextSplitter` |
| HTML | `HTMLHeaderTextSplitter` |

The **behaviour varies at runtime**. That is exactly the condition Strategy solves — and it is
exactly the condition that was *absent* when Strategy was deferred earlier in this PR. The
pattern did not become correct because it is famous; it became correct because a real
requirement made behaviour vary.

------------------------------------------------------------------------

### The Strategy Pattern

Instead of scattering this through the project:

```python
if extension == ".pdf":
    ...
elif extension == ".py":
    ...
elif extension == ".md":
    ...
```

each algorithm is encapsulated in its own class behind one interface:

```text
                 Strategy (abstract)
                         ▲
      ┌──────────────────┼──────────────────┐
      │                  │                  │
RecursiveStrategy  PythonStrategy   MarkdownStrategy
```

Every strategy exposes exactly the same method:

```python
chunk(document)
```

The caller never knows which implementation runs.

**Without Strategy**, every new algorithm modifies existing code:

```text
Chunk Service
     │
     ├── if PDF        →  Recursive
     ├── else if .py   →  Python Splitter
     └── else if .md   →  ...
```

**With Strategy**, the Chunk Service never changes:

```text
Chunk Service
     │
     ▼
Strategy Factory
     │
     ▼
Correct Strategy
     │
     ▼
chunk(document)
```

------------------------------------------------------------------------

### Factory and Strategy Solve Different Problems

This project uses **both**, and confusing them is a common interview failure.

| | Question | Responsible for | Example |
| --- | --- | --- | --- |
| **Factory** | Which object should I create? | object creation | `Uploaded File → LoaderFactory → PdfLoader` |
| **Strategy** | Which algorithm should execute? | behaviour | `Document → StrategyFactory → RecursiveChunkStrategy → chunk()` |

They compose naturally:

```text
Chunk Service
     │
     ▼
Strategy Factory      ← chooses the appropriate strategy
     │
     ▼
Strategy              ← executes the algorithm
     │
     ▼
LangChain Splitters
```

------------------------------------------------------------------------

### Responsibilities

**Chunk Service** owns orchestration only:

| Owns | Explicitly does NOT own |
| --- | --- |
| iterating over `Document`s | knowing chunking algorithms |
| asking the Factory for the right strategy | performing splitting |
| aggregating chunks | inspecting file types |

**Strategy Factory** owns one mapping: given a `Document`, return the correct chunk strategy.

```text
.pdf  →  RecursiveChunkStrategy
.py   →  PythonChunkStrategy
.md   →  RecursiveChunkStrategy
```

Note the third row. **Multiple document types may reuse the same strategy** — the factory
maps to *algorithms*, not to document types. Those are different things, and conflating them
would create a strategy class per extension for no reason.

------------------------------------------------------------------------

### Why Choose the Strategy Per Document?

A user may upload:

```text
resume.pdf
main.py
README.md
```

in a single batch. Each needs a different chunking algorithm.

```text
ChunkService
     │
     ▼
for each Document
     │
     ▼
StrategyFactory
     │
     ▼
Correct Strategy
```

If the strategy were selected once per upload batch, mixed uploads would be impossible.

> **Engineering Principle**
> Choose the strategy at the **smallest unit where behaviour actually varies**. Here that
> unit is one `Document`, not one upload.

------------------------------------------------------------------------

### Why `split_documents()` Instead of `split_text()`?

The first instinct was:

```python
split_text(document.page_content)
```

**Problem:** metadata would be lost. `split_text` takes a string and returns strings — the
`Document` wrapper, and everything it carried, is discarded at the boundary.

```python
split_documents([document])   # returns List[Document]
```

Each chunk inherits its parent's metadata automatically:

```python
# Before
Document(page_content="...",          metadata={"source": "spring.pdf", "page": 7})

# After chunking
Document(page_content="Smaller chunk", metadata={"source": "spring.pdf", "page": 7})
```

That metadata is what later makes traceability, filtering, and citation possible. Reaching
for `page_content` would have silently thrown it away at the very first stage.

------------------------------------------------------------------------

### The Flyweight Pattern

Once Strategy was implemented, a second observation followed: `StrategyFactory.create()` was
constructing a fresh object for every single document.

```text
Document 1  →  RecursiveChunkStrategy()
Document 2  →  RecursiveChunkStrategy()
Document 3  →  RecursiveChunkStrategy()
```

That is unnecessary, because **the strategy stores no state**.

**Flyweight solution** — the Factory owns reusable instances and hands out the same object:

```text
StrategyFactory
│
├── RecursiveChunkStrategy    ← one instance, shared
├── PythonChunkStrategy
└── MarkdownChunkStrategy
```

#### Why It Works Here

The strategy takes everything it needs as an argument:

```python
chunk(document)        # not  self.document
```

With no mutable instance state, the same object can safely process PDF A, then PDF B, then
PDF C — including concurrently.

#### When Flyweight Would *Not* Work

Suppose the strategy stored configuration:

```python
self.chunk_size = 500
```

and another request changed it to `1000`. Every user now shares one mutable object, and
behaviour becomes non-deterministic in a way that is extremely hard to reproduce.

> **Engineering Principle**
> Flyweight requires shared objects to be effectively immutable or stateless. Sharing a
> stateful object is not an optimisation; it is a race condition.

#### Why Implement It Anyway?

Honestly: in production this is probably unnecessary. Creating one strategy object is
extremely cheap, and the memory saved is negligible.

This project is primarily for learning, and implementing Flyweight taught object sharing,
stateless service design, object lifecycle, and memory optimisation patterns — plus the far
more valuable inverse lesson above about when sharing becomes dangerous.

------------------------------------------------------------------------

### Future Improvement

The extension-to-strategy mapping is currently hardcoded:

```text
.pdf  →  Recursive Strategy
```

It could instead be configuration:

```yaml
chunking:
  pdf: recursive
  md: recursive
  py: python
  html: html
```

The Factory would read the mapping rather than hardcode it, and supporting a new file type
would require no source code change at all.

------------------------------------------------------------------------

### Design Principles Applied

| Principle | How it shows up here |
| --- | --- |
| **Single Responsibility** | Chunk Service orchestrates, Strategy chunks, Factory creates strategies — one reason to change each |
| **Open/Closed** | Adding `SemanticChunkStrategy` means one new class plus a Factory entry; existing strategies are untouched |
| **Dependency Inversion** | Chunk Service depends on `Strategy`, never on `RecursiveChunkStrategy` |

------------------------------------------------------------------------

### Final Architecture

```text
                     Upload
                        │
                        ▼
                 Loader Factory
                        │
                        ▼
                    Documents
                        │
                        ▼
                  Chunk Service
                        │
                        ▼
                 Strategy Factory
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
RecursiveChunkStrategy      PythonChunkStrategy
          │                           │
          └─────────────┬─────────────┘
                        ▼
                LangChain Splitters
                        │
                        ▼
                     Chunks
```

------------------------------------------------------------------------

### Engineering Lessons

1. **Factory creates objects. Strategy encapsulates algorithms. Flyweight reuses stateless
   objects.** Three patterns, three distinct problems.
2. **Services orchestrate workflows** — and orchestrators should not contain the logic they
   orchestrate.
3. **The pipeline keeps carrying `Document` objects.** A stable type between stages is a
   design decision, not an accident.
4. **Metadata should never be discarded.** `split_text` versus `split_documents` is a
   one-word choice that determines whether citation is possible later.
5. **Choose the strategy at the smallest unit where behaviour varies** — per `Document`, not
   per upload.
6. **Flyweight requires statelessness.** Sharing a mutable object trades allocation cost for
   correctness.
7. **Patterns should be introduced when a requirement makes behaviour vary** — which is why
   Strategy was correctly deferred earlier in this same PR and correctly adopted later.

------------------------------------------------------------------------

### Interview Takeaways

**Why did you introduce the Strategy Pattern?**

> Different document types require different chunking algorithms. Strategy encapsulates each
> algorithm behind a common interface so the Chunk Service stays independent of any
> implementation, and adding an algorithm doesn't edit the service.

**Why use a Factory *with* Strategy?**

> They answer different questions. The Factory selects the appropriate strategy based on
> document metadata; the Strategy performs the chunking. Factory chooses **which object**,
> Strategy defines **what behaviour**.

**Why process one `Document` at a time?**

> Because a single upload can mix PDF, Markdown, and Python files, each needing a different
> algorithm. Selecting the strategy per document is what makes mixed uploads work at all.

**Why `split_documents()` rather than `split_text()`?**

> `split_text` returns plain strings and drops the `Document` wrapper, discarding metadata.
> `split_documents` preserves LangChain `Document` objects with their metadata intact, which
> is what enables traceability, filtering, and downstream retrieval.

**Why implement Flyweight?**

> Chunking strategies are stateless, so a single shared instance is safe and avoids
> unnecessary object creation. In this project the optimisation is primarily educational —
> the more useful lesson is the constraint: the moment a strategy held mutable state, sharing
> it would become a bug.

------------------------------------------------------------------------

### Biggest Takeaway

> **Design patterns should never be introduced because they are famous. They should emerge
> naturally when solving real software engineering problems.**

In this project: Factory solved object creation, Strategy solved algorithm variation, and
Flyweight solved object reuse. Each one arrived *after* the problem it answers.

---

## PR-4 Discussion — Embedding Pipeline & Designing for PR-5

> The objective is **not** simply generating embeddings. It is understanding **how
> responsibilities are distributed across services** in a scalable RAG architecture.

### Where the Pipeline Stands

**After PR-3:**

```text
Upload → Loader Factory → Documents → Chunk Service → Chunks (List<Document>)
```

**After PR-4:**

```text
Upload → Loader Factory → Documents → Chunk Service → Chunks → Embedding Service → Embeddings
```

Notice what is still missing: the Vector Database. **Embeddings exist before they are
stored**, and keeping those two facts separate is the entire subject of this PR.

------------------------------------------------------------------------

### Why an `EmbeddingService` at All?

Should `ingestion.py` simply call the model directly?

```python
embedding_model.embed_documents(...)
```

No. `ingestion.py` is an **orchestration layer**. It coordinates the workflow and must never
know implementation details. Its knowledge is limited to the sequence:

```text
Load  →  Chunk  →  Embed  →  Store  →  Retrieve
```

Putting the model call inside it would mean that changing embedding providers edits the
orchestrator — a component with no stake in that decision.

**`EmbeddingService` owns:**

- selecting the embedding model
- generating embeddings
- batching requests *(future)*
- measuring embedding performance
- hiding LangChain implementation details

**It must not know about:** vector databases, FAISS, retrieval, or the UI.

Its entire job is one transformation:

```text
Text  ──►  Vectors
```

------------------------------------------------------------------------

### Should the Strategy Pattern Be Used Here?

At first glance yes, because embedding models genuinely vary:

| Model | Dimensions |
| --- | --- |
| `BAAI/bge-small-en-v1.5` | 384 |
| OpenAI `text-embedding-3-small` | 1536 |
| Nomic Embed | 768 |

Different models, different dimensions, different retrieval quality.

**But today the application supports exactly one model.** There is no runtime decision, so
Strategy would be abstraction without a problem — the same conclusion reached (and initially
reached) for chunking in PR-3.

> **Engineering Principle**
> Design for extension. Implement for today's requirements.

#### When Strategy Would Become Justified

Suppose premium users get OpenAI embeddings and free users get HuggingFace embeddings. Now
behaviour varies at runtime and Strategy emerges naturally.

The important detail is **what** varies:

| | Variation axis |
| --- | --- |
| Chunking (PR-3) | Document Type |
| Embedding (hypothetical) | User Tier |

This is a key architectural insight: **always identify what actually varies before
introducing Strategy.** Two Strategy implementations in the same codebase can key off
completely different things, and getting the axis wrong produces an abstraction that fits
nothing.

#### Why a Factory Is Also Unnecessary Here

During loading, different document types required different loader **objects**, so the
Factory answered "which object should I create?"

During embedding, every input is already a `Document`. There is no object creation decision
to make, so a Factory would add a layer with nothing to decide.

------------------------------------------------------------------------

### The Service Contract

| | Input | Output |
| --- | --- | --- |
| `ChunkService` | `List[Document]` | `List[Document]` |
| `EmbeddingService` | `List[Document]` | `List[List[float]]` |
| `VectorStore` | `documents`, `embeddings` | *storage* |

Every service owns exactly one transformation, and the responsibility of `EmbeddingService`
ends the moment vectors are produced.

#### Why Not Return Vector Objects?

A richer return type was considered:

```python
EmbeddingResult {
    document,
    chunk,
    metadata,
    embedding
}
```

It is a reasonable-looking design, so the deciding question is: **who actually needs this
structure?**

Only the Vector Database. Which means `EmbeddingService` would be assembling a shape for a
component it is not supposed to know exists — doing work that belongs elsewhere and acquiring
a dependency it was specifically designed to avoid.

------------------------------------------------------------------------

### How Documents and Embeddings Stay Associated

If `EmbeddingService` returns only vectors, how does the application know which embedding
belongs to which `Document`?

**Ordering.**

```text
Documents        Embeddings
─────────        ──────────
Chunk1     ───►  Vector1
Chunk2     ───►  Vector2
Chunk3     ───►  Vector3
```

Both lists preserve the same order, so the *n*th embedding always corresponds to the *n*th
document. The relationship is maintained without an intermediate object.

The mapping then happens where the knowledge is needed — inside `VectorStore`:

```python
store(documents, embeddings)

# internally
for document, embedding in zip(documents, embeddings):
    ...
```

`zip()` iterates two collections simultaneously, pairing each document with its embedding. No
DTO is required, and `EmbeddingService` stays completely independent of storage.

> **Engineering Principle — Information Expert (GRASP)**
> Give a responsibility to the component that already possesses the knowledge required to
> carry it out. The component that owns storage should be the one that combines documents
> with their embeddings.

------------------------------------------------------------------------

### Why `EmbeddingService` Must Not Know FAISS

`EmbeddingService` should know nothing about FAISS, Chroma, Pinecone, or Qdrant. It converts:

```text
Chunk  ──►  Vector
```

Storage concerns belong exclusively to the Vector Database layer. This is the same boundary
identified back in PR-1, when the question "how many files change when FAISS becomes Qdrant?"
had the answer **one**. That answer only stays true if this boundary is never crossed.

#### Does the Vector Database Determine Dimensions?

No. **The embedding model determines dimensionality:**

```text
BAAI    →  384
OpenAI  →  1536
Nomic   →  768
```

The Vector Database merely **validates** that every inserted vector has the expected
dimension. It does not choose it.

> **Rule**
> One Vector Database index should contain vectors generated by a single embedding model — or
> by models with the same output dimensionality and representation.

------------------------------------------------------------------------

### Why Not Embed PDFs Directly?

Embedding models operate on **text**, not on binary document formats. Hence the pipeline:

```text
PDF  →  Loader  →  Text  →  Chunking  →  Embeddings
```

Chunking is not an optional optimisation in that chain. Embedding an entire document would
produce generic embeddings, reduce retrieval precision, increase token usage, waste context
window, and reduce answer quality. Only semantically relevant chunks should ever reach the
LLM.

------------------------------------------------------------------------

### The Pipeline After PR-5

```text
Chunks
   │
   ▼
Embedding Service
   │
   ▼
Embeddings
   │
   ▼
Vector Store
   │
   ▼
Similarity Search
   │
   ▼
Retrieved Chunks
   │
   ▼
LLM
```

`EmbeddingService` finishes before retrieval begins — and it has no idea retrieval exists.

**Full ingestion + query architecture:**

```text
Upload  →  Loader Factory  →  Documents  →  Chunk Service  →  Chunks
                                                                │
                                                                ▼
                                                       Embedding Service
                                                                │
                                                                ▼
                                                           Embeddings
                                                                │
                                                                ▼
                                                          Vector Store
                                                                │
                                                                ▼
                                                            Retriever
                                                                │
                                                                ▼
                                                               LLM
```

------------------------------------------------------------------------

### Rejected Alternatives

| Alternative | Why rejected |
| --- | --- |
| `ingestion.py` calls the embedding model directly | Orchestration would own an implementation detail; changing providers would edit the orchestrator |
| `EmbeddingService` returns an `EmbeddingResult` DTO | Only the Vector Database needs that shape; building it means doing another component's work |
| Strategy Pattern for embedding models | Only one model exists today — abstraction without a runtime decision |
| Factory for embedding models | Every input is already a `Document`; there is no object-creation decision to make |
| `EmbeddingService` writes to the vector store | Generation and storage are independent responsibilities; coupling them blocks swapping the database |

------------------------------------------------------------------------

### Design Principles Applied

| Principle | How it shows up here |
| --- | --- |
| **Single Responsibility** | Each service performs exactly one transformation |
| **Separation of Concerns** | Embedding generation stays independent of storage |
| **Open/Closed** | New embedding models can be introduced without changing orchestration |
| **Information Expert (GRASP)** | The component that owns storage owns the document↔embedding mapping |

------------------------------------------------------------------------

### Future Improvement

When multiple embedding providers genuinely exist, the abstraction earns its place:

```text
Embedding Service
        │
        ▼
Embedding Strategy
        │
   ┌────┴────────────────┬──────────────┐
   ▼                     ▼              ▼
OpenAI Strategy   HuggingFace     Nomic Strategy
```

Only then does Strategy become justified.

------------------------------------------------------------------------

### Interview Takeaways

**Why introduce an `EmbeddingService`?**

> To isolate embedding logic from orchestration. It keeps the application extensible and
> hides LangChain implementation details behind one transformation — text to vectors.

**Why doesn't `ingestion.py` call LangChain directly?**

> Because ingestion is responsible only for coordinating pipeline stages, not implementing
> them. If it called the model directly, swapping embedding providers would become an
> orchestration change.

**Why not use Strategy immediately?**

> Only one embedding model currently exists, so there is no runtime decision to encapsulate.
> Strategy should be introduced when multiple interchangeable algorithms genuinely exist —
> and the trigger here would be user tier, not document type.

**Why not return vector objects?**

> `EmbeddingService` should only transform text into vectors. A combined structure of
> document, chunk, metadata, and embedding is needed by exactly one component — the Vector
> Database — so building it in the embedding layer would mean doing another layer's work.

**Why preserve ordering instead of returning a mapping?**

> The *n*th embedding always corresponds to the *n*th document, so the Vector Database can
> combine them with `zip(documents, embeddings)`. The relationship is maintained without
> introducing a DTO that couples embedding to storage.

**Why shouldn't `EmbeddingService` know FAISS?**

> Embedding generation and storage are independent responsibilities. Keeping them separate is
> what makes it possible to swap vector databases without touching embedding logic — the
> answer to PR-1's original "how many files change?" question.

**Does the vector database choose the embedding dimension?**

> No. The embedding model determines dimensionality — 384 for BAAI, 1536 for OpenAI, 768 for
> Nomic. The database only validates that inserted vectors match the expected dimension, which
> is why one index should hold vectors from a single model.

------------------------------------------------------------------------

### Biggest Takeaway

> **Software architecture is not about creating more classes. It is about giving every
> component exactly one responsibility.**

The cleanest architecture emerged from repeatedly asking:

> **"Who actually owns this responsibility?"**

instead of:

> **"Where can I put this code?"**

---

## Self-Check

Answer these without looking. If any is shaky, the corresponding section above is the fix.

1. If FAISS is replaced by Qdrant, which files change — and why is `embeddings.py` not one of
   them?
2. Why should the parent `Loader` expose only `load()`?
3. Why should a Factory return `Loader` rather than `PdfLoader`, given both branches of the
   `isinstance` check call the same method?
4. What is the measurable test of an extensible architecture when `ExcelLoader` is added?
5. Why are pages a bad chunk boundary?
6. What does overlap actually prevent, and give the example.
7. What changes about a `Document` during chunking, and what does not?
8. Why was Strategy *deferred* for chunking and then *adopted* in the same PR?
9. What does `split_text` silently throw away that `split_documents` keeps?
10. Under what condition does Flyweight become a bug rather than an optimisation?
11. Why does `EmbeddingService` return `List[List[float]]` rather than an `EmbeddingResult`?
12. Who owns the mapping between documents and embeddings, and what principle decides that?
13. Which component chooses vector dimensionality — the model or the database?

---

### What Week 1 Actually Built

```text
Upload
   │
   ▼ LoaderFactory     ← Factory Pattern, polymorphism      (PR-1, PR-2)
   │
   ▼ ChunkService      ← Strategy + Flyweight               (PR-3)
   │
   ▼ EmbeddingService  ← one transformation, no storage     (PR-4)
   │
   ▼ (Vector Store)                                          → PR-5
```

Four PRs, and the recurring result is the same in each: `app.py` never changed, and every new
capability was added by writing a new class rather than editing an old one.

The patterns — Factory, Strategy, Flyweight, Information Expert — were never the goal. Each
one was the shape left behind after asking who owns a responsibility and how much has to
change when requirements do.

---

**Next:** PR-5 — the Vector Store: persistence, similarity search, and the layer every other
component in Week 1 was deliberately built not to know about.
