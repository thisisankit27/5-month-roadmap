# Java Exception Handling: Propagation, Cleanup & Design

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not "here's the try-catch syntax." Every rule in this chapter exists to answer one question: **who is responsible for recovering from a failure, and who is responsible for cleaning up after it** — the function that detected the problem, or some caller further up the stack? Get that ownership question right and the syntax is trivial; get it wrong and you get swallowed exceptions, leaked resources, and misleading logs in production.

## Crisp Definition

**An exception is Java's mechanism for interrupting normal control flow when an operation cannot complete — the failure propagates up the call stack, frame by frame, until something handles it or it reaches `main()` and terminates the program.**

------------------------------------------------------------------------

## The Exception Hierarchy — `Throwable`, `Exception`, `Error`

### Engineering Problem

Not all failures deserve the same response. A missing file is recoverable — retry, prompt the user, fall back. Running out of heap memory is not — no amount of catch-block logic fixes `OutOfMemoryError`. Treating both the same way either wastes effort trying to recover from the unrecoverable, or silently swallows failures that genuinely needed handling.

### Definition

```text
Throwable
├── Exception   → can be handled
└── Error       → almost nothing we can do (OutOfMemoryError, StackOverflowError, ...)
```

`Exception` itself splits further:

| | Checked Exception | Unchecked Exception |
|---|---|---|
| Also called | Compile-time exception | Runtime exception |
| Must declare `throws`? | **Yes** — compiler-enforced | No — but should still try to handle where recovery is possible |
| Example | `IOException` | `NullPointerException`, `NumberFormatException` |
| Represents | Conditions the caller can reasonably anticipate and recover from | Programmer errors or environment failures that usually can't be recovered inline |

A function must **declare** (`throws` clause) or **handle** (`try-catch`) every checked exception it can throw. Unchecked exceptions don't require this — but "not required" isn't the same as "should be ignored."

### Why Split Checked from Unchecked at All?

Checked exceptions put a compile-time contract on the caller: "this can fail, and you must decide what to do about it." That's appropriate for conditions the caller can genuinely act on (file missing → prompt for a different path). Forcing the same discipline onto `NullPointerException` would mean wrapping nearly every method call in the language in a try-catch — the exception would stop signaling anything meaningful.

### Engineering Insight

The checked/unchecked split is the type system encoding a **recovery expectation**, not a severity ranking. "Checked" doesn't mean "worse" — it means "the compiler believes the caller has a reasonable chance to do something about this."

------------------------------------------------------------------------

## Propagation — How an Uncaught Exception Kills a Program

### Engineering Problem

When a deeply nested function fails, something has to decide what happens next — does execution continue, does it abort just that function, or does the whole program die? Without a defined propagation rule, every function would need its own ad-hoc failure-signaling convention.

### Definition

Exceptions are thrown in a stack frame. A function that doesn't handle an exception throws it to its caller — and so on, ultimately reaching `main()` (the bottom of the call stack). Since nothing calls `main()`, the program dies there if the exception is still unhandled.

```text
deepFunction() throws
        │
        ▼
   callerFunction() — doesn't catch it, propagates further
        │
        ▼
      main() — nothing calls main(), so the program terminates here
```

### Handling Stops Propagation

`try-catch` breaks this chain — the program doesn't die. Inside a catch block you can:

- **handle** the exception (resolve it, continue normally), or
- **transform it** into a different exception and re-throw:

```java
catch (IOException e) {
    throw new RuntimeException(e);   // unchecked — no "throws" needed on the enclosing method
}
```

- ensure cleanup activity still happens (covered under `finally` below).

### Engineering Insight

Propagation is just the call stack unwinding in reverse — a `Throwable` isn't magic, it's a control-flow signal that says "abandon the rest of this frame and let the caller decide." That's exactly why an *uncaught* exception in `main()` kills the program: there's no caller left to decide anything.

------------------------------------------------------------------------

## Catching by Type — Parent vs. Child

### Engineering Problem

A caller often wants to handle a category of failures (`IOException`) the same way, while still being able to single out one specific case (`FileNotFoundException`) for special treatment. The catch mechanism needs to respect the exception's type hierarchy for this to work.

