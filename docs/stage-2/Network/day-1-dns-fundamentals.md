# DNS Fundamentals: Domains, Records & Resolution

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not "here's how to buy a domain on GoDaddy." DNS is a distributed, hierarchical, heavily-cached lookup system — the goal is to understand *why* it's shaped as a tree of authorities instead of one giant lookup table, what each record type actually delegates or points to, and where money changes hands in the domain ecosystem (registrar vs registry vs DNS host are three different businesses, not one). Get this model right and every "why won't my domain resolve" or "why is this taking 24 hours" question stops being mysterious.

## Crisp Definition

**DNS (Domain Name System) is a distributed, hierarchical database that translates human-readable domain names into the machine data (IP addresses, mail servers, and other records) that computers need to route requests — resolved via a chain of delegated authorities, not a single central lookup.**

------------------------------------------------------------------------

## Why DNS Exists

### Engineering Problem

Computers route traffic using IP addresses (`142.250.183.14`), not names. Without DNS, using the internet means memorizing IP addresses for every service, and every time a server's IP changes (scaling, migration, provider switch), every client that hardcoded that IP breaks.

The earliest fix — a single flat file (`HOSTS.TXT`) maintained by one organization (Stanford Research Institute, in the pre-DNS ARPANET era) and copied to every machine — worked at a few hundred hosts. It fails at internet scale for three concrete reasons:

- **Single point of failure / update bottleneck** — every new host means one team edits one file and every machine on the network re-downloads it.
- **No delegation** — one organization can't reasonably know about, or be trusted to manage, every name for every organization on earth.
- **No horizontal scaling of ownership** — a company should be able to manage its own subdomains without asking a central authority to edit a shared file.

### Engineering Insight

DNS's actual innovation isn't "name → IP mapping" — a flat file already does that. It's **hierarchical delegation of authority**: no single server holds the whole internet's records; instead, each level of the domain tree delegates responsibility for the level below it to a different, independently-operated server. This is the same idea as a package/namespace hierarchy in code — a root doesn't need to know every leaf, it only needs to know who to ask next.

------------------------------------------------------------------------

## Anatomy of a Domain Name

```text
        https://api.staging.example.com/v1/users
                 │      │       │    │
                 │      │       │    └── TLD  (Top-Level Domain)
                 │      │       └─────── SLD  (Second-Level / registered domain)
                 │      └─────────────── Subdomain (label)
                 └────────────────────── Subdomain (label, nested)
```

Read right to left — that's the actual delegation order:

| Term | Example | What it is |
|---|---|---|
| **TLD** (Top-Level Domain) | `.com`, `.io`, `.dev` | Managed by a **registry** (e.g. Verisign runs `.com`) |
| **SLD / registered domain** | `example.com` | The name you actually register and pay for — `example` is the SLD, `.com` is the TLD |
| **Subdomain** | `api.example.com`, `staging.example.com` | A label prepended to the registered domain — free, unlimited, controlled entirely by whoever owns `example.com` |
| **FQDN** (Fully Qualified Domain Name) | `api.staging.example.com.` | The complete, unambiguous name including the (usually hidden) trailing root dot |

**The trailing dot matters conceptually even though browsers hide it.** `example.com.` is the fully qualified form — the empty label after the final dot represents the DNS **root zone**, the top of the entire tree. Every domain is implicitly a child of the root.

### Subdomains Are Not a Separate Product

This is the detail people trip on: a subdomain is **not purchased separately** and does not need registry involvement. Once you own `example.com`, you fully control its DNS zone — adding `anything.example.com` is just adding a record in your own zone file, free and instant (modulo TTL/propagation, covered in Day 2). This is why companies run `app.`, `api.`, `blog.`, `staging.` subdomains liberally: they cost nothing beyond the one SLD registration.

------------------------------------------------------------------------

## The DNS Hierarchy & Resolution Flow

### Engineering Problem

