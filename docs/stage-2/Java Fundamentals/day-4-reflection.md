# Java Reflection: Runtime Introspection, Serialization & Dependency Injection

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not "here's the `java.lang.reflect` API." Reflection is the mechanism that lets frameworks do things your own code structurally can't — inspect a class it has never seen before, at runtime, and act on it. The goal is to understand *why* frameworks need this escape hatch from the type system, and why it stays an escape hatch rather than something you reach for in business logic.

## Crisp Definition

**Reflection lets Java inspect and manipulate classes, fields, methods, and constructors at runtime, even when none of that structure was known at compile time.**

------------------------------------------------------------------------

## What Problem Does Reflection Solve?

### Engineering Problem

Normally in Java you know class names, methods, and fields, and everything is checked at compile time. But sometimes you genuinely don't know **which class will be loaded**, **which methods exist**, or **which fields exist** until runtime — a plugin system loading a class by name from config, a serializer handed an arbitrary object, a framework instantiating whatever class you annotated. Compile-time-only tooling has no way to act on types it has never seen.

### Definition

Reflection lets Java **inspect itself at runtime** — treat a class, its fields, and its methods as data you can query and invoke programmatically, instead of only writing code against them directly.

### Engineering Insight

Reflection trades the compiler's static guarantees for runtime flexibility. That trade is exactly why it belongs at framework boundaries (where the framework genuinely can't know your types in advance) and not inside business logic (where the types are always known, and the compiler's checks are a feature, not an obstacle).

------------------------------------------------------------------------

## The Meta-Class: `Class<T>`

### Core Idea

Objects have data. Classes *also* have data — their own structure — and that data is represented by an object of type `Class`.

```java
public static void main(String[] args) {
    String s = new String();
    Class<?> cls = s.getClass();
    System.out.println(cls.getName());
}
// Output: java.lang.String
```

### Definition

`Class<?> cls = obj.getClass();` returns an object representing the **structure** of the class — it knows the class name, fields, methods, constructors, and modifiers. `Class` is just a normal Java class, not magic:

```java
public class Object {
    public final Class<?> getClass() { ... }
}
```

Every class extends `Object` — therefore every object has `getClass()`.

- `.getName()` → returns the fully qualified class name.

### Engineering Insight

Every object carries a reference to a description of its own type, reachable through one universal method. That's what makes reflection possible in the first place: the metadata isn't bolted on externally, it's part of what `Object` guarantees to every class in the language.

------------------------------------------------------------------------

## Inspecting Structure — Fields, Methods, Constructors

| Call | Returns |
|---|---|
| `cls.getDeclaredFields()` | Only fields **declared in this class** — includes `private`/`protected`/`public`, **excludes** inherited fields |
| `cls.getDeclaredMethods()` | Same as fields — declared in this class only, all access levels, no inherited methods |
| `cls.getMethods()` | **All public methods** of the current class, all superclasses, and all implemented interfaces — including inherited ones like `toString()`, `equals()`, `hashCode()` from `Object` |
| `cls.getDeclaredConstructors()` | Constructors declared in this class |

### Walking the Class Hierarchy — `getSuperclass()`

```java
Class<?> parent = cls.getSuperclass();
```

Returns the **direct (immediate)** parent class of the given class.

```java
public class ReflectionDemo {
    public static void main(String[] args) {
        ReflectionDemo s = new ReflectionDemo();
        Class<?> cls = s.getClass();
        while (cls != null) {   // after reaching Object, the next getSuperclass() is null
            Method[] m = cls.getDeclaredMethods();
            System.out.println("\n" + cls.getName());
            for (Method method : m)
                System.out.println(method);
            cls = cls.getSuperclass();
        }
    }
}
```

### Why Interfaces Aren't Returned by `getSuperclass()`

Java allows only **one** superclass — `getSuperclass()` walks a single chain. Interfaces are a separate relationship entirely, retrieved with `cls.getInterfaces()`.

------------------------------------------------------------------------

## Why Reflection Is Powerful (and Dangerous)

| Power | Danger |
|---|---|
| Frameworks (Spring, Hibernate) | Breaks encapsulation |
| Dependency Injection | Slower than normal calls |
| Serialization | Compile-time safety lost |
| ORM | Harder to debug |
| Test frameworks (JUnit) | — |

### Engineering Insight

This is exactly why **reflection is used by frameworks, not daily business code** — frameworks accept the cost because they're solving a genuinely generic problem (act on types you don't know yet); business code almost always knows its types at compile time, so paying reflection's cost there buys nothing.