### Definition

A function that can throw `<Parent_Exception>` is also capable of throwing its `<Child_Exception>` — but not the reverse. Symmetrically, a `catch` block catches everything assignable to its declared parameter type: **catching the parent also catches every child**, but catching a child does not catch its parent.

### Ordering Rule for Multiple Catch Blocks

- Always catch more **specific** (child) exceptions **first**.
- Catch more **general** (parent) exceptions **later**.

**Reason:** if the parent is caught first, the child's catch block becomes unreachable code — every exception the child block would have handled is already absorbed by the parent block above it. The Java compiler rejects unreachable catch blocks outright.

### `instanceof` Branching vs. Multiple Catch Blocks

```java
// Discouraged: relies on reflection-style type-checking inside one catch block
try {
    // something that throws IOException or TooManyRequestException
} catch (Exception e) {
    if (e instanceof IOException) {
        //
    } else if (e instanceof TooManyRequestException) {
        //
    }
}

// Preferred: let the language's own dispatch do the branching
try {
    // something that throws IOException or TooManyRequestException
} catch (IOException e) {
    //
} catch (TooManyRequestException e) {
    //
}
```

### Engineering Insight

The `instanceof` chain is manual dispatch bolted onto a mechanism (multiple catch blocks) that already does type-based dispatch natively. Preferring the specific-then-general catch chain is the same principle as preferring polymorphic dispatch over a chain of `if (type == X)` checks anywhere else in OOP.

------------------------------------------------------------------------

## User-Defined Exceptions

### Engineering Problem

The built-in exception types (`IOException`, `NumberFormatException`, ...) describe *technical* failure modes. Domain failures — `InvalidPhoneNoException`, `InsufficientBalanceException` — need their own vocabulary so callers and logs can reason about *business* failures directly, instead of translating a generic exception's message every time.

### Definition

To create a custom exception, extend either:

- `Exception` (or any of its subclasses) → a **checked** exception, or
- `RuntimeException` → an **unchecked** exception.

Custom exceptions are usually made **checked** because you want the caller/client to explicitly handle them — this enforces correctness at compile time, for failures the caller genuinely has a shot at recovering from.

### The Four Canonical Constructors

When creating a custom exception, you generally provide four constructors to match the ones available on `Throwable`/`Exception`:

```java
class A extends Exception {
    A() {                                    // Default constructor
        super();
    }

    A(String message) {                      // Message constructor
        super(message);
    }

    A(Throwable cause) {                     // Cause constructor
        super(cause);
    }

    A(String message, Throwable cause) {      // Message + cause constructor
        super(message, cause);
    }
}
```

| Constructor | Purpose |
|---|---|
| `A()` | Exception without details |
| `A(String)` | Human-readable error message |
| `A(Throwable)` | Exception chaining — wrap another exception |
| `A(String, Throwable)` | Message + root cause together |

### Engineering Insight

Providing all four isn't boilerplate for its own sake — each constructor exists because callers of your exception class need different amounts of context depending on *how* they discovered the failure: sometimes just a signal, sometimes a message, sometimes another exception to wrap and preserve.

------------------------------------------------------------------------

## Exception Message vs. Cause — Why Both Exist

### Engineering Problem

A failure has two different audiences: the end user (or a log line) who needs to know *what* went wrong in plain language, and the developer who needs to know *why*, down to the stack trace. Collapsing both into one string either exposes internal details to users, or loses the debugging trail entirely.

### Definition

```text
Exception Message (String)      → what the user should know
Throwable / Cause (Throwable)   → what the developer needs to fix
```

**Message** — a high-level, human-readable explanation, intended for users, support teams, and logs/error responses. Explains *what* went wrong, not *how*.

```java
throw new InvalidAgeException("Age must be 18 or above");
```

**Cause** — the actual root cause, intended for developers debugging the issue. Contains the stack trace, execution path, and low-level technical details.

### Exception Chaining

```java
try {
    Integer.parseInt("abc");
} catch (NumberFormatException e) {
    throw new InvalidAgeException("Invalid input", e);   // e is preserved as the cause
}
```