Given a name like `api.example.com`, some machine has to figure out, in order: *who runs `.com`? who runs `example.com` within `.com`? who runs `api` within `example.com`?* Answering that efficiently — without every device on earth talking directly to root servers for every lookup — is the actual distributed-systems problem DNS solves.

### The Resolution Chain

```text
Browser                Recursive Resolver         Root Server        TLD Server (.com)      Authoritative Server
   │  "api.example.com?"       │                       │                    │                     │
   ├──────────────────────────▶│                       │                    │                     │
   │                           │  "who handles .com?"  │                    │                     │
   │                           ├──────────────────────▶│                    │                     │
   │                           │◀── refers to .com TLD ┤                    │                     │
   │                           │                       │                    │                     │
   │                           │  "who handles example.com?"                │                     │
   │                           ├────────────────────────────────────────────▶│                    │
   │                           │◀── refers to example.com's nameservers ─────┤                    │
   │                           │                                                                   │
   │                           │  "what's the A record for api.example.com?"                       │
   │                           ├──────────────────────────────────────────────────────────────────▶│
   │                           │◀──────────────────────────── returns IP address ───────────────────┤
   │◀── returns IP to browser ─┤                                                                    │
```

| Actor | Role |
|---|---|
| **Recursive resolver** | The client-facing server (your ISP's, or `8.8.8.8` / `1.1.1.1`) that does the multi-hop work on the client's behalf and **caches** the result |
| **Root server** | Knows only which server is authoritative for each TLD (`.com`, `.org`, `.io`, …) — there are 13 logical root server addresses, globally anycast |
| **TLD server** | Knows which nameservers are authoritative for each registered domain under that TLD |
| **Authoritative nameserver** | Holds the actual DNS zone file for the domain — the actual source of truth for `example.com`'s records (this is what your DNS host, e.g. Cloudflare or Route 53, runs) |

**Iterative vs recursive, precisely:** the browser makes one **recursive** query to the resolver ("give me the final answer, I don't want to talk to root/TLD/authoritative myself"). The resolver then makes a series of **iterative** queries up the chain, each server answering "I don't know, but here's who to ask next," until it reaches the authoritative server holding the real record.

### Why Caching Makes This Fast in Practice

Every response carries a **TTL (Time To Live)**, in seconds — how long the resolver is allowed to cache that answer before re-querying. In steady state, almost no lookup actually walks the full root → TLD → authoritative chain; the recursive resolver (or even the OS/browser cache) already has a cached, unexpired answer. The full chain only runs on a cold cache. This is the same trade-off as any caching layer: correctness (fresh data) traded against cost (query load, latency) — TTL is that trade-off's dial, covered in depth in Day 2.

### Engineering Insight

DNS resolution is a real-world instance of a **trie / prefix-tree lookup with delegated ownership at each node**, plus a caching layer bolted on for performance. Each node in the domain tree (root → TLD → SLD → subdomain) only needs to know its immediate children's authorities, not the whole tree — exactly the same locality principle that makes routing tables, trie-based autocomplete, and filesystem path resolution tractable at scale.

------------------------------------------------------------------------

## DNS Record Types

### Engineering Problem

A domain isn't just "one name → one IP." The same name needs to resolve differently depending on *what kind of thing is asking* — a browser wants an IP, a mail server wants a mail exchange target, a certificate authority wants proof-of-ownership text, another DNS zone wants an alias, not a raw IP. One record type per concern is exactly this: separating *what data this name maps to* by the consumer's need, instead of overloading one field.

| Record | Maps a name to | Typical use |
|---|---|---|
| **A** | IPv4 address | `example.com → 93.184.216.34` |
| **AAAA** | IPv6 address | `example.com → 2606:2800:220:1::` |
| **CNAME** | Another domain name (an alias) | `www.example.com → example.com`, or `app.example.com → my-app.vercel.app` |
| **MX** | Mail server hostname + priority | Routes email for the domain to a mail provider (Google Workspace, etc.) |
| **TXT** | Arbitrary text | Domain ownership verification, SPF/DKIM/DMARC (Day 2) |
| **NS** | Authoritative nameservers for the zone (or a delegated subzone) | Tells the world *who* to ask for this domain's records |
| **SOA** | Zone metadata (primary nameserver, admin email, serial, refresh/retry/expire timers) | One per zone — describes the zone itself, not a resource |
| **PTR** | IP → name (reverse of A/AAAA) | Reverse DNS lookups, used in email deliverability/spam scoring |
| **CAA** | Which Certificate Authorities may issue TLS certs for this domain | Security control — restricts who can issue a valid cert for you |
| **SRV** | Service location: host + port for a specific protocol | Used by protocols like SIP, XMPP, or service discovery in some infra tools |

### Why CNAME Can't Coexist With Other Records on the Same Name

A CNAME says "this name is *entirely* an alias for that other name" — so if `www` is a CNAME, DNS can't also answer an MX or TXT query for `www` directly, because the spec treats a CNAME as the *only* record allowed at that name. This is why the root/apex domain (`example.com` itself, not `www.example.com`) traditionally **cannot** be a CNAME — it needs to simultaneously hold NS, MX, TXT, and other records, which a CNAME's "alias only" rule forbids. (The workaround — ALIAS/ANAME/CNAME-flattening — is a Day 2 topic.)

### Engineering Insight

This is the same design principle as a well-normalized schema or a discriminated union: rather than one overloaded record answering every question ambiguously, each record type has one job and one shape, and a resolver asks specifically for the type it needs (`dig example.com A` vs `dig example.com MX`). Adding a new capability to DNS over the decades (CAA for cert authorization, SRV for service discovery) meant adding a new record type, not redefining an existing one — an Open/Closed-style extension.

------------------------------------------------------------------------

## Registrar vs Registry vs DNS Host — Three Different Businesses

### Engineering Problem

"Buying a domain" is casually described as one transaction, but it actually involves three separable roles that can be — and often are — three different companies. Conflating them is why people get confused about where pricing comes from and why changing "who hosts my DNS" doesn't mean changing "who I bought the domain from."

```text
┌─────────────────────┐        ┌──────────────────────┐        ┌───────────────────────┐
│      Registry         │        │      Registrar          │        │      DNS Host              │
│  Owns/operates a TLD   │◀──────│  Sells domains to you,  │◀──────│  Hosts the actual zone     │
│  e.g. Verisign (.com), │ wholesale│  accredited by ICANN   │  you   │  file / answers queries    │
│  PIR (.org)             │  rate  │  e.g. Namecheap,        │ point  │  e.g. Cloudflare, Route 53,│
│                         │        │  GoDaddy, Google Domains│  NS to │  the registrar itself      │
└─────────────────────┘        └──────────────────────┘        └───────────────────────┘
```

| Role | What it does | Who's an example |
|---|---|---|
| **Registry** | Owns and operates a TLD, maintains the authoritative TLD-level database, sets wholesale pricing | Verisign (`.com`/`.net`), Public Interest Registry (`.org`), Identity Digital (`.dev`, many gTLDs) |
| **Registrar** | ICANN-accredited reseller — the interface you actually buy from; pays the registry a wholesale fee, adds markup | Namecheap, GoDaddy, Cloudflare Registrar, Google Domains (now Squarespace) |
| **DNS Host** | Runs the authoritative nameservers that actually answer queries for your zone — can be the registrar's default, or a separate provider entirely | Cloudflare, AWS Route 53, the registrar's built-in DNS |

**Why you'd split registrar and DNS host:** many engineers register through one company (often for price or UX) but point the domain's **NS records** at a different provider's nameservers for better tooling — e.g. Cloudflare's proxy/CDN/analytics, or Route 53 for tight AWS integration. This is purely a matter of "who answers DNS queries for my zone," completely independent of "who did I pay to reserve the name."

------------------------------------------------------------------------

## Domain & DNS Pricing — What You're Actually Paying For

### Engineering Problem

Pricing looks opaque ("why is `.com` $12 but `.ai` $70?") until you see it's driven by exactly two layers: what the **registry** charges the **registrar** wholesale for that TLD, and what the **registrar** marks it up to. DNS *hosting* is a separate, usually free-tier cost.

### Domain Registration Pricing

| Cost driver | Explanation |
|---|---|
| **TLD wholesale price** | Set by the registry per TLD. Legacy gTLDs (`.com`, `.net`) are ICANN price-capped and cheap (~$9–13/yr wholesale). Newer/niche gTLDs (`.ai`, `.io`, `.dev`) have no such cap and can run $30–90+/yr — registries price based on perceived demand, not delivery cost. |
| **Registrar markup** | Registrars compete on this margin — same `.com` domain can be $9 at one registrar, $20 at another. First-year "promo" pricing is common; **renewal price is the real number to check**, it's often 2–4x the first-year promo. |
| **Renewal** | Charged annually (or for however many years you pre-pay) to keep the registration active. Missing renewal after the grace period can put the domain into a redemption/auction phase — someone else can register it. |
| **Privacy protection (WHOIS privacy)** | ICANN requires registrant contact info to be published in WHOIS; registrars offer (often free, sometimes paid) a proxy service so your personal info isn't public. |
| **Transfer fee** | Moving a domain to a different registrar typically costs one renewal-year's price and re-locks the domain for a year — a switching cost, not a technical necessity. |
| **Premium / aftermarket domains** | Short, dictionary-word, or previously-registered domains are sold by resellers or the registry itself at prices with no relation to the standard wholesale rate — pure scarcity pricing. |

### DNS Hosting Pricing

Hosting your *zone* (the actual records) is a **separate cost from registration**, and for the vast majority of use cases it's free:

- Most registrars include free basic DNS hosting with registration.
- Cloudflare's free tier includes full DNS hosting, DDoS-protected authoritative nameservers, and a CDN/proxy layer, independent of who you registered through.
- Paid DNS tiers (Route 53, Cloudflare paid plans, NS1) exist for **volume** (very high query counts), **advanced routing** (GeoDNS, latency-based, weighted failover — Day 2), and **SLA guarantees**, not for basic name resolution.

### Subdomains: Always Free

Worth stating explicitly since it's a common point of confusion: **there is no per-subdomain fee.** A subdomain is just a DNS record inside a zone you already control. `app.example.com`, `api.example.com`, `staging.example.com` cost nothing beyond the one `example.com` registration — the constraint is operational (keeping records organized, TTL/propagation, cert coverage), never billing.

### Engineering Insight

The registry/registrar/DNS-host split is a textbook example of **separation of concerns across independent vendors mediated by a protocol** (the WHOIS/RDAP + registrar-registry EPP protocol layer), not a single company's product. Understanding *which* layer a cost or an outage belongs to is exactly the kind of "who owns this" reasoning that maps to production incident triage: "domain not resolving" could be a registry outage (rare), a registrar/NS misconfiguration, or your own DNS host being down — three completely different fixes.

------------------------------------------------------------------------

## Interview Q&A

### Why is DNS hierarchical instead of one central database?

A single flat file doesn't scale past a few hundred hosts — it's a single point of failure, an update bottleneck, and gives no organization the ability to manage its own names independently. DNS delegates authority level by level (root → TLD → domain → subdomain) so each zone owner controls only their own slice.

### What's the difference between a recursive query and an iterative query?

A client makes one recursive query to its resolver, asking for a final answer. The resolver then performs a series of iterative queries up the chain (root → TLD → authoritative), where each server responds "I don't know, ask this other server" until the authoritative answer is found.

### What's the difference between a registrar, a registry, and a DNS host?

The registry owns and operates a TLD (e.g. Verisign runs `.com`) and sets wholesale pricing. The registrar is the ICANN-accredited reseller you actually buy the domain from (Namecheap, GoDaddy). The DNS host runs the authoritative nameservers that answer queries for your zone — it can be the registrar's default service or a completely separate provider like Cloudflare or Route 53.

### Does adding a subdomain cost anything or require registry involvement?

No. Once you own the SLD (e.g. `example.com`), a subdomain is just a new DNS record in your own zone — free, unlimited, and entirely under your control. No registrar or registry interaction is needed.

### Why can't the apex/root domain (`example.com`) typically be a CNAME?

A CNAME means "this name is *entirely* an alias for another name," and DNS only allows a CNAME to be the sole record type at that name. The apex domain needs to simultaneously hold NS, MX, and other records, which conflicts with CNAME's "alias-only" constraint — hence the need for ALIAS/ANAME/CNAME-flattening workarounds.

### What does TTL control, and what's the trade-off in setting it low vs high?

TTL is how long a resolver may cache a DNS answer before re-querying. Low TTL means faster propagation of changes but more query load and latency for cache misses; high TTL means better caching/performance but slower propagation if the record needs to change (e.g. during a migration).

### If a domain fails to resolve, what are the three layers you'd check, in order of likelihood?

Your own DNS host/zone configuration (most likely — a misconfigured or missing record), the registrar/NS delegation (are the domain's NS records actually pointing at your DNS host?), and the registry/root infrastructure (extremely rare to be the cause, but technically the third layer).

------------------------------------------------------------------------

❌ Buying a domain means one company owns the whole pipeline from registration to resolution.

✔ It's three separable roles — registry (owns the TLD), registrar (sells you the name), DNS host (answers queries for your zone) — and you can freely mix providers across them.

------------------------------------------------------------------------

❌ Subdomains need to be purchased or registered separately from the main domain.

✔ A subdomain is just a record inside a zone you already control — free and instant to add, no registry or registrar involvement.

------------------------------------------------------------------------

❌ `mvnrepository.com`-style confusion, DNS edition: the registrar you bought from must also be where your DNS is hosted.

✔ NS records can point anywhere — it's common and often better (CDN, tooling, DDoS protection) to register at one company and host DNS at another (e.g. Cloudflare).

------------------------------------------------------------------------

❌ A `.com` costing $9 and a `.ai` costing $70 reflects different delivery costs.

✔ It reflects registry wholesale pricing policy — legacy gTLDs are ICANN price-capped, newer/niche gTLDs are priced on perceived demand with no cap.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
DNS                  → distributed, hierarchical, cached name → data lookup
                        (not a single flat table — delegation is the whole point)

Domain anatomy        → subdomain.subdomain.SLD.TLD.  (root dot implicit)
                        subdomains are free, unlimited, zone-owner controlled

Resolution chain      → client → recursive resolver → root → TLD → authoritative
                        one recursive query, many iterative queries behind it
                        TTL controls cache lifetime → propagation speed trade-off

Record types           → A/AAAA (IP), CNAME (alias), MX (mail), TXT (text/verification),
                          NS (delegation), SOA (zone metadata), CAA (cert authorization)
                          CNAME can't coexist with other records at the same name

Three businesses       → Registry (owns TLD) → Registrar (sells domain) → DNS Host (answers queries)
                          independently swappable

Pricing                → TLD wholesale (registry) + markup (registrar) = registration cost
                          DNS hosting is usually free, separate from registration
                          subdomains: always free
```

------------------------------------------------------------------------

## Stage 2 · Week 2 Checklist

- [x] Explain why DNS is hierarchical instead of a single flat lookup table
- [x] Break down a domain name into TLD, SLD, and subdomain, and explain why subdomains are free
- [x] Walk through the full resolution chain from browser to authoritative nameserver, naming each actor
- [x] Explain the difference between a recursive query and an iterative query
- [x] Name at least six DNS record types and what each one maps a name to
- [x] Explain why a CNAME can't coexist with other records at the same name
- [x] Explain the difference between a registry, a registrar, and a DNS host, with real examples of each
- [x] Explain what drives domain pricing differences between TLDs, and why renewal price often differs from first-year price
- [x] Explain what TTL controls and the trade-off between low and high values