------------------------------------------------------------------------

## Invoking Methods via Reflection — Access Control

### Engineering Problem

`getDeclaredMethod()` can *locate* a private method — but locating isn't the same as being allowed to call it. If reflection could bypass `private` for free, access modifiers would mean nothing at runtime.

### Definition

```java
Method m = cls.getDeclaredMethod("methodName", paramTypes...);
```

- Returns a method **declared in the class itself**, including `private`, `protected`, default, and `public`.
- Does **not** include inherited methods.
- **Access checks are still enforced by default.**

### The Failure — Access Checks Still Apply

```java
class Secret {
    private void hiddenMethod() {
        System.out.println("Hidden method executed");
    }
}

public class TestReflection {
    public static void main(String[] args) throws Exception {
        Secret obj = new Secret();
        Class<?> cls = obj.getClass();
        Method m = cls.getDeclaredMethod("hiddenMethod");
        m.invoke(obj);   // ✘ fails
    }
}
// Runtime Error: java.lang.IllegalAccessException
```

**Reason:** Java does not allow invoking private members reflectively by default — you can *find* a private method, but you cannot *invoke* it without one more step.

### The Fix — `setAccessible(true)`

```java
Method m = cls.getDeclaredMethod("hiddenMethod");
m.setAccessible(true);   // override access checks
m.invoke(obj);           // now it works
// Output: Hidden method executed
```

**What `setAccessible(true)` really does:**

- Disables Java language access checks.
- Allows access to private methods, private fields, private constructors.
- Works at **runtime only** — the compiler's own checks are untouched.
- Bypasses encapsulation.

### Why This Is Dangerous

Reflection with `setAccessible(true)`:

- breaks encapsulation,
- can access sensitive data,
- can violate class invariants,
- makes code fragile and unsafe,
- is harder to debug, and
- is slower than normal calls.

That's why reflection — especially with `setAccessible(true)` — is used by frameworks, not business logic.

### Security Aspect

`setAccessible(true)` can throw `SecurityException` when a `SecurityManager` is installed or the environment forbids reflective access — common in secure JVMs, application servers, and sandboxed environments.

**Interview one-liner:** *`getDeclaredMethod()` retrieves methods declared in a class, but private methods require `setAccessible(true)` to bypass access checks, which can throw `SecurityException` and is potentially unsafe.*

------------------------------------------------------------------------

## Specifying Parameter Types — Primitive Class Literals

### Method Signature

```java
Method m = cls.getDeclaredMethod(String name, Class<?>... parameterTypes);
```

- First argument → the method name.
- Second argument → one `Class` object per parameter, **in order** — order must match exactly.

### `int` Is Not a Class — But Java Provides Primitive Class Literals

```java
int.class
double.class
boolean.class
```

These are special JVM-backed `Class` objects, not wrapper classes — they let you describe a primitive parameter type to a reflective API that otherwise only deals in `Class<?>` objects.

```java
class Calculator {
    private int add(int a, int b) {
        return a + b;
    }
    private String concat(String a, int b) {
        return a + b;
    }
}

Class<?> cls = Calculator.class;

Method m1 = cls.getDeclaredMethod("add", int.class, int.class);        // matches add(int, int)
Method m2 = cls.getDeclaredMethod("concat", String.class, int.class);  // order and types must match exactly
```

### Invoking the Method

```java
Object result = m.invoke(Object target, Object... args);
```

```java
Calculator obj = new Calculator();
Object res = m1.invoke(obj, 3, 4);
System.out.println(res);   // 7
```

**Important details:**

- Arguments are passed as `Object`s — Java automatically boxes primitives (`3` → `Integer.valueOf(3)`) at **compile time**, before your program ever runs.
- The return value is always `Object` — cast it if you need the concrete type.