This preserves the original stack trace and helps debugging — it's exactly why constructors accepting a `Throwable cause` exist.

### Why Keeping Them Separate Matters

- Avoids exposing internal implementation details to end users.
- Preserves full debugging information for developers, instead of discarding it once a human-friendly message is chosen.

### Engineering Insight

This is the same Single Responsibility split as the message/cause distinction anywhere in error handling: one field serves *communication*, the other serves *diagnosis* — conflating them serves neither audience well.

------------------------------------------------------------------------

## Serialization and `serialVersionUID`

### Engineering Problem

`Throwable` (and therefore every exception) is `Serializable`. If a class's structure changes between when an object was serialized and when it's deserialized, the JVM has no inherent way to know whether the two versions are compatible.

### Definition

**Serialization** converts an object into a byte stream. **Deserialization** converts that byte stream back into an object.

### The Versioning Problem

Suppose version 1 of a class has one field, and version 2 evolves to have multiple fields. If an object serialized under the old version is deserialized using the new class version, the JVM may not be able to match the class structure correctly — leading to unpredictable behavior or errors.

### How `serialVersionUID` Fixes This

Java uses a version identifier, declared as:

```java
private static final long serialVersionUID = -89823645623L;
```

**Purpose:** ensures the serialized and deserialized class versions match. If versions differ, the JVM throws `InvalidClassException` instead of silently misreading the byte stream.

**One-line interview answer:** *`serialVersionUID` is used to ensure version compatibility during serialization and deserialization of objects.*

------------------------------------------------------------------------

## The `finally` Block

### Engineering Problem

It's your responsibility to close allocated physical resources (a `FileReader`, a socket, ...) — the garbage collector won't do it for you. Closing at the end of a block works when nothing goes wrong, but when an exception is thrown mid-block, that close call is skipped — leaking the resource and potentially triggering a *second* failure downstream (e.g. "too many open files"). Duplicating the close call into every catch block works, but it's redundant, error-prone code.

### Definition

`finally` executes **always** — whether an exception was thrown or not, and whether it was caught or not. It ensures resource cleanup and eliminates the redundant close-call duplication.

### When Code After `finally` Runs

Code after `try-catch-finally` (or `try-finally`) executes normally, even if an exception was thrown, **as long as the exception is handled or doesn't terminate the program**.

| Case | Code after `finally` runs? |
|---|---|
| Exception thrown and handled | ✔ Yes |
| No exception thrown | ✔ Yes |
| Exception thrown but **not** handled | ✘ No |

Code after `finally` will **not** run only if:

- the exception is not caught,
- `System.exit()` is called,
- the JVM crashes, or
- a fatal error occurs (e.g. `OutOfMemoryError`).

### The Null-Check Gotcha

```java
FileReader fr = null;
try {
    fr = new FileReader("missing.txt");   // throws exception
} catch (FileNotFoundException e) {
    System.out.println("File not found");
} finally {
    fr.close();   // NullPointerException
}
```

**What happened:** `fr` was declared, but initialization failed, so `fr` remains `null`. `finally` still executes unconditionally — and `fr.close()` on a `null` reference throws an `NullPointerException`, masking the fact that the real problem was a missing file. `finally` must always guard resource cleanup with a null check (`if (fr != null) fr.close();`).

### Engineering Insight

`finally`'s unconditional-execution guarantee is exactly why it exists for cleanup rather than for business logic — it's the one place in the language explicitly documented to run regardless of *how* the try block exits, which is precisely the property resource cleanup needs.

------------------------------------------------------------------------

## Nested Try-Catch(-Finally)

### Engineering Problem

Sometimes one resource depends on another, and different operations within the same block can fail for genuinely different reasons — collapsing them into one flat catch loses the ability to say exactly which step failed.

### When to Use

- Resource-dependent operations.
- Step-by-step failure handling.
- Need for specific error context per operation.

### Alternative

Multiple catch blocks can also separate failure types, but nested try-catch gives more localized handling — the failure context is scoped to exactly the operation that produced it.

### When *Not* to Use

