# LCEL: LangChain Expression Language

------------------------------------------------------------------------

## Crisp Definition

**LCEL (LangChain Expression Language)** is LangChain's declarative syntax for composing AI components — prompts, models, retrievers, parsers — into a single pipeline using the `|` operator.

Every component that participates in this pipeline implements one common interface: **Runnable**.

Think of LCEL as:

- SQL for databases
- Java Streams for collections
- Unix pipes for shell commands

...applied to AI workflows.

------------------------------------------------------------------------

## Why Was LCEL Introduced?

Early LangChain relied on specialized helper classes:

- `LLMChain`
- `SequentialChain`
- `RetrievalQA`
- `StuffDocumentsChain`

Fine for simple apps. But as systems grew, developers needed streaming, async execution, parallel execution, tracing, and reusable components — and a new helper class per workflow doesn't scale.

```text
Imperative Code → Helper Chains → LCEL → LangGraph
```

Each stage fixed the previous stage's rigidity. LangGraph later added cycles/state for agentic control flow — LCEL itself is for **acyclic, composable pipelines**.

> **Interview Insight** — Don't answer "LCEL uses Runnable." Answer: *"Helper chains became rigid as pipelines grew. LCEL replaced them with one standard composable interface, trading some directness of control for reusability, streaming, and observability."*

------------------------------------------------------------------------

## Runnable

### Crisp Definition

**Runnable** is the standard execution contract in LangChain. Anything that takes an input, does work, and produces an output can be a Runnable — a prompt, a model, a retriever, a parser, or your own function.

```text
Input → Runnable → Output
```

Because every component honors the same contract, components can be connected in any combination.

### Why Not Just a Python `Callable`?

A plain Python object with `__call__` also "takes input, returns output" — so why invent Runnable?

Because `__call__` only standardizes *one* thing: synchronous single-shot invocation. It says nothing about:

| Requirement | `__call__` alone | Runnable |
|---|---|---|
| Batch execution | Not defined | `batch()` |
| Streaming partial output | Not defined | `stream()` |
| Async execution | Not defined | `ainvoke()`, `astream()` |
| Composition via `\|` | Not defined | `__or__` implemented |
| Tracing / callbacks / config propagation | Not defined | `RunnableConfig` threaded through every call |
| Retries, fallbacks | Not defined | `.with_retry()`, `.with_fallbacks()` |

If LangChain had used bare callables, every one of these would need to be bolted on separately for every component. Runnable bundles them into one interface so that a prompt, an LLM, and a parser all expose identical capabilities.

### Why an Interface?

LangChain wants a `Prompt`, a `Retriever`, an `LLM`, and a `Parser` to all behave predictably — same method names, same execution styles — regardless of what they do internally. An interface enforces that without special-case code per component.

### Runnable Lifecycle

```text
Input → invoke() → Output
Input → batch()  → [Output, Output, ...]
Input → stream() → Output chunk, Output chunk, ...
```

The methods aren't the point — **the point is that every Runnable exposes the same execution model.**

### Common Methods

Don't memorize these. Understand the responsibility each one solves.

| Method | Responsibility |
|---|---|
| `invoke()` | Run once, synchronously |
| `batch()` | Run many inputs, possibly in parallel |
| `stream()` | Yield output incrementally |
| `ainvoke()` | Async version of `invoke()` |
| `astream()` | Async version of `stream()` |

### Runnable Responsibility (Single Responsibility Principle)

A Runnable should do **one job**. A pipeline of small Runnables (prompt formatting → retrieval → generation → parsing) is preferable to one giant Runnable doing everything — it stays testable, replaceable, and composable.

------------------------------------------------------------------------

## RunnableLambda

### Engineering Problem

Your codebase already has business logic:

```python
def clean_question(question: str) -> str:
    ...
```

Do you rewrite it as a custom LangChain component? No — that's wasted, and duplicated, effort.

### Definition

`RunnableLambda` adapts an existing Python function into the Runnable contract, without touching the function itself.

```text
Python Function → RunnableLambda → LCEL Pipeline
```

### Why Wrap a Python Function?

Because LCEL pipelines only compose Runnables. `RunnableLambda` is the bridge that lets existing, untouched business logic participate in a `|` chain.