**Working example, end to end:**

```java
public class ReflectionDemo {
    public static void main(String[] args) throws Exception {
        Calculator obj = new Calculator();
        Class<?> cls = obj.getClass();
        Method m = cls.getDeclaredMethod("add", int.class, int.class);
        m.setAccessible(true);
        Object result = m.invoke(obj, 5, 7);
        System.out.println(result);   // 12
    }
}
```

### Side Note — Why a Primitive Array Doesn't Satisfy a Varargs Generic

The same autoboxing/erasure mechanics that make `invoke(Object target, Object... args)` work also explain a common surprise elsewhere:

```java
@SafeVarargs
static <T> void printArray(T... a) {
    for (T t : a) System.out.print(t + " ");
}

int[] arr = {1, 2, 3, 4, 5};
printArray(arr);   // does NOT print 1 2 3 4 5
```

**Rule:** generics work when the *elements* are reference types, not when the *container* is a reference type. `int[]` is itself a reference type — so Java infers `T = int[]`, and the whole array becomes a **single element**, not five. A `String[]` doesn't have this problem, because its elements (`String`) are already reference types.

**Final mental model:**

```text
Generics force reference types.
Varargs only bundle same-type values into an array.
Autoboxing happens at compile time, not runtime.
Runtime only sees objects, due to type erasure.

Varargs decide how many, generics decide what kind,
and autoboxing happens before runtime.
```

------------------------------------------------------------------------

## Reflection Use Case 1 — Serialization

### Engineering Problem

An object living in JVM heap memory is useless to a REST API, a cache, or another microservice — none of them can read Java heap objects directly. Something has to convert an object into a transferable format, and convert it back.

### Definition

**Serialization** converts an object into a transferable format:

```text
Java Object → JSON → bytes (over network / file)
```

**Deserialization** is the reverse: `bytes / JSON → Java Object`.

### Why We Need It

- APIs (REST)
- Network communication
- Caching (Redis)
- File storage
- Microservices talking to each other

### Where Reflection Fits In

At runtime, generic serialization code doesn't know a given object's fields, getters/setters, or annotations in advance. Serialization uses **reflection** to inspect the class structure, read private fields, and call getters/setters dynamically — exactly the "types unknown until runtime" problem reflection exists for.

### Why Serialization Is Complicated

- Nested objects
- Lists / Maps
- Null handling
- Custom field names
- Date formats
- Ignoring fields
- Circular references

That's why we don't hand-write it in real projects — **Jackson** (and libraries like it) does this internally: heavy use of reflection, converting Object ↔ JSON ↔ bytes while honoring annotations.

**Interview gold lines:**

- "Serialization converts objects into a transferable format like JSON or bytes."
- "Reflection enables runtime inspection, which serializers use to access fields dynamically."
- "Spring uses Jackson internally for request/response body serialization."
- "We avoid manual serialization due to complexity and performance concerns."

### A Minimal Hand-Rolled Serializer

```java
package serialization;

import java.lang.reflect.*;

public class Serializer {
    public static String serialise(Object obj) throws Exception {
        String output;
        Class<?> cls = obj.getClass();
        output = cls.getName() + ":{";
        Field[] fields = cls.getDeclaredFields();
        for (Field f : fields) {
            Class<?> fieldType = f.getType();
            if (Modifier.isTransient(f.getModifiers()))   // skip transient fields
                continue;
            f.setAccessible(true);
            if (fieldType.isPrimitive()) {
                output += f.getName() + ":" + f.get(obj) + ",";
            } else if (fieldType.isArray()) {
                // left as an exercise — arrays need their own recursive handling
            } else {
                output += serialise(f.get(obj));
            }
        }
        output = output.substring(0, output.length() - 1) + "}";
        return output;
    }
}
```

```text
serialization.ReportCard:{id:1,serialization.ScienceMarks:
{phyMarks:0,chemMarks:0,mathMarks:0,sciPercent:0.0}serialization.ArtsMarks:
{socialSciMarks:0,literatureMarks:0,artsPercent:0.0}totalPercent:0.0}
```

### What a Senior Dev Immediately Guards Against