- Over-nesting hurts readability.
- Prefer `try-with-resources` when possible (see below).

### Does the Outer Catch Also Catch What the Inner Catch Already Caught?

**No.** Once an exception is caught and handled, it's considered resolved and does **not** propagate to the outer try-catch.

The outer catch executes **only** if:

- the inner catch doesn't exist for that exception type, **or**
- the inner catch explicitly rethrows the exception.

### Engineering Insight

This is the same "handled means handled" rule that governs any layered error-handling system: a catch block is a boundary, not a checkpoint everything passes through regardless.

------------------------------------------------------------------------

## Exception Masking — The Problem With `finally`

### Engineering Problem

If code inside `finally` itself throws, what happens to the exception that was already propagating from `try` or `catch`?

### The Failure Mode

```java
try {
    throw new IOException("IO failed");
}
catch (Exception e) {
    throw e;
}
finally {
    fr.close();   // if this throws FileNotFoundException
}
```

**Result:** the exception from `finally` is what propagates. The original `IOException("IO failed")` is **lost**. Debugging becomes misleading — this is called **exception masking**.

### Why This Happens

The JVM allows only **one** exception to propagate at a time. Whichever exception is thrown *last* (from `finally`) wins; the earlier one is silently discarded.

### Why This Is Dangerous

- The root cause is hidden.
- Logs show a misleading error — the symptom (`FileNotFoundException` on close) instead of the actual failure (`IOException`).
- Production debugging becomes very hard.

### Manual Workaround

```java
Exception primaryException = null;
try {
    throw new IOException("IO failed");
}
catch (Exception e) {
    primaryException = e;
    throw e;   // rethrow original exception
}
finally {
    try {
        if (fr != null) {
            fr.close();
        }
    } catch (Exception closeEx) {
        if (primaryException == null) {
            throw closeEx;   // no earlier exception → propagate the cleanup failure
        }
        // else: suppress / log the cleanup exception, don't let it mask the original
    }
}
```

### Engineering Insight

Exception masking is a case of one failure signal silently overwriting another — the exact class of bug `try-with-resources` (next section) was designed to eliminate by keeping *both* exceptions instead of discarding one.

------------------------------------------------------------------------

## Try-With-Resources

### Engineering Problem

The manual workaround above (tracking a `primaryException`, nested try-finally for cleanup) is correct but verbose, and easy to get wrong by hand every time a resource needs closing.

### Definition

`try-with-resources` automatically closes resources at the end of the try block, for any class implementing `AutoCloseable` (or its sub-interface `Closeable`). `close()` is called even if an exception is thrown inside the try block.

```java
public class MyResource implements AutoCloseable {
    @Override
    public void close() throws IOException {
        System.out.println("came to exception close()");
        throw new FileNotFoundException();
    }
}

public class TryWithResources {
    public static void main(String[] args) throws Exception {
        try (MyResource mr = new MyResource()) {
            System.out.println("came in try");
            if (true)
                throw new RuntimeException();
        } catch (Exception e) {
            throw e;
        }
    }
}
```

**Output:**

```text
came in try
came to exception close()
Exception in thread "main" java.lang.RuntimeException
    at ExceptionHandling.TryWithResources.main(TryWithResources.java:9)
    Suppressed: java.io.FileNotFoundException
        at ExceptionHandling.MyResource.close(MyResource.java:11)
        at ExceptionHandling.TryWithResources.main(TryWithResources.java:10)
```

The **primary exception** (`RuntimeException`, from the try block) is what's thrown. The **`close()` exception** (`FileNotFoundException`) is **suppressed, not lost** — it's attached to the primary exception and still visible in the stack trace.

### `AutoCloseable` vs. `Closeable`

```text
AutoCloseable
     ↑
 Closeable
```

| | `AutoCloseable` | `Closeable` |
|---|---|---|
| Signature | `void close() throws Exception;` | `void close() throws IOException;` |
| Scope | Very broad — any checked exception, any resource | Narrower — I/O-related exceptions only |
| Typical use | Any kind of resource | Streams, readers, writers |