### When Should Business Logic *Stay Outside* RunnableLambda?

| Good fit inside `RunnableLambda` | Keep outside `RunnableLambda` |
|---|---|
| Formatting | Large business workflows |
| Validation | Domain logic / rules engines |
| Small transformations | Anything needing its own tests independent of LangChain |
| Pre/post-processing | Orchestration logic that shouldn't be coupled to LCEL |

`RunnableLambda` should **connect** business logic, not **own** it. If the lambda body grows past a few lines of glue code, that's a signal the logic belongs in a service/domain layer, called *from* the lambda.

### Code Example:

```python
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# 1. Define custom Python functions (Pure, single-purpose functions)
def count_words(text: str) -> int:
    """Calculates word count of input string."""
    return len(text.split())

def add_metadata(word_count: int) -> dict:
    """Formats the word count into a structured summary dict."""
    status = "Verbose" if word_count > 50 else "Concise"
    return {"length": word_count, "category": status}


# 2. Wrap them into Runnables
# Option A: Explicit wrapping
word_counter = RunnableLambda(count_words)

# Option B: Implicit wrapping (LCEL automatically wraps functions passed via `|`)
# `RunnableLambda(add_metadata)` happens under the hood!


# 3. Build a pipeline with LCEL
prompt = PromptTemplate.from_template("Summarize this topic in 2 sentences: {topic}")
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

# Chain: Generate summary -> Count words -> Add metadata classification
chain = (
    prompt 
    | model 
    | parser 
    | word_counter          # Custom function 1
    | add_metadata          # Custom function 2 (implicitly wrapped)
)

# 4. Execute using standard Runnable methods
result = chain.invoke({"topic": "Quantum Computing"})
print(result)
# Output: {'length': 28, 'category': 'Concise'}
```

### Execution Order: How LCEL Decides What Runs When

Execution order is determined strictly by **data dependencies** — which component needs another's output — not by how the code happens to be written. When you chain Runnables with `|`, LCEL builds a **Directed Acyclic Graph (DAG)** under the hood, not just a flat sequence of calls.

#### Sequential Execution

For the chain above, every stage's input *is* the previous stage's output, so execution is strictly left-to-right:

```text
[Input Dict]
     │
     ▼
prompt        → fills the template   → PromptValue
     │
     ▼
model         → calls the LLM        → AIMessage
     │
     ▼
parser        → extracts the string  → str
     │
     ▼
word_counter  → counts words         → int
     │
     ▼
add_metadata  → classifies the count → dict
     │
     ▼
[Final Output]
```

Internally this is a `RunnableSequence`: Component B cannot start until Component A returns, because A's return value is B's only input.

#### Parallel Execution (Independent Branches)

Sequential order is just the default for `|`. When a pipeline branches — via a dict or `RunnableParallel` — LCEL runs every branch that depends on the *same* upstream output **concurrently**, then waits for all of them before continuing:

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

branches = RunnableParallel(
    word_count=word_counter,
    original_text=RunnablePassthrough(),
)

chain = prompt | model | parser | branches
```

```text
              parser output (str)
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
       word_counter         Passthrough
            │                   │
            ▼                   ▼
        int (count)         str (original)
            └─────────┬─────────┘
                       ▼
        {"word_count": ..., "original_text": ...}
```

`word_counter` and `Passthrough` both depend only on `parser`'s output, not on each other's — so LCEL has no reason to serialize them. It runs both, waits for both to resolve, and merges the results into a single dict before the next sequential step.

#### The Two Rules, Generalized

- **Sequence Rule** — Runnables joined by `|` (a `RunnableSequence`) always run left-to-right; each one waits for the previous one's output.
- **Graph Rule** — Runnables joined inside a dict / `RunnableParallel` run concurrently whenever neither depends on the other's output, and the pipeline waits for all of them before proceeding.

This is exactly why LCEL is *declarative*: you never write "run these two in parallel, then join." You describe the shape of the dependencies, and LCEL's DAG scheduling decides how to execute it.

### Engineering Insight

`RunnableLambda` is the **Adapter Pattern** — it adapts an existing interface (a plain function) to a new one (Runnable), without modifying the original.

------------------------------------------------------------------------

## RunnablePassthrough

### Engineering Problem

Multiple downstream steps sometimes need the *original* input, not a transformed version of it:

```text
Question → Retriever → Prompt
```

Both the retriever and the final prompt need the raw question. Without a mechanism to preserve it, you end up manually threading the same variable through every step, which quickly becomes brittle wiring.

### Definition

`RunnablePassthrough` forwards its input unchanged so it stays available to any branch that needs it:

```text
Question ─────────────► Prompt
    │
    └──────────► Retriever