- Cyclic references (this recursive version would stack-overflow on one)
- `null` handling
- Static fields (should almost always be excluded)
- Transient fields (already handled above)
- Inheritance (`getSuperclass()` — declared fields alone miss inherited ones)
- Collections / arrays
- Performance (string concatenation in a loop → `StringBuilder`)
- Stack overflow risk on deep/cyclic structures
- Security concerns of `setAccessible(true)`
- API contract — what format, deterministic field order?

### Engineering Insight

This toy serializer demonstrates *why* Jackson exists rather than replacing it — every item in the guard-against list above is a real production concern that a hand-rolled reflective serializer has to solve from scratch, and a mature library already has.

------------------------------------------------------------------------

## Reflection Use Case 2 — Deserialization & Runtime Class Loading

### Engineering Problem

Serialized data is not executable code — it's a byte stream that references a class **by name**. Deserialization needs the actual class definition available at runtime to reconstruct an object; it can't reconstruct behavior it has no class metadata for.

### Compile-Time Classpath vs. Runtime Classpath

| | Compile-Time Classpath | Runtime Classpath |
|---|---|---|
| Used by | The compiler (`javac`) | The JVM |
| Needed to | Compile source code, resolve symbols | Load classes, deserialize objects, execute bytecode |
| Sufficient for deserialization? | **No** | **Yes — required** |

If the class is missing from the runtime classpath → `ClassNotFoundException`.

### Deserialization — Key Flow

1. The serialized stream contains the **Fully Qualified Class Name (FQCN)**.
2. The JVM tries to load that class via the runtime classpath.
3. If found → class loaded, object reconstructed.
4. If not found → deserialization fails.

### `Class.forName()` — Dynamic Class Loading

```java
Class<?> cls = Class.forName("com.example.User");
```

- Loads the class at runtime.
- Requires the FQCN, and the class must be present on the runtime classpath.
- Triggers class loading and static initialization.

### Creating an Object at Runtime (Reflection)

```java
Class<?> cls = Class.forName("com.example.User");
Object obj = cls.getDeclaredConstructor().newInstance();
```

Used when the class name is only known at runtime — frameworks, serializers, plugins.

**Deprecated way:**

```java
Class<?> cls = Class.forName("serialization.ReportCard");
Object o = cls.newInstance();   // deprecated
```

**Correct way:**

```java
Class<?> cls = Class.forName("serialization.ReportCard");
Constructor<?> constructor = cls.getConstructor();
Object o = constructor.newInstance();
```

### Relation to Deserialization

Deserialization internally uses the class name found in the stream plus the runtime class loader — conceptually the same mechanism as `Class.forName(fqcn)`. If the class isn't on the runtime classpath, it fails the same way.

### Common Interview Errors to Avoid

- Compile-time classpath ≠ runtime classpath.
- "Class compiled" ≠ "class available at runtime" (the class could be missing from the deployed artifact).
- A serialized object ≠ executable code — it's data describing an object, requiring the class definition separately.

**One-line interview answer:** *"Deserialization requires the class to be present on the runtime classpath; the JVM loads it using the fully qualified class name, similar to `Class.forName()`."*

------------------------------------------------------------------------

## Reflection Use Case 3 — Dependency Injection (Spring)

### Engineering Problem

Sometimes you want exactly one instance of a class to exist for the whole application, with every thread sharing it — and you want the objects that depend on each other wired together without every class hand-writing `new SomeDependency()` everywhere it's needed, which would hardcode the dependency graph into every constructor.

### Definition

A **Spring Bean** is an object whose entire lifecycle — creation, dependency injection, scope, destruction — is managed by the Spring container, not by your own code calling `new`.

### Spring Singleton ≠ JVM Singleton

- Spring singleton → **one instance per Spring container**.
- Multiple containers → multiple instances are possible; "singleton" here is scoped to the container, not to the JVM process.

**Interview one-liner:** *"In Spring, a singleton bean is a container-managed object where only one instance exists per application context and is shared across all threads."*

```java
@Component
class UserService { }
```

`@Component` marks a class as a Spring bean candidate, so Spring can instantiate and manage its object lifecycle.

