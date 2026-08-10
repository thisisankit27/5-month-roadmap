# Spring IoC: Dependency Injection, Containers, Beans & Autowiring

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not "here's the `@Autowired` annotation." The whole chapter answers one question: **who decides which concrete object a class gets to work with — the class itself, or something external to it?** Every mechanism here (constructor injection, `@Qualifier`, the IoC container) is a different answer to that one question, and the answer determines whether your code is testable, or hard-wired to concrete classes you can never swap out.

## Crisp Definition

**Inversion of Control means a class no longer decides how its dependencies are created — an external container creates them and hands them in. Dependency Injection is the specific technique Spring uses to do that handing-in: constructor, setter, or field.**

------------------------------------------------------------------------

## Dependency Injection: Maven's Meaning vs. Spring's Meaning

The phrase "dependency" means something different in each tool:

```text
Maven's "dependency"   → a dependency on a PACKAGE   (compile/build-time concern)
Spring's "dependency"  → a dependency on an OBJECT    (runtime concern)
```

```java
A obj = new A(new B(), new C());
```

Here, `B` and `C` are dependencies **of** `A` — this is Spring's sense of the word. Writing `new` yourself means *your code* decides exactly which concrete objects `A` gets. Spring exists to let you write this without ever calling `new` for `B` or `C` yourself.

------------------------------------------------------------------------

## What's Actually Wrong With `new`?

### Engineering Problem

```java
class OrderService {
    private PaymentGateway gateway = new PaymentGateway();

    void placeOrder() {
        gateway.pay(100);
    }
}
```

This isn't a style complaint — it's a concrete set of problems:

1. `OrderService` is **locked** to `PaymentGateway` — no other implementation can ever be substituted.
2. You **cannot replace** `PaymentGateway` without editing `OrderService`'s source.
3. **Testing becomes painful.**

### Why Testing Breaks

You want to test: *does `placeOrder()` call payment?* — **not** *does it actually charge real money?* But `new PaymentGateway()` connects to a real payment system: a real network call, real money deducted. The test becomes slow, unsafe, or outright impossible to run in CI.

### Definition — Mocking

**Mocking** means using a fake object instead of the real one during testing — fake behavior, no real DB, no real payment, no real network.

### Why `new` Blocks Mocking

Because you hardcoded the dependency. `new PaymentGateway()` says *"ONLY use this exact concrete class"* — you left no room to swap it for a fake at test time.

------------------------------------------------------------------------

## The Fix — Dependency Injection (Manual, Before Spring)

### Step 1: Remove `new`

```java
class OrderService {
    private PaymentGateway gateway;

    OrderService(PaymentGateway gateway) {
        this.gateway = gateway;
    }

    void placeOrder() {
        gateway.pay(100);
    }
}
```

Now `OrderService` says: *"I don't care HOW payment happens. Just give me something that can pay."*

### Testing Becomes Easy

```java
class FakePaymentGateway extends PaymentGateway {
    void pay(int amount) {
        System.out.println("Fake payment of " + amount);
    }
}

PaymentGateway fake = new FakePaymentGateway();
OrderService service = new OrderService(fake);
service.placeOrder();
```

No real payment. Fast. Safe. Controlled behavior — this **is** mocking.

### Where Spring Comes In

Doing this manually everywhere doesn't scale. Spring automates it: creates objects, injects dependencies, and lets you swap real → mock easily in tests.

```java
@Service
class OrderService {
    private final PaymentGateway gateway;

    OrderService(PaymentGateway gateway) {
        this.gateway = gateway;
    }
}
```

Spring creates `PaymentGateway`, injects it into `OrderService`, and in tests injects a mock instead. **You never write `new`.**

### Mocking in Real Life — JUnit + Mockito

```java
PaymentGateway mockGateway = mock(PaymentGateway.class);
OrderService service = new OrderService(mockGateway);
service.placeOrder();

verify(mockGateway).pay(100);
```

This checks *"did my code behave correctly?"* — not *"did payment actually happen?"*

### The Key Mental Switch

```text
Using new                → "I decide what object to use"
Dependency Injection      → "I receive what object to use"
```

That's the whole thing.

**One-line interview explanation:** *"Using `new` tightly couples classes and makes mocking difficult; dependency injection allows replacing real objects with mocks during testing."*

------------------------------------------------------------------------

## Inversion of Control (IoC)

### Engineering Problem

```java
private PaymentGateway gateway = new PaymentGateway();
```

