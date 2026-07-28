# Week 3 — Part 2
# LangChain Expression Language (LCEL)

> **Goal of this Chapter**
>
> In the previous chapter, we studied the engineering principles behind declarative systems:
>
> - Declarative Programming
> - Composition
> - Pipeline Pattern
> - Functional Programming
>
> In this chapter, we study how **LangChain applies those principles** through LCEL (LangChain Expression Language).
>
> This chapter is intentionally **framework-specific**, while still focusing on **engineering reasoning** rather than syntax.

---

# Learning Outcomes

By the end of this chapter, I should confidently answer:

- What is LCEL?
- Why was LCEL introduced?
- What is a Runnable?
- Why not simply use Python functions?
- Why is Runnable an interface?
- What responsibilities belong to Runnable?
- What is RunnableLambda?
- What is RunnablePassthrough?
- What is RunnableParallel?
- Why does the Pipe Operator improve maintainability?
- Why is Output Parsing separated from the LLM?
- Why are Prompts also Runnables?

---

# 1. What is LCEL? ⭐⭐⭐⭐⭐

## Definition

LCEL (**LangChain Expression Language**) is LangChain's declarative language for composing AI applications.

Instead of manually orchestrating execution using imperative code, LCEL allows developers to build AI systems by composing reusable components called **Runnables**.

Think of LCEL as:

- SQL for Databases
- Java Streams for Collections
- Unix Pipes for Shell Commands

but applied to AI workflows.

---

# Why was LCEL introduced?

Early versions of LangChain relied heavily on helper classes such as:

- LLMChain
- SequentialChain
- RetrievalQA
- StuffDocumentsChain

These abstractions worked well for simple applications.

As AI applications became larger, developers needed:

- Streaming
- Async execution
- Parallel execution
- Better observability
- Reusable components
- Custom orchestration

Creating another helper class for every workflow was not scalable.

Instead,

LangChain introduced one standard abstraction:

```
Runnable
```

Everything became composable.

---

# Evolution

```
Imperative Code

↓

Helper Chains

↓

LCEL

↓

LangGraph
```

Each stage solved the limitations of the previous one.

---

# Interview Insight ⭐

LCEL was introduced because **composition scales better than specialization**.

Instead of creating more helper classes,

LangChain standardized execution around one abstraction.

---

# 2. Runnable ⭐⭐⭐⭐⭐

---

## Definition

Runnable is the fundamental building block of LCEL.

Anything capable of:

- receiving an input
- performing some work
- producing an output

can become a Runnable.

Everything in LCEL is built around this common abstraction.

---

# Mental Model

Imagine a factory conveyor belt.

```
Input

↓

Runnable

↓

Output
```

Every machine follows exactly the same contract.

Because of this,

machines can be connected together indefinitely.

---

# Why not just use normal Python functions?

A normal Python function certainly performs work.

However,

every function exposes different APIs.

Example

```
clean()

↓

parser.parse()

↓

retriever.search()

↓

llm.generate()
```

Nothing is standardized.

Composition becomes difficult.

Runnable introduces one common execution contract.

Now every component behaves identically.

---

# Why an Interface?

LangChain wanted every component to expose the same behaviour.

Whether something is

- Prompt
- Retriever
- LLM
- Parser

it should execute in a predictable way.

This enables

- Composition
- Streaming
- Async Execution
- Parallel Execution
- Tracing
- Retry Logic

without special-case code.

---

# Runnable Lifecycle

Every Runnable follows the same lifecycle.

```
Input

↓

invoke()

↓

Output
```

Other execution styles include

```
Input

↓

batch()

↓

Multiple Outputs
```

and

```
Input

↓

stream()

↓

Partial Outputs
```

The important idea is not the methods.

The important idea is that **every Runnable exposes a consistent execution model.**

---

# Common Runnable Methods

You do **not** need to memorize these.

Understand their responsibilities.

| Method | Responsibility |
|----------|----------------|
| invoke() | Execute once |
| batch() | Execute multiple inputs |
| stream() | Stream output progressively |
| ainvoke() | Async execution |
| astream() | Async streaming |

---

# Runnable Responsibility

Runnable should own **one responsibility**.

Examples

