# Spring: Circular Beans, Config Beans, Profiles & Application Events

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not "here's another annotation." Every mechanism here — cyclic-dependency detection, `@Bean`/`@Configuration`, property resolution priority, profiles, application events — exists to answer the same underlying question the IoC chapter raised: **who is responsible for creating and wiring something, and what happens when that responsibility can't be resolved cleanly?** Circular beans are what happens when it *can't* be resolved. Config beans and profiles are about wiring things Spring can't discover on its own. Events are about decoupling *who reacts* from *who acted* entirely.

## Crisp Definition

**Spring resolves what to build and how to configure it from three places: component scanning (what it can discover), explicit configuration (what you register by hand), and externalized properties (what varies by environment) — and it decouples cross-cutting reactions from the code that triggers them via an internal publish/subscribe event system.**

------------------------------------------------------------------------

## Circular Dependency Between Beans

### Engineering Problem

```java
@Component
public class Customer {
    @Autowired
    private Cart cart;
}

@Component
public class Cart {
    @Autowired
    private Customer customer;
}
```

Both are singleton beans (default scope), field-injected, and **mutually dependent** — `Customer` needs `Cart` to exist, and `Cart` needs `Customer` to exist.

### What Happens at Startup

Spring tries to create beans during context initialization:

1. Create `Customer`.
2. `Customer` needs `Cart`.
3. Create `Cart`.
4. `Cart` needs `Customer`.
5. But `Customer` is still being created — it doesn't exist yet to hand over.

Now there's a cycle: neither bean can finish construction without the other already existing.

### The Error (Spring Boot 2.6+)

By default, circular references are disabled, and Spring reports:

```text
The dependencies of some of the beans in the application context form a cycle:

┌─────┐
| customer
↑     ↓
| cart
└─────┘

Action:

Relying upon circular references is discouraged and they are prohibited by default.
Update your application to remove the dependency cycle.
```

### Engineering Insight