### Autowiring

**Autowiring** is Spring's mechanism for automatically resolving and injecting bean dependencies at runtime. If a bean `DBAccessor` depends on another bean `Logger`, Spring — using the application context — locates a suitable `Logger` bean and injects it into `DBAccessor` (typically via constructor injection, or alternatively field/setter injection).

The wiring decision is made based on **type first**; if multiple candidates exist, qualifiers or bean names disambiguate. This removes manual object creation (`new`), keeps classes loosely coupled, and lets Spring control object relationships and lifecycle consistently across the application.

### Behind the Scenes — Reflection + Graph Resolution

Spring enables autowiring by building a **dependency graph** of bean definitions and resolving it at runtime:

- It uses **reflection** to inspect constructors, fields, and methods (e.g. annotated with `@Autowired`).
- It builds a **directed graph** where nodes are beans and edges represent dependencies.
- During context initialization, Spring traverses this graph, determines a valid instantiation order via **topological sort**, creates beans accordingly, and injects dependencies via reflection.

Reflection is used **for inspection and injection**; the graph-based resolution is what ensures correct ordering, detects missing dependencies, and identifies circular dependencies (with specific handling rules).

### Engineering Insight

This splits cleanly into two separate responsibilities: reflection answers "what does this bean need, and how do I set it?", while the dependency graph and topological sort answer "in what order can these beans even be constructed?" Conflating the two would make Spring's core both harder to reason about and harder to test — a clean instance of the same Single-Responsibility reasoning that shows up everywhere else in this course.

------------------------------------------------------------------------

## Interview Q&A

### What problem does reflection actually solve?

It lets code inspect and act on classes, methods, and fields it didn't know about at compile time — needed whenever a class name, method, or field is only knowable at runtime (plugins, serializers, DI containers).

### What's the difference between `getDeclaredFields()`/`getDeclaredMethods()` and `getFields()`/`getMethods()`?

The `getDeclared*` variants return only members declared directly in that class, at any access level, excluding inherited ones. The non-declared variants (`getMethods()`, `getFields()`) return all **public** members, including ones inherited from superclasses and interfaces.

### Why doesn't `getSuperclass()` return interfaces?

Because Java only allows a single superclass — `getSuperclass()` walks that one chain. Interfaces are a separate relationship, retrieved via `cls.getInterfaces()`.

### Why does `getDeclaredMethod()` find a private method, but `invoke()` on it throw `IllegalAccessException`?

Locating a member via reflection is independent of Java's language-level access control — reflection can *see* a private method, but invoking it still respects `private` unless access checks are explicitly disabled with `setAccessible(true)`.

### What does `setAccessible(true)` actually do, and why is it dangerous?

It disables Java's language-level access checks at runtime, allowing invocation of private methods/fields/constructors. It's dangerous because it breaks encapsulation, can expose sensitive data, can violate class invariants, and can throw `SecurityException` in environments with a `SecurityManager` or reflection restrictions.

### Why do primitive class literals like `int.class` exist?

Because `int` isn't a class, but reflective APIs like `getDeclaredMethod()` only accept `Class<?>` arguments to describe parameter types — Java provides special JVM-backed `Class` objects for primitives so a primitive-typed parameter can still be described reflectively.

### Why does `printArray(int[])` behave differently from `printArray(String[])` when `printArray` is declared as `<T> void printArray(T... a)`?

Generics require reference-type elements. `int[]` is itself a reference type, so Java infers `T = int[]` and the whole array collapses into a single varargs element. `String[]`'s elements are already reference types, so it behaves as expected — one varargs element per array entry.

### What role does reflection play in serialization libraries like Jackson?

At runtime, a generic serializer doesn't know a given object's fields, getters/setters, or annotations in advance — reflection lets it inspect the class structure and read/write fields dynamically, which is exactly the "unknown until runtime" problem reflection exists to solve.

### Why is compile-time classpath insufficient for deserialization?

Because deserialization happens at runtime, using the JVM's runtime classpath to locate and load the class by its fully qualified name from the serialized stream — a class being compiled successfully says nothing about whether it's present in the deployed runtime environment.