```

### Why Preserve the Original Input? What Breaks Without It?

Without it, developers end up:

- copying the same variable into multiple places manually
- recomputing values that were already available upstream
- tightly coupling steps together, since each step must know what the next one needs

`RunnablePassthrough` removes this duplication by design — it performs **no transformation**; its only job is forwarding data. This matters most inside `RunnableParallel`, where one branch retrieves documents and another needs the untouched question for the final prompt.

### Engineering Insight

Pure Pipeline Pattern — a stage that passes data through unmodified so parallel branches don't have to reconstruct it.

------------------------------------------------------------------------

## RunnableParallel

### Engineering Problem

Some operations don't depend on each other at all:

```text
Retrieve Documents
Retrieve Conversation History
```

Running them one after another wastes latency for no reason.

### Definition

`RunnableParallel` declares that a set of Runnables can execute simultaneously, each receiving the same input:

```text
                Question
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
    Retriever    History    Metadata
        │          │          │
        └──────────┼──────────┘
                   ▼
             Merge Results
```

Notice: you never create threads yourself. You **declare independence**; the runtime decides how to execute it (LangChain uses a thread pool for sync code, `asyncio.gather` under async).

### What Problems Become Parallelizable?

Any set of operations that share an input but don't depend on each other's output:

- Retrieve documents
- Retrieve conversation history
- Fetch user profile
- Load metadata / permissions

### Can Retrieval and Conversation History Be Fetched Together?

**Yes.** Both need the original question as input, but neither needs the other's output — that's exactly the independence `RunnableParallel` is for. Combine it with `RunnablePassthrough` when the final prompt also needs the raw question alongside both results.

### Engineering Insight

`RunnableParallel` is not "manual multithreading" — it's a **declaration of independence** between steps. The runtime owns the execution strategy.

------------------------------------------------------------------------

## Pipe Operator (`|`)

### What It Does

The `|` operator composes Runnables into a pipeline, where each stage's output becomes the next stage's input:

```text
Prompt | LLM | Parser
```

### Why Is This More Maintainable Than Nested Calls?

Without composition:

```python
parser(llm(prompt(...)))
```

Nested calls read inside-out, get harder to modify as depth grows, and hide the actual data flow. With LCEL:

```text
Prompt → LLM → Parser
```

The pipeline reads top-to-bottom in execution order — adding, removing, or reordering a stage is a one-line change instead of a nesting-depth change.

### Engineering Insight

The pipe operator is just another implementation of the **Pipeline Pattern**, same idea as Unix pipes (`cat | grep | sort`) or Java Streams (`.filter().map().collect()`).

------------------------------------------------------------------------

## Output Parser

### Engineering Problem

LLMs generate text. Applications need structured data:

```text
"The customer's priority is High."   →   {"priority": "High"}
```

Should the LLM parse its own output? No.

### Why Parsing Belongs Outside the LLM

Two different responsibilities:

```text
LLM     → generate text
Parser  → convert text into structured data
```

Keeping them separate follows **Single Responsibility Principle** and **Separation of Concerns**. It also means the parser can be swapped, tested, and validated independently of the model — and reused across different prompts/models that produce the same output shape.

### Benefits

- Reusable parsers across chains
- Independently testable
- Structured, validated outputs (e.g. via Pydantic)
- Cleaner failure modes (a parsing error is distinguishable from a generation error)

### Engineering Insight

The Output Parser is a translator between the LLM's unstructured language and the rest of the application's structured data needs.

------------------------------------------------------------------------

## Prompt Composition

### Engineering Problem

A prompt isn't just a string — it's a template that accepts variables and produces formatted instructions. If it can't participate in the pipeline like everything else, it becomes a special case.

### Prompts as Runnables

A Prompt Template satisfies the Runnable contract:

```text
Variables → Prompt Template → Formatted Prompt
```

So it *is* a Runnable — which means it supports composition, streaming, tracing, and testing exactly like the LLM or parser next to it in the chain.

```text
Question → Prompt Template → Formatted Prompt → LLM
```

### Why This Matters

A prompt is no longer "just a string interpolation step" — it's an executable, composable component, tested and versioned the same way as any other stage in the pipeline.

------------------------------------------------------------------------

## LCEL vs Traditional Chains

| Traditional Chains | LCEL |
|---|---|
| Specialized helper classes | Generic composition |
| Hard to extend | Easy to extend |
| Less reusable | Highly reusable |
| Manual streaming | Native streaming |
| Manual async | Native async |
| Manual parallel execution | `RunnableParallel` |

------------------------------------------------------------------------

## Interview Q&A

### What is LCEL?

LangChain's declarative language for composing Runnables into pipelines using the `|` operator — the AI-workflow equivalent of Unix pipes or SQL.

### What is a Runnable?

The standard execution contract in LangChain: anything with `invoke`/`batch`/`stream` (and async equivalents) that takes an input and produces an output.

### Why not just use a Python `Callable`?

`__call__` only standardizes single synchronous invocation. It says nothing about batching, streaming, async, retries, tracing, or `|`-composition — all of which Runnable defines as part of one shared contract.

### Why is Runnable an interface rather than a base class with default behavior only?

So heterogeneous components — prompts, retrievers, LLMs, parsers — can all be composed and executed identically, without the framework special-casing each type.

### What design pattern does RunnableLambda resemble?

The Adapter Pattern — it adapts an existing function to the Runnable interface without modifying it.

### When should you avoid putting logic inside RunnableLambda?

When the logic is a full business workflow rather than glue code — that belongs in a service/domain layer, invoked *from* the lambda, not written inside it.

### What problem does RunnablePassthrough solve?

It forwards the original input unchanged so multiple downstream branches (e.g. a retriever and the final prompt) can use it without manual duplication.

### Is RunnableParallel about multithreading?

No — it's a declaration that operations are independent. The runtime, not the developer, decides how to execute them concurrently.

### Can Retrieval and Conversation History be fetched in RunnableParallel?

Yes — both depend only on the original question, not on each other's output.

### Why is the pipe operator more maintainable than nested function calls?

It makes data flow read top-to-bottom in execution order instead of inside-out, so adding/removing/reordering a stage is a local edit, not a restructuring of nested calls.

### Why shouldn't the LLM parse its own output?

Generation and parsing are different responsibilities. Separating them (Single Responsibility Principle) makes the parser reusable, independently testable, and its failures distinguishable from generation failures.

### Why are Prompt Templates considered Runnables?

Because they take variables and produce a formatted output — satisfying the same contract as any other pipeline stage, which lets them be composed, streamed, and traced identically.

------------------------------------------------------------------------

## Common Interview Traps

❌ LCEL is just syntax sugar for the `|` operator.

✔ The operator is incidental. LCEL's actual contribution is the Runnable contract — the standard execution interface underneath.

------------------------------------------------------------------------

❌ RunnableParallel means "runs on multiple threads."

✔ It declares independence between steps. Whether that becomes threads, async tasks, or something else is the runtime's decision.

------------------------------------------------------------------------

❌ RunnableLambda is where business logic should live.

✔ It should call business logic, not contain it — large logic inside a lambda couples your domain code to LangChain.

------------------------------------------------------------------------

❌ RunnablePassthrough transforms data.

✔ It deliberately performs zero transformation — its only job is preserving the original input for later stages.

------------------------------------------------------------------------

❌ The LLM should return structured JSON directly, so no parser is needed.

✔ Even when a model can emit JSON, keeping a separate parser/validator step is what makes failures diagnosable and the pipeline testable independent of the model.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
LCEL is not about the pipe operator.
LCEL is not about Runnables themselves.

LCEL exists to answer one engineering question:

"How do we build large, composable AI systems
without a specialized helper class for every workflow?"
```

Runnable is the standard contract. LCEL is the language for composing Runnables. Everything else — `RunnableLambda`, `RunnablePassthrough`, `RunnableParallel`, the pipe operator, output parsers, prompt composition — is a consequence of those two ideas.