This is the same "control of creation" question from [Spring IoC](day-6-ioc-di-spring.md), just pushed to its limit: if two beans each require the other to already exist before *they* can exist, there is no valid creation order at all. The right fix isn't a workaround (older Spring versions tolerated this via early bean references) — it's redesigning ownership so the dependency graph is actually acyclic: extract shared state into a third bean, use `@Lazy` to defer resolution, or — as the [event architecture](#event-based-architecture-the-observer-pattern-in-spring) section below shows — replace a direct dependency with a published event neither side needs a hard reference to.

------------------------------------------------------------------------

## Component Scanning — What Spring Finds, and What It Doesn't

### Engineering Problem

`@Component` only gets picked up by **component scanning**, and component scanning by default only looks in the same package (and sub-packages) as your `@SpringBootApplication` class. A third-party class you didn't write can't be annotated at all, and even your own `@Component`-annotated classes go undiscovered if they live in a package the scan never reaches.

### Case 1 — A Non-Annotated Class From a Third-Party Library

```java
// Third-party class — you cannot add annotations to it
public class SomeExtLibrary {
}

@Configuration
public class ExternalConfig {
    @Bean
    public SomeExtLibrary someExtLibrary() {
        return new SomeExtLibrary();   // you own the creational responsibility —
                                        // hence you can customize, log, etc.
    }
}
```

- `@Configuration` tells Spring: *"this class defines beans."*
- `@Bean` tells Spring: *"the return value of this method is a Spring Bean."*

**Common mistakes:**

- **Forgetting `@Configuration`** — Spring may never scan the class, so the bean is never created.
- **Thinking `@Bean` works anywhere** — it must be inside a `@Configuration` class (or at least a component class).
- **Wrong bean name confusion** — the default bean name is the method name; override it with `@Bean(name = "customLib")`.

**Interview one-liner:** *"For third-party classes where we cannot add annotations, we use `@Bean` inside a `@Configuration` class to manually register them in the Spring IoC container."*

### Case 2 — An `@Component`-Annotated Class in Another Package (Yours or a Library's)

```java
@Configuration
@ComponentScan(basePackages = "com.example.resources")   // scans everything in this package
public class ExternalConfig {
    @Bean
    public SomeExtLibrary someExtLibrary() {
        return new SomeExtLibrary();
    }

    // Alternative: manually select which single component to register,
    // instead of scanning the whole package
    // @Bean
    // public MongoDBConnector mongoDBConnector() {
    //     return new MongoDBConnector();
    // }
}
```

### Engineering Insight

`@Component` means "let Spring discover and construct this end to end." `@Bean` means "I own the construction — Spring only takes the finished object." That distinction is exactly why third-party classes always need `@Bean`: you can't retroactively give a class you don't own a `@Component` annotation, so you take over construction yourself and only hand Spring the result.

------------------------------------------------------------------------

## Environment Variables and Property Sources

### Engineering Problem

Secrets and environment-specific values (DB credentials, API keys, feature flags) shouldn't be hardcoded — and the *same* application needs to read different values depending on where it's running (local dev, CI, production), without a code change.

### `@Value` Injection — Full Example

```java
@SpringBootApplication
@PropertySource("classpath:extra.properties")   // adds src/.../extra.properties as a source
public class MyFirstSpringProjectApplication implements ApplicationRunner {

    @Value("${KEY}")                              // from IntelliJ Run/Debug Config
    private String envVar;

    @Value("${AnkitType}")                         // from src/main/resources/application.properties
    private String envVar2;

    @Value("${Duplicate}")                          // from Java Args, NOT application.properties
    private String envVar3;

    @Value("${SomeKey:defaultValueCanBeGivenToPreventCTE}")   // default if not found anywhere
    private String notPresentInEnv;

    @Value("${MongoDBKey}")                          // from extra.properties, via @PropertySource
    private String mongoDBSecret;

    public static void main(String[] args) throws ClassNotFoundException {
        SpringApplication.run(MyFirstSpringProjectApplication.class, args);
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        System.out.println(envVar + "|" + envVar2);
        System.out.println(envVar3);
        System.out.println(notPresentInEnv);
        System.out.println(mongoDBSecret);
    }
}
// Output:
// ankitisthebest|Human
// IntelliJVariable
// defaultValueCanBeGivenToPreventCTE
// ThisIsRandom12*(^OK
```

### Property Sources and Priority Order

Spring resolves properties from multiple sources:

- Java Args (VM options / `-D`)
- Environment Variables (OS / IntelliJ Run Config)
- `application.properties` / `application.yml`
- Custom files, added via `@PropertySource`

**Priority order (highest wins on a duplicate key):**

```text
Java Args (-D)
  > Environment Variables
  > application.properties / application.yml
  > @PropertySource (extra.properties, etc.)
```

| Variable | Source |
|---|---|
| `envVar` | IntelliJ Run Config |
| `envVar2` | `application.properties` |
| `envVar3` | Java Args (`-D`) — overrides everything else |
| `notPresentInEnv` | Default value used (`${key:default}` syntax) |
| `mongoDBSecret` | `extra.properties`, via `@PropertySource` |

### Default Value Handling

```java
@Value("${SomeKey:defaultValue}")
```

If `SomeKey` isn't found in any source, `defaultValue` is used instead — this is what prevents a missing property from failing context startup (a **Context Load Failure**) outright.

### `@Value` Without `@PropertySource` Doesn't Reach Custom Files

```java
// @Value("${exclusive.properties.DirectCheck}")   // ✘ does NOT work without @PropertySource
```

A property that only exists in a custom file is invisible to `@Value` unless that file was registered via `@PropertySource` first — Spring's default property sources don't include arbitrary files.

### `ApplicationRunner`

```java
public class MyFirstSpringProjectApplication implements ApplicationRunner {
    @Override
    public void run(ApplicationArguments args) throws Exception { ... }
}
```

`ApplicationRunner`'s `run()` executes **after** the Spring context is fully initialized — useful for debugging configs, initial logging, or general startup logic that needs every bean already wired.

**Interview one-liners:**

- *"Spring resolves properties from multiple sources with a defined priority, where JVM arguments override all."*
- *"`@Value` injects configuration values at startup from Spring's Environment abstraction."*
- *"We can avoid startup failures by providing default values using `${key:default}` syntax."*

------------------------------------------------------------------------

## Profile-Based Configuration

### Engineering Problem

Beta and production environments need different credentials and connection details for the same components — hardcoding either, or branching on environment inside application code, would couple business logic to deployment concerns.

### Naming Convention (Strict)

```text
application-{profile}.properties
```

Examples: `application-beta.properties`, `application-prod.properties`. Spring auto-detects files that follow this pattern exactly:

```text
application_beta.properties   ✘   (underscore — not detected)
application-beta.properties   ✔
```

### What Spring Does Internally

1. Read the active profile (`spring.profiles.active`).
2. Load `application.properties` **and** `application-{activeProfile}.properties`.
3. Merge them.
4. Profile-specific values **override** the defaults.

### Worked Example

```properties
# application-beta.properties
mongodb.userName=betaUser
mongodb.userPswd=betaPass
```

```properties
# application-prod.properties
mongodb.userName=prodUser
mongodb.userPswd=prodPass
```

```java
@Component
@ConfigurationProperties(prefix = "mongodb")   // binds every property under the "mongodb" prefix
public class MongoDBConnector {
    private String userName;
    private String userPswd;

    public String getUserName() { return userName; }
    public void setUserName(String userName) { this.userName = userName; }

    public String getUserPswd() { return userPswd; }
    public void setUserPswd(String userPswd) { this.userPswd = userPswd; }
}
```

```java
ApplicationContext ctx = SpringApplication.run(MyFirstSpringProjectApplication.class, args);
MongoDBConnector mongoDB = (MongoDBConnector) ctx.getBean("mongoDBConnector");
System.out.println(mongoDB.getUserName() + "|" + mongoDB.getUserPswd());
```

```text
Env: spring.profiles.active=prod   →   OUTPUT: prodUser|prodPass
Env: spring.profiles.active=beta   →   OUTPUT: betaUser|betaPass
```

No `@Autowired` field was written anywhere in `MongoDBConnector` — it still initialized correctly from the active profile.

### Why No `@Autowired` Was Needed

- `@Component` → the bean gets created.
- `@ConfigurationProperties` → values are injected **during** bean creation, automatically, as part of the binding phase.

### Why Setters Are Required

`@ConfigurationProperties` binding uses **setter injection** internally — without setters, the properties simply won't populate the fields. This also makes setters a natural place for preventive checks (e.g. sanitizing against SQL injection), since these values ultimately come from an external, potentially untrusted source (environment config).

### Mental Model

```text
ENV decides PROFILE
PROFILE decides FILE
FILE provides VALUES
VALUES bind to BEAN
```

------------------------------------------------------------------------

## The Journey of a Web Request (Preview)

This is a first pass, not the full picture — enough to place Spring MVC in context before going deeper later.

```text
NIC receives packet
      │
      ▼
Kernel interrupt → OS decides TCP or UDP
      │
      ▼
TCP: ordering + reassembly → complete packet
      │
      ▼
User space — caught by the servlet container as an HTTP request
      │
      ▼
Spring MVC (DispatcherServlet) — routes to the matching controller method
      │
      ▼
Deserialization — request body → Java objects
```

The part worth remembering for now: by the time your `@Controller` method runs, the framework has already handled packet reassembly, protocol parsing, and request routing — none of that is something application code touches directly.

------------------------------------------------------------------------

## Event-Based Architecture — the Observer Pattern in Spring

### Engineering Problem

Direct method calls between services (`ServiceA.doSomething()` calling `ServiceB.reactToIt()`) couple the caller to every reactor. If five different things need to happen when "the score updates," `ServiceA` ends up calling all five directly — and every time a new reaction is added, `ServiceA`'s code has to change.

### Foundation — the Observer Pattern

One object announces that something happened; many objects react to it independently. Example: a cricket match score updates, and many apps react (TV, mobile app, notifications) — none of them told the scoreboard they exist.

```text
Subject (Publisher) → notifies → Observers (Listeners)
```

### How Spring Implements This

| Role | Spring Type |
|---|---|
| Publisher | `ApplicationEventPublisher` |
| Listeners | `@EventListener`, or `implements ApplicationListener<T>` |
| Dispatcher | Hidden — Spring internally manages who listens to what |

**Important fact:** `ApplicationContext` **extends** `ApplicationEventPublisher` — Spring itself can publish events, and your application code can too, through the same mechanism.

### Built-In Spring Events

| Event | When |
|---|---|
| `ApplicationStartedEvent` | The app just started |
| `ContextClosedEvent` | The app is shutting down |

You never write the publisher for these — Spring publishes them for you.

### Reacting to Built-In Events — Full Working Example

```java
@SpringBootApplication
public class EventDemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(EventDemoApplication.class, args);
    }
}
```

```java
@Component
public class StartupListener {
    @EventListener
    public void onStartup(ApplicationStartedEvent event) {
        System.out.println("Application has started!");
        System.out.println("Initializing cache...");
        System.out.println("Connecting to external services...");
    }
}
```

```java
@Component
public class ShutdownListener {
    @EventListener
    public void onShutdown(ContextClosedEvent event) {
        System.out.println("Application is shutting down!");
        System.out.println("Closing DB connections...");
        System.out.println("Sending shutdown alert...");
    }
}
```

**What's happening:**

- `@Component` → Spring creates the bean.
- `@EventListener` → registers this method as a listener.
- The **method parameter type** decides which event it listens to — `ApplicationStartedEvent` here fires only on startup.

### Flow

```text
SpringApplication.run()
        ↓
Spring Boot starts the context
        ↓
Spring publishes ApplicationStartedEvent
        ↓
StartupListener.onStartup() executes
        ↓
App runs normally
        ↓
App shuts down
        ↓
Spring publishes ContextClosedEvent
        ↓
ShutdownListener.onShutdown() executes
```

**Key concept:** you never called these listener methods manually. Spring detected them, matched them to the event type, and executed them — because of `@EventListener`, not because of any explicit wiring you wrote.

### Common Confusions, Answered

- **"Where is `ApplicationEventPublisher` used here?"** — Not by you. Spring uses it internally (`ApplicationContext extends ApplicationEventPublisher`).
- **"Who called my method?"** — Spring's internal event dispatcher.
- **"Why no interface implementation?"** — `@EventListener` replaces the need to `implement ApplicationListener<T>` explicitly.

### Real-World Use Cases

| On Startup | On Shutdown |
|---|---|
| Warm up cache | Save in-memory data |
| Load ML model | Close connections |
| Start schedulers | Notify monitoring system |

------------------------------------------------------------------------

## Publishing Your Own Events

### What We're Building

```text
CricketScoreBroadcaster → publishes event
        ↓
CricketScoreEvent → carries data
        ↓
Listener1 (@EventListener)
Listener2 (ApplicationListener)
```

One publisher, multiple listeners — the Observer pattern, end to end, with your own event type instead of a built-in one.

### Step 1 — the Custom Event

Modern Spring doesn't require extending `ApplicationEvent`, but the explicit version makes the mechanics visible:

```java
import org.springframework.context.ApplicationEvent;

public class CricketScoreEvent extends ApplicationEvent {
    private final int runs;
    private final int wickets;
    private final int overs;

    public CricketScoreEvent(Object source, int runs, int wickets, int overs) {
        super(source);   // required — records who fired the event
        this.runs = runs;
        this.wickets = wickets;
        this.overs = overs;
    }

    public int getRuns() { return runs; }
    public int getWickets() { return wickets; }
    public int getOvers() { return overs; }
}
```

An event is just a data container: **"something happened" + the data describing it.**

### Step 2 — the Publisher

```java
@Component
public class CricketScoreBroadcaster {
    @Autowired
    private ApplicationEventPublisher eventPublisher;

    public void broadcast(int runs, int wickets, int overs) {
        System.out.println("Score Update: " + runs + "/" + wickets + " (" + overs + " overs)");

        CricketScoreEvent event = new CricketScoreEvent(this, runs, wickets, overs);
        eventPublisher.publishEvent(event);
    }
}
```

`ApplicationEventPublisher` is the bridge to Spring's event system; `publishEvent()` triggers every registered listener for that event type. **You publish → Spring notifies all listeners.**

### Step 3 — Listener 1 (Modern Way)

```java
@Component
public class ScoreListener1 {
    @EventListener
    public void handleScore(CricketScoreEvent event) {
        System.out.println("Listener1 (Mobile App): " + event.getRuns() + "/" + event.getWickets());
    }
}
```

### Step 4 — Listener 2 (Explicit Interface Way)

```java
@Component
public class ScoreListener2 implements ApplicationListener<CricketScoreEvent> {
    @Override
    public void onApplicationEvent(CricketScoreEvent event) {
        System.out.println("Listener2 (TV Broadcast): " + event.getRuns() + "/" + event.getWickets());
    }
}
```

Spring detects the generic type parameter (`CricketScoreEvent`) and binds this listener to exactly that event type.

### Step 5 — Trigger the Flow

```java
@Configuration
public class RunnerConfig {
    @Bean
    public ApplicationRunner run(CricketScoreBroadcaster broadcaster) {
        return args -> broadcaster.broadcast(120, 3, 15);
    }
}
```

### Final Flow

```text
App starts
   ↓
RunnerConfig triggers broadcaster
   ↓
CricketScoreBroadcaster.broadcast()
   ↓
publishEvent(event)
   ↓
Spring Event Dispatcher
   ↓
Listener1 executes
Listener2 executes
```

```text
Score Update: 120/3 (15 overs)
Listener1 (Mobile App): 120/3
Listener2 (TV Broadcast): 120/3
```

### Key Insights

**1. Loose coupling** — `CricketScoreBroadcaster` does not know its listeners exist. Ten more listeners could be added with zero change to the broadcaster.

**2. One-to-many** — one event, multiple independent reactions.

**3. Same thread by default** — publisher → Listener1 → Listener2 run sequentially, on the same thread. This is **blocking** behavior, not async.

**4. Order is not guaranteed** — don't depend on listener execution order unless explicitly configured.

### Common Mistakes

- **Forgetting `@Component`** on a listener class — it simply won't be registered, with no error.
- **Expecting async behavior** — it's synchronous by default; a slow listener blocks everything after it.
- **Heavy logic inside a listener** — since execution is synchronous by default, this can slow the entire publishing call.

### The Mental Model Upgrade

```text
Before:  Service A → calls Service B directly     (tight coupling)

After:   Service A → announces an event
                          ↓
                B, C, D react independently         (loose coupling)
```

**Interview punchline:** *"Spring's event mechanism allows decoupled communication where publishers emit events and multiple listeners react without direct dependency."*

### Engineering Insight

This is the Observer Pattern, not just "an annotation that fires code" — the payoff is identical to Observer anywhere else: the publisher's code never has to change to add a new reaction, because it never held a reference to any listener in the first place. It's also a genuine alternative to the circular-dependency problem from the top of this chapter: two beans that seem to need each other often actually need to *react to the same event*, not hold a direct reference to one another.

------------------------------------------------------------------------

## Interview Q&A

### Why does Spring reject circular bean dependencies by default?

Because neither bean can complete construction without the other already existing — there's no valid instantiation order. Spring Boot 2.6+ disables the legacy workaround (exposing early, partially-constructed bean references) and fails fast instead, forcing a redesign of the dependency graph.

### What's a real fix for a circular dependency between two beans, beyond re-enabling legacy circular-reference support?

Redesign the ownership so the graph is acyclic — extract shared behavior into a third bean both depend on, defer one side with `@Lazy`, or replace the direct dependency with an event: one bean publishes, the other reacts, and neither holds a hard reference to the other.

### Why doesn't Spring automatically turn every class into a bean?

Component scanning only discovers `@Component`-annotated classes within the scanned package tree (by default, the package of your `@SpringBootApplication` class and its sub-packages). Classes in other packages, or third-party classes you can't annotate, are invisible to it.

### How do you register a bean for a third-party class you can't annotate?

Write a `@Bean`-annotated method inside a `@Configuration` class that constructs and returns the object — you take over the construction responsibility Spring would otherwise infer from `@Component`.

### What's the practical difference between `@Component` and `@Bean`?

`@Component` means Spring discovers and constructs the object end-to-end via scanning. `@Bean` means you personally own construction (inside a `@Configuration` class) and only hand the finished object to Spring — necessary whenever you can't put `@Component` directly on the class.

### What's the priority order Spring uses when resolving a property that exists in multiple sources?

Java Args (`-D`) highest, then Environment Variables, then `application.properties`/`application.yml`, then `@PropertySource`-registered custom files lowest.

### Why does `@Value("${SomeKey:defaultValue}")` matter for startup reliability?

Without a default, a missing property causes a Context Load Failure at startup. The `${key:default}` syntax lets the application start successfully even if that property isn't set anywhere.

### Why doesn't `@Value` resolve a key that only exists in a custom properties file, unless you do something extra?

Because Spring's default property sources don't include arbitrary files — the file has to be explicitly registered via `@PropertySource` before `@Value` can see keys defined only there.

### What naming convention do profile-specific property files require, and why does it matter?

`application-{profile}.properties` exactly — e.g. `application-beta.properties`. Spring auto-detects files that match this pattern; an underscore instead of a hyphen (`application_beta.properties`) simply won't be picked up.

### How does `@ConfigurationProperties` bind values without any `@Autowired`?

`@Component` gets the bean created, and `@ConfigurationProperties(prefix = "...")` injects matching property values during that same creation process, via setter injection under the hood — no explicit wiring code is needed.

### Why are setters required on a `@ConfigurationProperties` class?

Because Spring uses setter injection internally to populate the bound fields — without setters, the properties simply won't populate, and setters also give you a natural place to validate/sanitize values coming from an external, potentially untrusted config source.

### What is the Observer Pattern, and how does Spring implement it?

One object (the Subject/Publisher) announces something happened; many independent objects (Observers/Listeners) react. Spring implements this with `ApplicationEventPublisher` as the publisher, `@EventListener` (or `implements ApplicationListener<T>`) as listeners, and an internal dispatcher that matches events to listeners by type.

### How does a listener method know which event type to react to?

From its own parameter type — `@EventListener public void onStartup(ApplicationStartedEvent event)` only fires for `ApplicationStartedEvent`; Spring inspects the parameter to register the binding.

### Are Spring application events processed asynchronously by default?

No — by default, listeners execute synchronously, on the same thread as the publisher, in unspecified order. A slow or heavy listener blocks everything downstream of the `publishEvent()` call.

### What's the main engineering benefit of using events instead of direct method calls between services?

Loose coupling — the publisher never holds a reference to its listeners, so new reactions can be added (or removed) without changing the publisher's code at all, unlike a direct call chain where the caller must know about every reactor.

------------------------------------------------------------------------

❌ A circular dependency between two `@Autowired` fields is just a warning — the app still starts.

✔ In Spring Boot 2.6+, circular references are prohibited by default and fail context startup outright, specifically because relying on them is discouraged.

------------------------------------------------------------------------

❌ Any class in your project automatically becomes a Spring bean once the app runs.

✔ Only classes reached by component scanning (by default, the application's own package tree) and annotated `@Component` become beans — anything outside that scope, or any class you can't annotate, needs explicit `@Bean` registration.

------------------------------------------------------------------------

❌ `application_beta.properties` (underscore) will be picked up the same as `application-beta.properties`.

✔ Spring's profile-file detection requires the exact hyphenated pattern — the underscore variant is silently ignored.

------------------------------------------------------------------------

❌ Since `MongoDBConnector` has no `@Autowired` field, its values must be hardcoded or manually set.

✔ `@ConfigurationProperties` binds property values automatically during bean creation via setter injection — no `@Autowired` is needed for this kind of binding.

------------------------------------------------------------------------

❌ Spring application events are processed asynchronously, so a slow listener won't block anything else.

✔ They're synchronous by default — publisher and every listener run sequentially, on the same thread, and a slow listener blocks the call that published the event.

------------------------------------------------------------------------

❌ Listeners always execute in the order they're defined or registered.

✔ Execution order is not guaranteed by default — don't design logic that depends on one listener running before another unless it's explicitly configured to.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
Circular bean dependency  → no valid construction order exists;
                             Spring 2.6+ fails fast by default;
                             fix the graph, don't re-enable the workaround

Component scanning         → only finds @Component within the scanned
                              package tree
@Bean + @Configuration      → for classes Spring can't discover
                              (third-party, or outside the scan path)

Property priority           → Java Args > Env Vars >
                               application.properties/yml > @PropertySource

Profile files                → application-{profile}.properties, exact
                                 hyphenated naming, merged over the defaults
@ConfigurationProperties      → binds values via setter injection,
                                 no @Autowired needed

Web request (preview)          → NIC → kernel/TCP → servlet container →
                                   DispatcherServlet → controller

Spring events                  → ApplicationEventPublisher (publish) +
                                   @EventListener / ApplicationListener<T>
                                   (react) — synchronous, same-thread,
                                   order not guaranteed by default
Events                         → decouple "what happened" from "who reacts,"
                                   the same benefit Observer always provides
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain why a circular bean dependency fails at startup, and how to actually fix it
- [x] Explain the difference between `@Component` and `@Bean`, and when each is required
- [x] Explain the full property-source priority order, and what `${key:default}` protects against
- [x] Explain why `@Value` can't see a key from a custom file without `@PropertySource`
- [x] Explain the profile file naming convention and what happens internally when a profile is active
- [x] Explain why `@ConfigurationProperties` doesn't need `@Autowired`, and why it needs setters
- [x] Explain the Observer Pattern and how `ApplicationEventPublisher`/`@EventListener` implement it
- [x] Explain why Spring's built-in events (`ApplicationStartedEvent`, `ContextClosedEvent`) never require you to write a publisher
- [x] Explain why application events are synchronous and unordered by default, and what that implies for listener design
- [x] Explain how publishing an event can eliminate a circular dependency between two beans
