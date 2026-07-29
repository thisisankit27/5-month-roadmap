# Streaming

> **Goal of this Chapter**
>
> This is not "add a typewriter animation to the chat UI."
>
> This is **engineering** — understanding *why* LLM inference is inherently incremental (token-by-token), and why exposing that incremental structure to the client is a transport-level architectural decision, not a cosmetic one. Surprisingly important, because it's the difference between a chat product that feels instant and one that feels broken.

------------------------------------------------------------------------

## Crisp Definition

**Streaming** is sending model output incrementally — token-by-token or event-by-event — to the client as it is generated, instead of buffering the entire response server-side and sending it in one shot once generation completes.

------------------------------------------------------------------------

## Why Streaming?

### Engineering Problem

LLMs generate output **autoregressively** — one token at a time, each new token conditioned on every token generated before it. A 500-token response might take several seconds to fully generate, token by token, with no way to skip ahead. If the server waits for generation to finish before sending *anything*, the client is blocked on the full duration of that loop, no matter how fast any individual token was produced.

### Why Not Just Wait?

Waiting is the naive default: call the LLM, block until the complete string comes back, send it once. It works, and it's simpler to implement. But it means the user stares at a blank screen (or a spinner) for the entire generation window, with zero signal that anything is happening or whether the answer is even going the right direction.

### Think ChatGPT

The product experience that made streaming a default expectation: text appears progressively, word by word, starting almost immediately after you hit send. That's not a UI flourish layered on top — it's the direct, visible consequence of the server forwarding each token to the browser as soon as the model produces it, rather than assembling the full response first.

------------------------------------------------------------------------

## Types of Streaming

*(High-level distinction only — no deep dive into each.)*

### Token Streaming

The raw model output, forwarded one token (or small chunk) at a time, as the decoding loop produces it. This is the lowest-level form of streaming — what you get from `model.stream(...)` in LCEL.

### Event Streaming

Structured **lifecycle events** of the whole pipeline — not just output tokens. Things like "chain started," "tool called," "retriever finished," "LLM produced a new token," "chain ended." Token generation is just *one* event type among many. This is what `chain.astream_events(...)` gives you in LangChain — useful for surfacing intermediate steps in multi-step/agentic chains (e.g. showing "Searching documents…" → "Calling calculator tool…" → the final answer tokens).

| | Token Streaming | Event Streaming |
|---|---|---|
| Granularity | Raw output pieces only | Structured events across the whole chain |
| What it exposes | "Here's the next bit of text" | "Here's *what stage* of the pipeline just did something" |
| Typical API | `chain.stream(...)` | `chain.astream_events(...)` |
| Best fit | Simple prompt → model → parser chains | Multi-step/agentic chains where the user benefits from seeing intermediate progress |

------------------------------------------------------------------------

## Streaming Architecture

### Without Streaming

```text
LLM
 │
 ▼
Entire Response
 │
 ▼
Browser
```

The server holds the connection open, accumulates the *entire* generated output internally, and only then sends one complete payload. From the client's point of view: silence, then everything at once.

### With Streaming

```text
LLM
 │
 ▼
Token
 │
 ▼
Token
 │
 ▼
Token
 │
 ▼
Browser
```

Each token is forwarded to the client as soon as it's produced. The connection stays open across the whole generation, and the client renders incrementally as chunks arrive — instead of one request/response round trip, it's a long-lived connection carrying a sequence of chunks (typically Server-Sent Events, chunked HTTP transfer encoding, or a WebSocket).

### In Code (LCEL)

```python
chain = prompt | model | StrOutputParser()

for chunk in chain.stream({"question": "Explain streaming in one sentence."}):
    print(chunk, end="", flush=True)
```

### Forwarding It Over HTTP (FastAPI + SSE)