**Interview-perfect answer:** *`Closeable` is a sub-interface of `AutoCloseable` designed specifically for I/O resources and restricts `close()` to throwing `IOException`, whereas `AutoCloseable` is more general and allows any exception.*

### Multiple Resources — Initialization and Closing Order

```java
try (Resource1 r1 = new Resource1();
     Resource2 r2 = new Resource2();
     Resource3 r3 = new Resource3()) {
    // use resources
}
```

- All resources must implement `AutoCloseable` (or `Closeable`).
- **Initialization order:** left → right — `r1 → r2 → r3`.
- **Closing order (important):** right → left, the **reverse** — `r3 → r2 → r1`. This ensures dependencies are closed safely (a resource is never closed while something built on top of it is still open).
- **No `finally` needed** — the JVM guarantees cleanup. No null checks, no resource leaks.

### Engineering Insight

Try-with-resources is the language codifying the exact discipline the manual `primaryException` workaround was hand-rolling: guaranteed cleanup, reverse-order closing, and *suppression* instead of *masking* when cleanup itself fails. It's a strict improvement over `finally`-based cleanup wherever the resource type allows it.

------------------------------------------------------------------------

## Exception Translation — Checked to Unchecked at Interface Boundaries

### Engineering Problem

```java
interface Task {
    void start();
}
```

If an implementation needs to do I/O:

```java
class FileTask implements Task {
    @Override
    public void start() throws IOException {   // ✘ not allowed
    }
}
```

Java forbids this. Why?

### Why Java Forbids Widening the Throws Clause on Override

- An **interface is a contract**: `Task.start()` promises callers it throws no checked exceptions.
- The caller of `Task.start()` must not be surprised by a new checked exception appearing only because a *particular implementation* happens to do I/O — that would break every existing caller written against the interface.
- This is the **Liskov Substitution Principle** in action: a subtype (here, an implementation) must be usable anywhere the supertype (interface) is expected, without the caller needing to know which concrete implementation it received.

So Java is enforcing the *right* constraint here — the two remaining questions are what `FileTask.start()` should do with the `IOException` it actually encounters.

### Option A — Swallow the Exception (Bad)

```java
try {
    readFile();
} catch (IOException e) {
    // ignore
}
```

Almost always bad: the failure is hidden, debugging becomes very hard, and the system can enter an inconsistent state silently. Swallowing is only acceptable when you're **100% sure** the failure is irrelevant, or you explicitly log it and degrade gracefully.

### Option B — Wrap Into an Unchecked Exception (Good)

```java
try {
    readFile();
} catch (IOException e) {
    throw new RuntimeException(e);
}
```

This works because unchecked exceptions don't need to be declared — the interface contract remains intact, and the failure still propagates instead of being silently swallowed. This isn't a workaround; it's a deliberate escape hatch Java's designers built in.

### The Senior-Level Refinement — Don't Throw Raw `RuntimeException`

Instead, create a domain-specific unchecked exception:

```java
public class TaskExecutionException extends RuntimeException {
    public TaskExecutionException(String message, Throwable cause) {
        super(message, cause);
    }
}
```

```java
try {
    readFile();
} catch (IOException e) {
    throw new TaskExecutionException("Failed to start FileTask", e);
}
```

**Why this is better:**

- Preserves semantic meaning — `TaskExecutionException` says *what kind* of failure this is, not just "something threw."
- The stack trace keeps the original cause (`e`).
- Callers can optionally catch `TaskExecutionException` specifically if they want to.
- Logs become self-explanatory instead of showing a generic `RuntimeException`.

This is how mainstream frameworks (Spring, Hibernate, ...) handle exactly this situation.

### Why Unchecked Exceptions Are the Right Fit Here

Unchecked exceptions are ideal when:

- the caller cannot reasonably recover,
- the failure is environmental (I/O, DB, network) rather than a business condition, and
- you want to avoid polluting the interface with technical implementation details.

`Task.start()` is a **behavioral** contract, not a technical one. Forcing `IOException` into the interface would leak an implementation detail (this particular `Task` happens to read a file) into a contract meant to describe *behavior*, not mechanism. Wrapping into unchecked is good design here, not a compromise.