```
Prompt Formatting

↓

Retriever

↓

LLM

↓

Parser
```

Avoid creating one Runnable that performs everything.

This follows:

- Single Responsibility Principle
- Separation of Concerns

---

# Interview Questions

- What is Runnable?
- Why was Runnable introduced?
- Why not use Python functions?
- Why is Runnable considered an interface?
- Explain the Runnable lifecycle.
- What engineering principles does Runnable support?

---

# 3. RunnableLambda ⭐⭐⭐⭐☆

---

# Engineering Problem

Suppose your application already contains business logic.

Example

```python
def clean_question(question):
    ...
```

Should you rewrite this into a custom LangChain component?

No.

That would create unnecessary work.

---

# RunnableLambda

RunnableLambda adapts an existing Python function into the LCEL ecosystem.

```
Python Function

↓

RunnableLambda

↓

LCEL Pipeline
```

Instead of rewriting your logic,

you simply wrap it.

---

# Why wrap a Python function?

Because LCEL expects every component to behave like a Runnable.

RunnableLambda allows existing business logic to participate in the pipeline without modification.

---

# Trade-offs

### Good Use Cases

- Formatting
- Validation
- Small Transformations
- Pre-processing
- Post-processing

### Poor Use Cases

Avoid placing large business workflows inside RunnableLambda.

Business logic should remain inside

- Services
- Domain Layer
- Orchestrators

RunnableLambda should connect business logic,

not replace it.

---

# Engineering Insight ⭐

RunnableLambda closely resembles the **Adapter Pattern**.

It adapts an existing function to a new interface.

---

# Interview Questions

- What is RunnableLambda?
- Why wrap existing functions?
- When should RunnableLambda NOT be used?
- Which design pattern resembles RunnableLambda?

---

# 4. RunnablePassthrough ⭐⭐⭐⭐☆

---

# Engineering Problem

Sometimes multiple downstream components require access to the original input.

Example

```
Question

↓

Retriever

↓

Prompt
```

Both need

the original question.

Without preserving it,

developers would need to manually duplicate data.

---

# RunnablePassthrough

RunnablePassthrough forwards the original input unchanged.

```
Question

────────────► Prompt

│

▼

Retriever
```

The same input is now available to multiple branches.

---

# Why preserve original input?

Without RunnablePassthrough,

developers often end up

- copying variables
- recomputing values
- tightly coupling components

RunnablePassthrough removes this duplication.

---

# Engineering Insight ⭐

RunnablePassthrough follows the Pipeline Pattern.

It performs no transformation.

Its only responsibility is forwarding data.

---

# Interview Questions

- What problem does RunnablePassthrough solve?
- Why not duplicate variables manually?
- Why is RunnablePassthrough considered a pipeline component?

---

# 5. RunnableParallel ⭐⭐⭐⭐⭐

---

# Engineering Problem

Some operations are completely independent.

Example

```
Retrieve Documents

Retrieve Conversation History
```

Neither depends on the other.

Executing them sequentially wastes time.

---

# RunnableParallel

RunnableParallel declares that multiple operations may execute simultaneously.

```
Question

↓

──────────────

↓

Retriever

↓

History

↓

Metadata

↓

──────────────

↓

Merge Results
```

Notice

we never manually create threads.

We simply declare

independent work.

The framework decides execution.

---

# What problems become parallelizable?

Examples

- Retrieve documents
- Retrieve conversation history
- Fetch user profile
- Load metadata

These operations are independent.

Therefore,

they can execute together.

---

# Can Retrieval and Conversation History be fetched together?

Yes.

Both require the original question,

but neither depends on the result of the other.

RunnableParallel is ideal here.

---

# Engineering Insight ⭐

RunnableParallel is not about multithreading.

It is about expressing **independence**.

The runtime decides how to execute.

---

# Interview Questions

- What is RunnableParallel?
- When should RunnableParallel be used?
- Can dependent tasks execute in RunnableParallel?
- Why is RunnableParallel declarative?

---

# 6. Pipe Operator ( | ) ⭐⭐⭐⭐⭐

---

# What is the Pipe Operator?

The Pipe Operator composes multiple Runnables into a single pipeline.

Example

```
Prompt

|

LLM

|

Parser
```

Each stage receives the output of the previous stage.