```python
from fastapi.responses import StreamingResponse

@app.post("/chat")
async def chat(request: ChatRequest):
    async def event_generator():
        async for chunk in chain.astream({"question": request.question}):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

`chain.stream()` / `chain.astream()` are themselves possible because every LCEL component implements the shared `Runnable` interface — streaming is a built-in capability of the pipeline, not something bolted on afterward.

### Engineering Insight

This is a **pull-vs-push** shift at the transport level. Non-streaming is one blocking request/response — the client is a passive receiver waiting for a single value. Streaming turns the LLM call into a producer emitting values over time, with the client consuming them incrementally as they arrive — the same shape as an iterator/generator, or a reactive stream, applied to a network response instead of an in-memory collection.

------------------------------------------------------------------------

## Benefits

### UX / Perceived Latency

Streaming does **not** make the model generate tokens faster — total generation time is roughly the same, sometimes marginally higher (per-chunk transport overhead). What changes is **time-to-first-token**: the client sees *something* almost immediately instead of waiting for time-to-last-token. The user's felt experience is dominated by "when did anything start happening," not "when did everything finish."

| | Without Streaming | With Streaming |
|---|---|---|
| Time to first visible output | = full generation time | ≈ time to produce the first token |
| User signal during generation | None (blank/spinner) | Continuous — text is visibly arriving |
| Total generation time | Same | Same (or marginally higher) |

### Early Cancellation

**Engineering Problem:** without streaming, once a request is sent, the client has no partial signal at all — it can't tell the response is going to be wrong, too long, or off-topic until the *entire* thing has already been generated and paid for. There's nothing to act on until it's too late to save anything.

**With streaming**, the client sees tokens early enough to judge the response as it forms — and can abort the connection (cancel the fetch / close the SSE stream) mid-generation. That cancellation only actually saves compute if the **server propagates it down to the LLM call** (e.g. cancelling the underlying async task) — closing the client connection alone doesn't stop a server that keeps generating into a void.

### Trade-offs

| Benefit | Cost |
|---|---|
| Lower perceived latency (fast time-to-first-token) | Total generation time is unchanged, sometimes slightly higher |
| Enables early cancellation → saves wasted compute | Only saves compute if cancellation is propagated to the LLM call server-side |
| Matches real-time chat UX expectations (ChatGPT-style) | Harder to cache a full response — you're caching/serving chunks, not one value |
| Natural fit for LCEL (`Runnable.stream()` built in) | Mid-stream error handling is harder — a failure partway through leaves a partial, already-rendered response |

### Engineering Insight

This isn't unique to LLMs — it's the general **producer/consumer streaming pattern** (iterators, generators, reactive streams, Node.js streams) applied to inference. The underlying principle: don't materialize the whole result before handing anything to the consumer when the consumer can start useful work on partial data. For LLMs specifically, that "useful work" is both rendering text to a human *and* letting that human cut off a bad response early.

------------------------------------------------------------------------

## Interview Q&A

### Why is streaming valuable?

Because LLM generation is inherently token-by-token and can take several seconds — streaming exposes that incremental output to the client instead of buffering it, which drastically reduces *perceived* latency (time-to-first-token) and lets the client cancel early if the response is going wrong, saving wasted compute.

### Does streaming make the model generate faster?

No. Total generation time is essentially unchanged (or marginally higher due to per-chunk overhead). What improves is when the client starts *seeing* output, not how long generation actually takes.

### What's the difference between token streaming and event streaming?

Token streaming forwards raw model output pieces as they're decoded. Event streaming forwards structured lifecycle events of the entire chain (tool calls, retrieval steps, chain start/end) — token generation is just one event type within that broader stream.

### What architectural change does streaming require compared to a normal REST call?

A normal REST call is one blocking request/response. Streaming requires keeping the connection open across the whole generation and pushing chunks as they're produced — typically via Server-Sent Events, chunked HTTP transfer encoding, or a WebSocket, rather than a single buffered payload.

### How does early cancellation actually save compute?

Only if the cancellation signal from the client (closing the stream) is propagated all the way down to actually stopping the LLM call server-side (e.g. cancelling the async generation task). If the server keeps generating after the client disconnects, cancellation saves nothing.

------------------------------------------------------------------------

## Common Interview Traps

❌ Streaming makes the LLM generate tokens faster.

✔ It doesn't change generation speed at all — it changes when the client sees each token. Perceived latency improves because time-to-first-token is far lower than time-to-last-token, even though total time is the same.

------------------------------------------------------------------------

❌ Streaming is just a frontend "typewriter effect" for show.

✔ It's a real transport-level mechanism (SSE / chunked HTTP / WebSocket) delivering partial results as they're generated — enabling both perceived-latency gains and genuine early cancellation, not a decorative animation.

------------------------------------------------------------------------

❌ Token streaming and event streaming are the same thing.

✔ Token streaming is raw model output, piece by piece. Event streaming is structured lifecycle events across the whole pipeline (tool calls, retrieval steps, chain boundaries), of which token output is only one event type.

------------------------------------------------------------------------

❌ Streaming has no downsides, so it should always be the default.

✔ It adds real cost: harder to cache a full response, harder mid-stream error handling, and client-side incremental-rendering logic. For batch or backend jobs nobody is watching live, non-streaming is simpler and sufficient.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
LLMs generate token by token — streaming just exposes that step-by-step
nature to the client instead of buffering it into one blocking response.

Without streaming:  LLM → [buffer entire output] → Browser   (blank until done)
With streaming:      LLM → token → token → token → Browser   (first token is fast)

Token Streaming  → raw model output, piece by piece
Event Streaming  → structured lifecycle events (tool calls, steps, tokens)

Streaming does not speed up generation — it lowers perceived latency
(time-to-first-token) and enables early cancellation, which only saves
compute if the server actually propagates the cancel down to the LLM call.
```

------------------------------------------------------------------------

# Stage 1 · Week 3 Checklist

You should now be able to explain, without notes:

- [x] Why streaming exists — the engineering problem it solves
- [x] Why streaming is a transport-level mechanism, not a UI animation trick
- [x] The difference between Token Streaming and Event Streaming
- [x] The architecture difference between buffered whole-response delivery and incremental token delivery
- [x] Why perceived latency improves even though total generation time doesn't
- [x] Why early cancellation only saves compute if the server propagates the cancel signal to the LLM call

If you can answer these cold, you understand streaming as a systems concern — not as "the chat bubble types itself out."