### Engineering Insight

This whole pattern — **throw early, catch/translate later** — means the intermediate layer wraps (translates) a low-level, leaf exception and forwards a higher-level one up the call stack. It's the same idea as an Adapter: the technical failure detail stays at the boundary where it was detected, and callers further up only ever see a contract they were promised.

------------------------------------------------------------------------

## Stack Traces

### Definition

`printStackTrace()` is a method on `Throwable` (available on every exception, since all exceptions extend `Throwable`). For structured, per-frame access, `getStackTrace()` returns a `StackTraceElement[]`, where each element exposes:

- `getClassName()`
- `getMethodName()`
- `getLineNumber()`
- `getFileName()`
- `isNativeMethod()`

```java
catch (Exception e) {
    for (StackTraceElement ste : e.getStackTrace()) {
        System.out.println(
            ste.getClassName() + " | " +
            ste.getMethodName() + " | " +
            ste.getLineNumber()
        );
    }
}
```

Example output:

```text
com.example.service.FileService | readData | 42
com.example.controller.Main      | start    | 18
```

### Why This Is Useful

Compact, human-readable, easy to pipe into structured logs — much cleaner than dumping a full `printStackTrace()` when you only need the failure's location, not its entire formatted text block.

------------------------------------------------------------------------

## Interview Q&A

### Can a function that declares `throws ParentException` also throw a child of that exception?

Yes — a function capable of throwing a parent exception type can throw any of its children too. The reverse doesn't hold: declaring a child exception type doesn't authorize throwing the parent.

### Why must multiple catch blocks be ordered specific-to-general?

Because catching a parent type also catches all its children. If the parent's catch block came first, the child's catch block beneath it would never be reachable — every exception it was written to handle is already absorbed above it. The compiler rejects this as unreachable code.

### Why is checking `instanceof` inside a single catch block discouraged?

Because it re-implements, by hand, the type-based dispatch that multiple catch blocks already provide natively — the same reasoning as preferring polymorphism over manual type checks anywhere else.

### Why are custom exceptions usually made checked rather than unchecked?

Because you want the caller/client to be forced to explicitly handle them — checked exceptions enforce that decision at compile time, which is appropriate when the failure is one the caller can reasonably recover from.

### What are the four canonical constructors on a custom exception, and why have all four?

No-arg, `(String message)`, `(Throwable cause)`, and `(String message, Throwable cause)` — matching `Throwable`'s own constructors. Different call sites discover failures with different amounts of context (just a signal, a message, or another exception to wrap), and each constructor serves one of those cases.

### What's the difference between the exception's message and its cause?

The message is a high-level, human-readable explanation for users/logs/support. The cause is the actual root `Throwable`, carrying the stack trace and technical detail, intended for developers. Keeping them separate avoids leaking internals to users while preserving full debugging information.

### What is `serialVersionUID` for?

It ensures version compatibility during serialization and deserialization of objects — if the serialized and deserializing class versions don't match, the JVM throws `InvalidClassException` instead of silently misreading the byte stream.

### Under what conditions does code *after* a `try-catch-finally` block NOT run?

Only if the exception isn't caught, `System.exit()` is called, the JVM crashes, or a fatal error like `OutOfMemoryError` occurs. Otherwise — handled exception or no exception at all — execution continues normally after `finally`.

### Why must resource cleanup in `finally` be null-checked?

Because if the resource's initialization itself threw (e.g. `new FileReader(...)` failed), the reference is still `null` when `finally` runs — `finally` executes unconditionally, so calling `.close()` on a null reference throws a `NullPointerException` that masks the real failure.

### Does an outer catch block also catch an exception already caught by an inner catch block?

No. Once an exception is caught and handled by the inner catch, it's resolved and does not propagate outward. The outer catch only runs if the inner catch doesn't exist for that exception type, or if the inner catch explicitly rethrows.

### What is exception masking, and why is it dangerous?

If `finally` itself throws, that exception overrides whatever was already propagating from `try`/`catch` — the JVM only lets one exception propagate at a time, and the last one thrown wins. The original root cause is silently lost, which makes logs misleading and production debugging very hard.