---

# Why is this better than nested function calls?

Without composition

```
parser(

    llm(

        prompt(...)

    )

)
```

Nested code becomes difficult to read.

With LCEL

```
Prompt

↓

LLM

↓

Parser
```

The pipeline becomes immediately visible.

---

# Engineering Insight ⭐

The Pipe Operator is simply another implementation of the Pipeline Pattern.

It improves

- readability
- maintainability
- composition

---

# Interview Questions

- What does the Pipe Operator do?
- Why is it easier to maintain?
- Which architectural pattern does it resemble?

---

# 7. Output Parser ⭐⭐⭐⭐☆

---

# Engineering Problem

LLMs generate text.

Applications often require structured data.

Example

Instead of

```
"The customer's priority is High."
```

the application might need

```json
{
  "priority": "High"
}
```

Should the LLM be responsible for parsing its own output?

No.

---

# Why parsing belongs in a separate component

The LLM has one responsibility:

```
Generate text.
```

The parser has another responsibility:

```
Convert generated text into structured data.
```

Keeping them separate follows:

- Single Responsibility Principle
- Separation of Concerns

---

# Benefits

Separating parsing provides:

- Cleaner architecture
- Reusable parsers
- Easier testing
- Easier validation
- Structured outputs

---

# Engineering Insight ⭐

The Output Parser behaves like a translator between the LLM and the rest of the application.

It converts unstructured language into application-friendly data.

---

# Interview Questions

- Why shouldn't the LLM parse its own output?
- What responsibility belongs to the Output Parser?
- What software engineering principle does this follow?

---

# 8. Prompt Composition ⭐⭐⭐⭐☆

---

# Engineering Problem

Prompts are not just strings.

They are reusable components that accept variables and produce formatted instructions.

Therefore,

they should participate in the pipeline just like any other component.

---

# Prompts as Runnables

Prompt Templates receive

```
Variables

↓

Formatted Prompt
```

This satisfies the Runnable contract.

Therefore,

prompts themselves become Runnables.

---

# Why is this powerful?

Because prompts now support:

- Composition
- Reuse
- Streaming
- Tracing
- Testing

just like every other Runnable.

---

# Prompt Composition

```
Question

↓

Prompt Template

↓

Formatted Prompt

↓

LLM
```

Notice

the prompt is no longer "just a string."

It is an executable component.

---

# Interview Questions

- Why are Prompt Templates considered Runnables?
- Why is Prompt Composition useful?
- How does Prompt Composition improve maintainability?

---

# LCEL Design Principles ⭐⭐⭐⭐⭐

LCEL promotes several engineering principles:

- Declarative Programming
- Composition
- Pipeline Pattern
- Separation of Concerns
- Single Responsibility Principle
- Open / Closed Principle
- Reusability
- Standardized Interfaces

---

# LCEL vs Traditional Chains

| Traditional Chains | LCEL |
|--------------------|------|
| Specialized helper classes | Generic composition |
| Difficult to extend | Easy to extend |
| Less reusable | Highly reusable |
| Harder streaming | Native streaming |
| Harder async | Native async |
| Harder parallel execution | RunnableParallel |

---

# What You Should Remember Forever ⭐

LCEL is **not** about the Pipe Operator.

LCEL is **not** about Runnables.

LCEL is about solving a software engineering problem:

> **How do we build large, maintainable, composable AI systems without creating hundreds of specialized helper classes?**

Runnable became the standard execution contract.

LCEL became the language for composing those Runnables.

Everything else is simply a consequence of those two ideas.

---

# Stage Checkpoint ✅

Before moving to Prompt Engineering, ensure you can confidently answer:

- Why was LCEL introduced?
- What engineering problem does Runnable solve?
- Why not use normal Python functions?
- Why is Runnable an interface?
- Why does RunnableLambda resemble the Adapter Pattern?
- Why preserve the original input with RunnablePassthrough?
- What work is suitable for RunnableParallel?
- Why is the Pipe Operator more maintainable than nested calls?
- Why does Output Parsing belong outside the LLM?
- Why are Prompt Templates considered Runnables?

If you can answer these questions without referring to your notes, you understand **the engineering philosophy behind LCEL**, not just its syntax.