The `new` for this dependency lives inside your class — if that component has an issue (fails to construct, needs config you don't have), **your class won't even compile or run.** Object-creation failures are baked into the class that shouldn't need to care about them.

### Definition

Move to constructor injection instead:

```java
private final PaymentGateway gateway;

OrderService(PaymentGateway gateway) {
    this.gateway = gateway;
}
```

Now the control of object creation sits at the **client (caller) side** — every failure or exception from constructing the dependency is handled there, not inside `OrderService`. This is called **Inversion of Control**: control over *how* and *when* a dependency is created is inverted away from the class that uses it. Spring uses IoC extensively — a Spring app doesn't call `new` for its own beans; the framework does.

### Engineering Insight

The name is literal, not clever branding: control that would normally sit inside the dependent class (deciding what to construct, and dealing with construction failures) is *inverted* — pushed outward to the caller, and ultimately to the framework. Dependency Injection is simply the mechanism Spring uses to perform that inversion.

------------------------------------------------------------------------

## IoC Container & Beans

### Definition — IoC Container

The **IoC Container** is the Spring runtime that creates objects, manages their lifecycle, and injects dependencies. `ApplicationContext` is the most commonly used IoC container in Spring.

### Definition — Bean

A **Bean** is a Java object managed by the Spring IoC container. Spring controls its creation, its wiring (dependency injection), and its lifecycle (init, destroy). Typical examples: a database accessor, a network/connection pool, service classes, configuration objects.

### Scope & Lifecycle

The container holds bean instances with a defined **scope**:

- **Default scope: `singleton`** — one instance per `ApplicationContext`.
- Other scopes exist (`prototype`, `request`, `session`, ...).

Spring manages when the instance is created, when it's destroyed, and how long it lives.

### Interdependent Beans

Beans can depend on other beans, and Spring resolves those dependencies automatically:

```text
OrderService → PaymentService → Logger
```

Spring builds a dependency graph, instantiates beans in the correct order, and injects required dependencies — the same graph-resolution mechanics used elsewhere in Spring's autowiring.

**Interview answer:** *"The Spring IoC container, typically `ApplicationContext`, manages beans — Java objects whose lifecycle and dependencies are controlled by Spring. These beans are usually singleton-scoped and can depend on each other, with Spring resolving and injecting dependencies automatically."*

------------------------------------------------------------------------

## Spring Boot — Convention Over Configuration

### Philosophy

Reduce manual setup, provide sensible defaults, and let the developer override only when needed: *"Spring Boot auto-configures common infrastructure based on classpath."*

### What Auto-Configuration Does

Spring Boot automatically creates beans, based on:

- classes present on the classpath,
- existing user-defined beans, and
- properties.

It uses conditional annotations like `@ConditionalOnClass`, `@ConditionalOnMissingBean`, and `@ConditionalOnProperty`.

**Key rule:** Boot configures only if you **haven't already** configured it — it will **not** override your custom bean.

### Starters

```xml
<artifactId>spring-boot-starter-web</artifactId>
```

A **starter** is a curated dependency bundle — it pulls in required libraries, auto-config support, and sensible defaults, all at once.

### How Boot Decides What to Configure

Classpath-driven configuration:

- Web classes present → configure `DispatcherServlet`.
- JDBC driver present → configure a `DataSource`.
- Jackson present → configure an `ObjectMapper`.

### Important Clarification

Boot is not "intelligent guessing." It checks conditions, applies configuration only if those conditions match, and fails if a requirement is missing.

**Interview one-liner:** *"Spring Boot uses conditional auto-configuration to create default beans based on the classpath, reducing manual configuration while allowing full override."*

------------------------------------------------------------------------

## Making Objects Discoverable — `@Component` and the Bootstrap Annotations

### Engineering Problem

If Spring needs to know which classes should become beans, a naming convention (`<ClassName>Bean`?) is fragile — `Bean`, `bean`, `Been`, `BEAN` all invite typos and inconsistency across a codebase. Something more reliable than string-matching a class name is needed.

### Solution — `@Component`

`@Component` marks a class as a Spring bean candidate, so Spring can instantiate and manage its object lifecycle.

### `ApplicationContext` = the Name for the IoC Container

Just terminology: when you see `ApplicationContext`, that *is* the IoC container instance for your app.

### `@SpringBootApplication`

```java
@SpringBootConfiguration
@EnableAutoConfiguration
@ComponentScan(
    excludeFilters = {
        @Filter(type = FilterType.CUSTOM, classes = {TypeExcludeFilter.class}),
        @Filter(type = FilterType.CUSTOM, classes = {AutoConfigurationExcludeFilter.class})
    }
)
public @interface SpringBootApplication { ... }
```

| Annotation | Responsibility |
|---|---|
| `@SpringBootConfiguration` | A specialized `@Configuration` — this class defines Spring bean configuration for the app |
| `@EnableAutoConfiguration` | Enables Spring Boot's auto-configuration mechanism, based on classpath and existing beans |
| `@ComponentScan` | Scans the package (and sub-packages) for Spring components (`@Component`, `@Service`, ...) and registers them as beans |

**Ultra-short mental model:** `@SpringBootApplication` = **Config + Auto-config + Component scan**, in one annotation.

### Naming a Bean Explicitly

```java
@Component("thisWillBeTheNameOfThisBean")
```

### Two Gotchas Worth Remembering

**1. `@Component` on an interface or abstract class does nothing.** It doesn't throw an error, but it has no effect — and any class implementing/extending that interface/abstract class (or any superclass) does **not** inherit the annotation. Each concrete class needs its own `@Component`.

**2. `SpringApplication.run(...)` is what actually performs bean management, injection, and autowiring — a manually `new`'d object bypasses all of it:**

```java
ApplicationContext ctx = SpringApplication.run(MyFirstSpringProjectApplication.class, args);
DatabaseAccessor databaseAccessor = (DatabaseAccessor) ctx.getBean("databaseAccessor");
databaseAccessor.talkToDB();   // works — Spring wired the Logger in

DatabaseAccessor dba = new DatabaseAccessor();
dba.talkToDB();                // ✘ NPE — Spring never touched this instance,
                                //   its Logger field was never set
```

Autowiring only happens for objects the **container** created. Instantiate the class yourself, and you've opted out of every wiring guarantee Spring would otherwise provide.

------------------------------------------------------------------------

## Autowiring

### Definition

**Autowiring** is Spring's mechanism for automatically resolving and injecting bean dependencies at runtime. If a bean `DBAccessor` depends on another bean `Logger`, Spring — using the application context — locates a suitable `Logger` bean and injects it into `DBAccessor`, via constructor, field, or setter injection.

For a dependency to be found, it must itself be a bean — otherwise Spring has nothing in the container to inject.

------------------------------------------------------------------------

## Field Autowiring

```java
@Component
public class Logger {
    public void log() {
        System.out.println("#######--Logging--#######");
    }
}

@Component
public class DatabaseAccessor {
    @Autowired   // field autowiring
    private Logger logger;

    public void talkToDB() {
        System.out.println("#######--Talkin--To--Database--#######");
        logger.log();
    }
}
```

```java
@SpringBootApplication
public class MyFirstSpringProjectApplication {
    public static void main(String[] args) throws ClassNotFoundException {
        ApplicationContext ctx = SpringApplication.run(MyFirstSpringProjectApplication.class, args);
        DatabaseAccessor databaseAccessor = (DatabaseAccessor) ctx.getBean("databaseAccessor");
        databaseAccessor.talkToDB();
    }
}
// Output:
// #######--Talkin--To--Database--#######
// #######--Logging--#######
```

### The Drawback

**Field autowiring is a ticking time bomb for `NullPointerException`.** When Spring creates the object, everything works fine — but if a developer or test manually instantiates the class with `new` and forgets to set the hidden dependency, calling a method that uses it throws an NPE. Nothing in the class signature warns you the dependency exists.

### Core Design Problem

Field injection:

- hides required dependencies (nothing visible from outside the class body),
- breaks immutability (the field can't be `final`),
- makes manual testing harder (you need reflection or a framework to set it), and
- violates the *explicit dependency* principle.

**Interview one-liner:** *"Field injection hides required dependencies and can cause runtime NullPointerExceptions when objects are instantiated outside the Spring container."*

------------------------------------------------------------------------

## Ambiguous Autowiring — `@Qualifier` and Named Autowiring

### Engineering Problem

When a bean's type is an **interface** with multiple implementations, Spring has no way to know which one to inject by type alone:

```java
public interface Game {
    void play();
}

@Component
public class Chess implements Game {
    public void play() { System.out.println("#####--Playing--Chess--#####"); }
}

@Component
public class Ludo implements Game {
    public void play() { System.out.println("#####--Playing--Ludo--#####"); }
}

@Component
public class GameManager {
    @Autowired
    private Game game;

    public void manage() {
        game.play();
    }
}
```

```text
Field game in com.example.demo.GameManager required a single bean, but 2 were found:
- chess
- ludo

Action: Consider marking one of the beans as @Primary, updating the consumer to
accept multiple beans, or using @Qualifier to identify the bean that should be consumed
```

### Fix — `@Qualifier`

```java
@Component
public class GameManager {
    @Autowired
    @Qualifier("ludo")
    private Game game;

    public void manage() {
        game.play();
    }
}
// Output: #####--Playing--Ludo--#####
```

### Named Autowiring — the Implicit Alternative

The same disambiguation can happen **without** `@Qualifier`, purely from the field's name:

```java
@Component
public class GameManager {
    @Autowired
    private Game chess;   // Spring uses reflection to read the field name and matches it to a bean

    public void manage() {
        chess.play();
    }
}
// Output: #####--Playing--Chess--#####
```

This isn't magic — Spring uses reflection to inspect the field name, and falls back to matching it against bean names when the type alone is ambiguous.

### Does `@Qualifier` Kill Runtime Polymorphism?

**No.** `@Qualifier(...)` is only honored by the specific client (`GameManager`, here) that declares it. A different client can hold its own distinct `Game game` field with no qualifier, or a different qualifier entirely — each caller's wiring choice is independent, so polymorphism at the `Game` interface level is untouched; only *this particular injection point's* choice is pinned.

------------------------------------------------------------------------

## Setter Autowiring

```java
@Component
public class GameManager {
    private Game game;

    @Autowired
    public void setGame(@Qualifier("chess") Game game) {
        this.game = game;
    }

    public void manage() {
        game.play();
    }
}
```

### When Setter Injection Is Genuinely Useful

**1. Optional dependencies** — the primary use case:

```java
@Autowired(required = false)
public void setLogger(Logger logger) {
    this.logger = logger;
}
```

If a `Logger` bean exists, it's injected; if not, there's no failure — the bean is still created. **Constructor injection cannot support optional dependencies this cleanly.**

**2. Late / reconfigurable dependencies** — setter injection allows changing a dependency after object creation, or replacing a bean in advanced scenarios. Less common, but valid.

### Cons of Setter Injection

**Mutability** — `gameManager.setLogger(newLogger)` means the dependency can change after construction; the object is not immutable, and its state becomes harder to reason about. This violates the "fully initialized after construction" principle.

**Potential race conditions (nuance)** — in singleton beans (the default scope), Spring creates the bean single-threaded during startup; multiple threads may access it afterward. If the setter is public and something mutates the dependency at runtime, one thread may observe the old reference while another observes the new one — unpredictable behavior. **However:** Spring itself injects dependencies before the bean is exposed to the application, so this risk only materializes if *you* mutate the bean later.

**Hidden required-dependency risk** — if a setter-injected dependency is optional (or the setter is never called), the object may end up partially initialized. Constructor injection prevents this by construction.

**Interview one-liner:** *"Setter injection is useful for optional dependencies or when dependencies may change after object creation, but constructor injection is preferred for mandatory dependencies."*

------------------------------------------------------------------------

## Constructor Autowiring

```java
@Component
public class DatabaseAccessor {
    private final Logger logger;

    @Autowired   // constructor autowiring
    DatabaseAccessor(Logger l) {
        this.logger = l;
    }

    public void talkToDB() {
        System.out.println("#######--Talkin--To--Database--#######");
        logger.log();
    }
}
```

Spring scans `@Component` classes, checks whether they have a constructor annotated `@Autowired` (or a single constructor at all), and injects the dependency there — this is what prevents the field-autowiring NPE risk entirely: the object simply **cannot exist** without its `Logger`.

### With a Polymorphic Dependency

```java
@Component
public class GameManager {
    private final Game game;

    @Autowired
    GameManager(@Qualifier("chess") Game g) {
        this.game = g;
    }

    public void manage() {
        game.play();
    }
}
```

### Why This Is Better Than Setter Injection

- **Object is fully initialized at creation** — no partially constructed state is possible.
- **Dependencies are explicit** — everything required is visible just by looking at the constructor signature.
- **Immutability possible** — fields can be `final`.
- **No mutation after construction** — setter injection allows late modification; constructor injection doesn't.

### When Setter Injection Is Still Acceptable

- Truly optional configuration.
- Rare circular-dependency scenarios.
- Legacy code.

But modern Spring practice defaults to **constructor injection**.

### Senior-Level Mental Model

| Constructor Injection | Setter Injection |
|---|---|
| Object is complete, immutable, thread-safe by design | Object is configurable but potentially unstable |

**Senior-level one-liner:** *"Constructor injection makes dependencies explicit and immutable; optional dependencies can be modeled using `Optional<T>` without resorting to setter injection."*

### `Optional<T>` in Constructor Autowiring

Combining a mandatory (qualified) dependency with a genuinely optional one, without falling back to setter injection at all:

```java
@Component
public class GameManager {
    private final Game game;
    private final Logger logger;

    @Autowired
    GameManager(@Qualifier("chess") Game game, Optional<Logger> logger) {
        this.game = game;
        this.logger = logger.orElse(null);
    }

    public void manage() {
        game.play();
        if (logger != null) {
            logger.log();
        }
    }
}
```

```java
ApplicationContext ctx = SpringApplication.run(MyFirstSpringProjectApplication.class, args);
GameManager gameManager = (GameManager) ctx.getBean("gameManager");
gameManager.manage();

GameManager gm = new GameManager(new Ludo(), Optional.empty());
gm.manage();

// Output:
// #####--Playing--Chess--#####
// #####--Playing--Ludo--#####
```

### Engineering Insight

Constructor injection is the same reasoning as [`final` and immutability](day-1-oop-fundamentals.md) applied to object wiring: a `final` field set only in the constructor can't drift after construction, which is exactly what makes a bean safe to share across threads without synchronization. Setter injection reopens that door deliberately — acceptable only when the dependency is genuinely optional or reconfigurable, never as the default.

------------------------------------------------------------------------

## Interview Q&A

### How does "dependency" differ in meaning between Maven and Spring?

Maven's dependency is a dependency on a package — a compile/build-time concern. Spring's dependency is a dependency on an object — a runtime concern, resolved and injected by the IoC container.

### What's concretely wrong with writing `new PaymentGateway()` inside `OrderService`?

It locks `OrderService` to one concrete implementation, makes that implementation impossible to swap, and blocks mocking in tests — since `new` always constructs the real object, tests using it would hit a real network call and real side effects.

### What is mocking, and why does `new` block it?

Mocking is substituting a fake object for the real one during a test. `new` blocks it because it hardcodes exactly which concrete class gets constructed — there's no injection point left for a caller to substitute a fake.

### What is Inversion of Control?

Moving the responsibility for creating and configuring a dependency out of the class that uses it, and into an external caller or framework — so failures in constructing that dependency are handled at the client/framework side, not baked into the dependent class.

### What is a Spring Bean, and what does the IoC container manage about it?

A Bean is a Java object whose creation, dependency wiring, and lifecycle (init/destroy) are controlled by the Spring IoC container (`ApplicationContext`), rather than by application code calling `new`.

### What's the default Spring bean scope, and what does it mean?

Singleton — one instance per `ApplicationContext`. Note this is scoped to the container, not the JVM: multiple `ApplicationContext`s can each hold their own separate instance.

### What does Spring Boot's "convention over configuration" actually check before creating a bean?

Conditions — via annotations like `@ConditionalOnClass`, `@ConditionalOnMissingBean`, `@ConditionalOnProperty` — based on what's on the classpath, what beans already exist, and configured properties. It's condition-checking, not "intelligent guessing," and it never overrides a bean you've already defined yourself.

### Why does `@Component` on an interface have no effect?

Because Spring instantiates concrete classes, and annotations are not inherited by implementing/extending classes — each concrete class needs its own `@Component` (or equivalent stereotype annotation).

### If you call `new DatabaseAccessor()` yourself instead of getting it from `ApplicationContext`, what happens to its `@Autowired` field, and why?

It stays unset, because autowiring only happens for objects the Spring container itself creates during `SpringApplication.run(...)`. A manually constructed instance never goes through that wiring process, so calling a method relying on the field throws `NullPointerException`.

### What's the main risk with field autowiring specifically?

If the object is ever manually instantiated outside the Spring container (in a test, or by a developer forgetting the framework manages it), the field is never set — and using it throws an NPE with no compile-time warning, because the dependency requirement is invisible from the constructor.

### If two beans implement the same interface, how does Spring know which to inject?

It doesn't, by type alone — you either disambiguate explicitly with `@Qualifier("beanName")`, or rely on Named Autowiring, where Spring uses reflection to match the field/parameter name itself against a bean name.

### Does using `@Qualifier` on one injection point break polymorphism elsewhere?

No — `@Qualifier` is only honored at the specific injection point that declares it. Other clients of the same interface can hold entirely different, unqualified or differently-qualified references; each wiring decision is local to its own call site.

### When is setter injection actually the right choice over constructor injection?

For genuinely optional dependencies (`@Autowired(required = false)`), for dependencies that may legitimately change after construction, for some circular-dependency workarounds, or in legacy code — not as a general default.

### Why is constructor injection considered the modern Spring default?

It guarantees the object is fully initialized at creation with no partially-constructed state, makes every dependency explicit in the constructor signature, allows `final` fields (immutability), and forbids any mutation after construction — all of which setter injection allows to happen.

### How can a constructor-injected bean still support one optional dependency without falling back to setter injection?

By taking `Optional<T>` as a constructor parameter — Spring injects `Optional.empty()` if no matching bean exists, and the constructor resolves it explicitly (e.g. `logger.orElse(null)`), keeping the class immutable and its optionality visible in the signature.

------------------------------------------------------------------------

❌ Dependency Injection just means "Spring creates my objects for me" — it's a convenience feature.

✔ It's specifically what makes classes swappable and testable — the actual engineering payoff is decoupling *what* a class needs from *which concrete implementation* satisfies it, which is what makes mocking possible in the first place.

------------------------------------------------------------------------

❌ A Spring singleton bean means one instance exists in the whole JVM.

✔ It means one instance per `ApplicationContext` (container) — multiple containers in the same JVM can each hold their own instance.

------------------------------------------------------------------------

❌ Putting `@Component` on an interface makes every implementation of it a bean automatically.

✔ `@Component` is not inherited — every concrete implementing class needs its own `@Component` (or equivalent) annotation; the one on the interface has no effect at all.

------------------------------------------------------------------------

❌ If a class is annotated `@Component`, calling `new` on it manually still gets you a fully-wired object.

✔ Autowiring only happens for objects the Spring container itself constructs during `SpringApplication.run(...)`. A manually `new`'d instance never goes through that process — its `@Autowired` fields stay unset.

------------------------------------------------------------------------

❌ `@Qualifier` on one field means every use of that interface across the app now resolves to that specific bean.

✔ `@Qualifier` only applies to the specific injection point that declares it — other clients of the same interface are free to wire a different implementation, or none at all.

------------------------------------------------------------------------

❌ Setter injection is strictly worse than constructor injection and should never be used.

✔ It's the correct tool specifically for optional or late-changing dependencies (`@Autowired(required = false)`) — the objection is to using it as the *default* for mandatory dependencies, not to its existence.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
Maven "dependency"    → a package (compile/build-time)
Spring "dependency"    → an object (runtime)

new                    → "I decide what object to use"  (tight coupling,
                          blocks mocking)
Dependency Injection    → "I receive what object to use" (swappable, testable)

Inversion of Control    → object-creation responsibility moves from the
                           dependent class to an external caller/framework

IoC Container (ApplicationContext) → creates beans, injects dependencies,
                                       manages lifecycle
Bean scope (default)                → singleton, one per ApplicationContext

@Component               → makes a class a bean candidate; NOT inherited,
                            has no effect on interfaces/abstract classes
SpringApplication.run()  → the only path through which autowiring happens;
                            manual `new` bypasses it entirely

Field injection    → hides deps, breaks immutability, NPE risk if `new`'d manually
Setter injection    → mutable, but the right fit for optional/late-bound deps
Constructor injection → explicit, immutable, no NPE risk — the modern default

Multiple beans, same interface → disambiguate with @Qualifier or
                                   Named Autowiring (field-name match)
Optional<T> in a constructor    → models an optional dependency WITHOUT
                                   giving up constructor injection
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain why constructing dependencies with `new` blocks mocking and unit testing
- [x] Explain Inversion of Control in your own words, using the "control moves to the caller" framing
- [x] Explain what an IoC container and a Spring Bean are, and the default bean scope
- [x] Explain Spring Boot's convention-over-configuration philosophy and why it never overrides your own beans
- [x] Explain why `@Component` on an interface has no effect
- [x] Explain why manually calling `new` on a `@Component`-annotated class produces an unwired object
- [x] Explain the difference between field, setter, and constructor autowiring, and rank them by safety
- [x] Explain how `@Qualifier` and Named Autowiring resolve ambiguous bean injection
- [x] Explain why constructor injection is the modern default, and when setter injection is still the right call
- [x] Explain how `Optional<T>` lets constructor injection model an optional dependency