### How does try-with-resources avoid exception masking?

If both the try block and the resource's `close()` throw, the primary exception (from the try block) is what propagates, and the `close()` exception is attached as a **suppressed** exception rather than discarding either one — both remain visible in the final stack trace.

### In what order are multiple try-with-resources closed?

Reverse of initialization order — right to left. If `r1`, `r2`, `r3` were opened in that order, they close as `r3`, `r2`, `r1`, so a resource is never closed while something built on top of it is still open.

### Why can't an interface method implementation add a new checked exception the interface doesn't declare?

Because the interface is a contract callers rely on — the Liskov Substitution Principle requires that any implementation be usable wherever the interface is expected, without surprising the caller with exceptions the contract never promised.

### Given that constraint, how should a checked exception from an implementation detail be surfaced?

Wrap it into an unchecked exception — ideally a domain-specific one (e.g. `TaskExecutionException extends RuntimeException`) rather than a raw `RuntimeException`, so the semantic meaning is preserved, the original cause is chained, and the interface's contract stays intact.

### Why are unchecked exceptions the right fit for wrapping environmental failures like I/O errors at an interface boundary?

Because the caller usually can't recover from them anyway, the failure is environmental rather than a business condition the caller should branch on, and forcing the checked type into the interface would leak an implementation detail into what should be a purely behavioral contract.

------------------------------------------------------------------------

❌ Checked exceptions are "more serious" than unchecked ones.

✔ The split isn't about severity — it's about whether the compiler believes the caller has a reasonable chance to recover. Unchecked failures (like `OutOfMemoryError`'s sibling class, or a bad cast) can be just as serious.

------------------------------------------------------------------------

❌ `finally` runs "usually," as long as things go roughly to plan.

✔ It runs unconditionally on every path out of the try block except `System.exit()`, a JVM crash, a fatal error, or an exception that's never caught at all.

------------------------------------------------------------------------

❌ If an inner try-catch handles an exception, the outer catch still gets a chance to see it too, "just in case."

✔ A handled exception is resolved — it does not propagate outward unless the inner catch explicitly rethrows it.

------------------------------------------------------------------------

❌ If `finally` throws, both the original and the `finally` exception are reported.

✔ Without try-with-resources, only the *last* exception thrown (from `finally`) propagates — the original is silently discarded. This is exception masking, and it's exactly what try-with-resources's suppressed-exception mechanism was built to avoid.

------------------------------------------------------------------------

❌ You should never let an implementation detail like `IOException` escape an interface method — just swallow it.

✔ Swallowing hides real failures. The correct move is translating it into an unchecked exception (ideally a domain-specific one) so the interface contract stays intact *and* the failure still propagates.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
Throwable
├── Exception  → can be handled (checked: must declare/handle; unchecked: should still try)
└── Error      → don't bother trying to recover

Catch order    → specific (child) before general (parent), or it won't compile

finally        → runs always; guard resource cleanup with a null check

Nested catch   → handled means handled; doesn't leak to the outer catch
                 unless explicitly rethrown

finally throws → masks (discards) whatever was already propagating
try-with-resources → suppresses instead of masking; closes in reverse order

Interface method → cannot widen checked exceptions on override (Liskov)
Fix              → wrap the checked exception into a domain-specific
                    unchecked exception, preserve the cause

Message  → for humans (what)
Cause    → for developers (why) — preserve it, always
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain the difference between checked and unchecked exceptions, and why the split exists
- [x] Explain how an uncaught exception propagates up the call stack and terminates a program
- [x] Explain why catch blocks must be ordered specific-to-general
- [x] Explain why the four canonical custom-exception constructors exist
- [x] Explain the difference between an exception's message and its cause, and why both matter
- [x] Explain what `serialVersionUID` is for
- [x] Explain why `finally` needs a null check before closing a resource
- [x] Explain exception masking, and how try-with-resources avoids it
- [x] Explain the initialization and closing order for multiple try-with-resources
- [x] Explain why an interface implementation can't add new checked exceptions, and how to work around it correctly