### What does `Class.forName()` do, and when would you use it?

It loads a class at runtime given its fully qualified class name, triggering class loading and static initialization — used whenever the class to instantiate is only known at runtime, such as in frameworks, serializers, and plugin systems.

### What's the difference between a Spring singleton and a JVM (classic) singleton?

A Spring singleton is scoped to one instance **per Spring application context** — multiple containers in the same JVM can each hold their own instance. A classic JVM singleton is enforced at the class level and is one instance per JVM regardless of any container.

### How does Spring resolve which bean to inject when autowiring by type?

Type is checked first; if multiple beans of a matching type exist, qualifiers or explicit bean names are used to disambiguate the choice.

### How does Spring use reflection and graph algorithms together for dependency injection?

Reflection inspects constructors, fields, and annotated members (e.g. `@Autowired`) to discover what a bean needs. Separately, Spring builds a directed dependency graph of beans and uses a topological sort to determine a valid instantiation order, detect missing dependencies, and catch circular dependencies — reflection handles the "what," the graph algorithm handles the "in what order."

------------------------------------------------------------------------

❌ If reflection can locate a private method, it can call it too.

✔ Locating and invoking are separate checks — Java still enforces access control on `invoke()` unless you explicitly call `setAccessible(true)`.

------------------------------------------------------------------------

❌ Autoboxing for varargs/reflection calls happens at runtime, right before the method executes.

✔ Autoboxing happens at **compile time** — by the time the program runs, primitives passed to an `Object...`-style parameter are already boxed; runtime only ever sees objects, partly due to type erasure.

------------------------------------------------------------------------

❌ A generic varargs method like `<T> void f(T... a)` treats an `int[]` argument the same way it treats a `String[]` argument.

✔ `int[]` is itself inferred as `T`, collapsing the whole array into one element — because generics require the *elements*, not just the container, to be reference types. `String[]`'s elements already are reference types, so it behaves as expected.

------------------------------------------------------------------------

❌ If a class compiled successfully, deserialization involving it will always work at runtime.

✔ Compile-time classpath and runtime classpath are different things — a class missing from the runtime classpath causes `ClassNotFoundException` during deserialization regardless of whether it compiled fine originally.

------------------------------------------------------------------------

❌ A Spring singleton bean means there's exactly one instance of that class in the whole JVM.

✔ It means one instance **per Spring application context** — multiple containers in the same JVM can each hold a separate instance.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
Reflection            → inspect/act on types unknown at compile time
Class<T>               → every object's own metadata, reachable via getClass()

getDeclared*()          → this class only, any access level, no inheritance
get*() (no "Declared")  → public only, including inherited members

getDeclaredMethod finds → private methods
invoke() still enforces → access control, unless setAccessible(true)

setAccessible(true)    → disables access checks; breaks encapsulation;
                          framework territory, not business logic

int.class               → primitive class literal, needed because int
                          isn't itself a Class

Serialization           → object → transferable format (JSON/bytes),
                          powered by reflection to read structure dynamically
Deserialization         → needs the class on the RUNTIME classpath,
                          not just compiled successfully once

Spring Bean              → lifecycle owned by the container, not your code
Spring singleton         → one instance per container, not per JVM
Autowiring               → reflection discovers dependencies;
                            a dependency graph + topological sort
                            decides instantiation order
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain what problem reflection solves and why it belongs at framework boundaries, not in business logic
- [x] Explain the difference between `getDeclared*()` and non-declared reflective lookups
- [x] Explain why `getDeclaredMethod()` can find a private method but `invoke()` still needs `setAccessible(true)`
- [x] Explain why `setAccessible(true)` is dangerous, and when it throws `SecurityException`
- [x] Explain why primitive class literals like `int.class` exist
- [x] Explain why reflection is central to how serialization libraries like Jackson work
- [x] List at least five things a senior engineer would guard against in a hand-rolled reflective serializer
- [x] Explain the difference between compile-time and runtime classpath, and why it matters for deserialization
- [x] Explain the difference between a Spring singleton and a JVM singleton
- [x] Explain how Spring combines reflection with a dependency graph to perform autowiring
