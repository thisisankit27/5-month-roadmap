# DNS in Practice: Propagation, Routing, Security & Deployment

------------------------------------------------------------------------

> **Goal of this Chapter**
> Day 1 covered how DNS is structured and resolved. This chapter is about the decisions a full-stack engineer actually makes with that structure: how to migrate a domain without an outage, why the apex domain fights with CNAME and what to do about it, how DNS gets weaponized for load balancing and geo-routing, how email deliverability and TLS certificates depend on DNS records, and how DNS gets misused for internal-vs-external routing. This is the layer where DNS knowledge turns into "why did production break for four hours after that deploy."

------------------------------------------------------------------------

## TTL & Propagation — Planning a Change, Not Just Understanding It

### Engineering Problem

"DNS propagation" sounds like something that happens *to* you, passively, over ambiguous "24–48 hours." In reality it's a direct, predictable consequence of TTL and caching (Day 1) — and it's something you can and should plan around before a migration, not discover mid-incident.

### What's Actually Happening

When you change a record, the **authoritative nameserver** updates immediately. What takes time is every recursive resolver around the world that had the **old** value cached, honoring its **old** TTL before it re-queries. There is no global "push" — it's a pull model, gated by however long ago each resolver last cached the answer and what TTL it was told.

```text
You change the A record at t=0
        │
        ▼
Authoritative server: updated instantly
        │
        ▼
Resolver A (cached 5 min ago, TTL 3600s)  → still serves OLD value for ~55 more minutes
Resolver B (cache just expired)            → re-queries NOW, gets NEW value immediately
Resolver C (never queried before)          → gets NEW value immediately
```

### The Practical Playbook for a Migration

1. **Before the change**, lower the TTL on the record you're about to touch (e.g. from 3600s to 300s or 60s), and wait for at least the *old* TTL's duration — so every cached copy expires and gets replaced with the new low-TTL version.
2. **Make the actual change** — now any resolver picking up the new value will only cache it for the short TTL.
3. **After confirming the migration is stable**, raise the TTL back to a normal value (e.g. an hour or a day) to reduce query load on your DNS host.

### Trade-off Table

| TTL | Pros | Cons |
|---|---|---|
| **Low** (60–300s) | Fast propagation of future changes, quick failover | More queries hit your DNS host (cost at scale), slightly higher per-lookup latency for cache misses |
| **High** (3600s+) | Fewer queries, better caching performance | Slow to propagate changes — a mistake or needed failover takes longer to take effect everywhere |

### Engineering Insight

This is the exact same reasoning as cache invalidation anywhere in a system — "how do I safely change a value that's cached downstream with a TTL I don't control the moment of expiry for." The fix is always the same shape: shrink the cache window *before* the change, make the change, then widen it back out once stable. If you've tuned a CDN cache header or a browser `Cache-Control` max-age before a deploy, you've already done this pattern.

------------------------------------------------------------------------

## The Apex/Root Domain Problem — CNAME Flattening & ALIAS

### Engineering Problem

Recap from Day 1: a CNAME must be the *only* record at that name, but the apex domain (`example.com`, no subdomain) needs NS, MX, TXT, and other records simultaneously. Yet modern hosting platforms (Vercel, Netlify, load balancers) give you a *hostname* to point at (`cname.vercel-dns.com`), not a stable IP — CNAMEs are exactly what you'd want to use, except you can't, at the apex.

### The Workarounds

| Approach | How it works | Who offers it |
|---|---|---|
| **ALIAS / ANAME record** | A provider-specific record type that *looks* like a CNAME to you, but the DNS host resolves it to an A record behind the scenes before answering — so it's spec-legal at the apex | Route 53 (as "Alias"), many modern DNS hosts |
| **CNAME flattening** | The DNS host itself performs the CNAME lookup at query time and returns a flattened A/AAAA answer, functionally the same outcome as ALIAS | Cloudflare |
| **Static A record to a fixed IP** | If the target service publishes a stable IP (some platforms do, for exactly this reason), just use a plain A record | Varies by platform |

**Practical pattern for most projects:** put the `www` subdomain as a CNAME to the platform's hostname (fully spec-legal, subdomains have no such restriction), and either redirect the apex to `www`, or use your DNS host's ALIAS/flattening feature to point the apex at the same target directly.

### Engineering Insight

This is a workaround layered *below* the protocol, not a change to it — the DNS host is doing the CNAME resolution work at answer-time so the wire protocol still only ever sees a valid A/AAAA record. It's the same shape as an ORM doing eager-loading to hide N+1 queries from the caller: the constraint at the low level didn't change, a layer above absorbed the complexity.

------------------------------------------------------------------------

## Email Deliverability — SPF, DKIM, DMARC

### Engineering Problem

Anyone can send an email claiming to be `from: you@example.com` — SMTP has no built-in sender verification. Without DNS-based proof of legitimacy, receiving mail servers (Gmail, Outlook) have no way to distinguish your real transactional email (password resets, invoices) from spoofed spam, and increasingly just reject or spam-folder anything unverified.

### The Three Records, What Each Proves

| Record | Type | Proves |
|---|---|---|
| **SPF** (Sender Policy Framework) | TXT | *Which mail servers are allowed to send mail claiming to be from this domain* — a list of authorized sending IPs/hosts |
| **DKIM** (DomainKeys Identified Mail) | TXT (public key) | *The email wasn't tampered with in transit* — the sending server signs the message with a private key; the receiver verifies against the public key published in DNS |
| **DMARC** (Domain-based Message Authentication, Reporting & Conformance) | TXT | *What to do if SPF/DKIM fail* — a policy (`none` / `quarantine` / `reject`) plus a reporting address for who to notify about failures |

```text
Incoming mail claiming to be from example.com
        │
        ▼
Receiving server checks SPF   → is the sending IP authorized for example.com?
        │
        ▼
Receiving server checks DKIM  → does the signature verify against the published public key?
        │
        ▼
Receiving server applies DMARC policy → both failed? reject / quarantine / allow, per your policy
```

### Why This Matters for a Full-Stack Engineer Specifically

Any transactional email flow (SES, SendGrid, Postmark, Google Workspace) requires you to add these exact TXT/CNAME records to your DNS zone during setup — this is the single most common "why are my emails going to spam" root cause, and it's a DNS configuration problem, not a code problem.

### Engineering Insight

SPF/DKIM/DMARC is a real-world example of **defense in depth applied to a broadcast protocol with no built-in auth**: SPF checks the transport-level sender, DKIM checks message integrity via signature, DMARC defines the enforcement policy and feedback loop. No single record is sufficient alone — SPF alone breaks under forwarding, DKIM alone doesn't say what to do on failure — the three compose into one verification story.

------------------------------------------------------------------------

## DNSSEC — Authenticity, Not Encryption

### Engineering Problem

Plain DNS responses are unsigned and unauthenticated — a resolver has no cryptographic way to know a response actually came from the real authoritative server and wasn't forged or tampered with in transit (**DNS cache poisoning / spoofing**). An attacker who can inject a fake response can redirect a domain's traffic anywhere, including to a phishing clone or an intercepting mail server.

### What DNSSEC Actually Adds

DNSSEC adds a **chain of cryptographic signatures**, mirroring the DNS hierarchy itself: the root signs the TLD's key, the TLD signs the domain's key, the domain signs its own records. A validating resolver can walk that chain and confirm the answer is authentic and unmodified.

**Important distinction:** DNSSEC provides **authenticity and integrity** — proof the answer is genuine and unaltered. It does **not** provide **confidentiality** — DNS queries and answers under DNSSEC are still plaintext, visible to anyone observing the traffic (that's a separate concern, addressed by DNS-over-HTTPS/DNS-over-TLS, a different mechanism entirely).

### Trade-offs

| Benefit | Cost |
|---|---|
| Prevents cache-poisoning/spoofing attacks on your domain's records | Adds operational complexity (key rotation, signing) |
| Enables trust chains other systems build on (e.g. some CAA/cert-issuance policies) | Slightly larger DNS responses; misconfiguration can cause total resolution failure (a broken signature chain makes the domain unresolvable, not just insecure) |

### Engineering Insight

DNSSEC is the DNS-layer analogue of TLS certificate chains — a hierarchy of signatures where each level vouches for the next, rooted in one trust anchor (the DNS root, analogous to a root CA). The "authenticity ≠ confidentiality" distinction is worth internalizing generally: plenty of security mechanisms provide one without the other, and conflating them is a common interview trap.

------------------------------------------------------------------------

## DNS-Based Load Balancing, Failover & Geo-Routing

### Engineering Problem

A single A record pointing at one IP means one server, one region, one point of failure. Before you reach for a dedicated load balancer, DNS itself already provides several routing strategies — because "return a different answer depending on context" was already the core operation DNS performs.

### The Strategies

| Strategy | How it works | Use case |
|---|---|---|
| **Round-robin DNS** | Multiple A records for one name; resolver returns them in rotating order | Crude load distribution across identical servers — no health awareness |
| **Weighted routing** | Multiple targets, traffic split by configured percentage | Canary releases, gradual migrations (e.g. 5% to new infra) |
| **Latency-based routing** | Returns the target with the lowest measured latency from the querying resolver's region | Multi-region deployments optimizing for user-perceived speed |
| **GeoDNS / geolocation routing** | Returns different records based on the querier's geographic location | Serving region-specific content, or data-residency compliance |
| **Failover routing** | Health-checks the primary target; automatically returns the backup if the primary fails checks | High-availability setups without an active load balancer in front |
| **Anycast** | The *same* IP address is announced from multiple physical locations at the BGP routing layer; network routing (not DNS) sends the client to the nearest one | How root DNS servers and CDNs (Cloudflare, Fastly) achieve global low latency from one IP |

### Why This Isn't "Just Use a Load Balancer" Instead

DNS-based routing operates **before** any connection is established — the client doesn't even know which IP to connect to yet. A load balancer, by contrast, sits in the request path *after* DNS resolution, in front of an already-chosen IP. They're complementary, not competing: DNS routing picks which **region/cluster**, a load balancer distributes **within** that cluster. Large-scale systems typically use both — GeoDNS/latency routing to the nearest region, then a regional load balancer across that region's servers.

### Engineering Insight

This is load balancing pushed to the earliest possible layer of the request lifecycle — deciding "where" before a single packet is sent to the actual service, rather than after. The same instinct — fail fast, decide early, cheaper the earlier you decide — shows up throughout distributed systems design (schema validation before a DB round-trip, auth checks before business logic runs).

------------------------------------------------------------------------

## Wildcard & Split-Horizon DNS

### Wildcard DNS

```text
*.example.com  →  A record / target
```

A wildcard record matches **any** subdomain that doesn't have its own explicit record — `anything.example.com`, `foo.example.com` all resolve to the same target. Common for multi-tenant SaaS (`tenant-a.example.com`, `tenant-b.example.com` all routing to the same app, which then reads the `Host` header to determine the tenant) and for wildcard TLS certificates that need to cover unpredictable subdomain names.

**Trade-off:** convenient for dynamic subdomain provisioning, but it also means a typo'd or unintended subdomain silently resolves instead of failing loudly (`NXDOMAIN`) — which can be a security or debugging surprise (e.g. it can defeat some subdomain-takeover detection tooling that expects to see `NXDOMAIN` for unregistered names).

### Split-Horizon (Split-Brain) DNS

The same domain name resolves to **different answers depending on who's asking** — typically, internal company network clients get an internal/private IP, while external clients get the public-facing IP. Implemented by running two separate authoritative zones (internal DNS servers vs public-facing ones) for the same name.

**Use case:** an internal admin dashboard at `admin.example.com` that should route to a private VPC IP for employees on the corporate network, but shouldn't even be discoverable (or should hit a different, more restricted endpoint) from the public internet.

------------------------------------------------------------------------

## Connecting a Domain to Hosting — The Full-Stack Checklist

### Engineering Problem

This is where all the above concepts land for a working project: you have a domain, you have an app deployed somewhere (Vercel, Netlify, EC2 + a load balancer, S3 + CloudFront), and you need the domain to actually route to it *and* be servable over HTTPS.

### The Flow

```text
1. Deploy the app → hosting platform gives you a target (an IP, or a CNAME-able hostname)
2. Add DNS records in your zone:
      - apex (example.com)  → ALIAS/ANAME/flattened-CNAME or A record, per Day 2's apex workaround
      - www.example.com     → CNAME to the platform's hostname
3. Platform (or you, via Let's Encrypt/ACME) issues a TLS certificate for the domain
      - HTTP-01 challenge: platform serves a file at a well-known path, proving control over the domain via the web server
      - DNS-01 challenge: you add a specific TXT record proving control over the DNS zone itself
        (required for wildcard certs, since there's no single HTTP path that proves ownership of *.example.com)
4. TTL/propagation window (Day 2's first section) before the change is universally visible
```

### Why DNS-01 Matters Specifically

**HTTP-01** proves you control the *web server* at that name. **DNS-01** proves you control the *DNS zone* — which is the only way to prove ownership of a name that has no running web server yet, or to issue a **wildcard certificate** (`*.example.com`), since a wildcard can't be proven by serving a file at one specific hostname's path. This is why automated cert tools (`certbot`, ACME clients) support a "DNS provider plugin" — they need API access to your DNS host to programmatically add the proof TXT record.

### Engineering Insight

Domain-to-hosting setup is really the composition of everything in these two notes: record types (Day 1) solving apex-vs-subdomain routing (this note's ALIAS section), TTL/propagation timing your cutover safely, and DNS-01 validation reusing the same "prove you control this zone" trust model that DNSSEC and SPF/DKIM/DMARC all rely on — DNS keeps getting reused as a low-friction, universally-checkable proof-of-ownership channel, not just a name-to-IP lookup.

------------------------------------------------------------------------

## Interview Q&A

### Why does "DNS propagation" take time, and how do you plan around it for a migration?

Propagation delay is just cached-TTL expiry across many independent resolvers — there's no global push, only pull with a cache lifetime. The safe pattern is: lower the TTL well before the change, wait out the old TTL so all cached copies expire, make the change, then raise the TTL back once stable.

### Why can't you put a CNAME on the apex domain, and how do platforms work around it?

A CNAME must be the only record at that name, but the apex needs NS/MX/TXT records simultaneously. DNS hosts work around it with an ALIAS/ANAME record or CNAME flattening — the host resolves the target to an A/AAAA record behind the scenes so the wire response is still spec-legal.

### What's the difference between SPF, DKIM, and DMARC?

SPF authorizes which mail servers may send on the domain's behalf. DKIM cryptographically signs messages so tampering can be detected. DMARC defines the enforcement policy (reject/quarantine/allow) when SPF or DKIM checks fail, plus a reporting mechanism. They're complementary — none alone is sufficient.

### What does DNSSEC actually protect against, and what does it not protect?

It protects against cache poisoning/spoofing by adding a cryptographic signature chain mirroring the DNS hierarchy, proving a response is authentic and unmodified. It does not provide confidentiality — queries and answers remain plaintext; that's addressed separately by DNS-over-HTTPS/TLS.

### How does DNS-based load balancing differ from a traditional load balancer, and why use both?

DNS routing decides which region/cluster to send a client to *before* any connection is made, at resolution time. A load balancer sits after resolution, distributing traffic within an already-chosen cluster. Large systems typically use both: GeoDNS/latency routing to the nearest region, then a load balancer within it.

### Why does issuing a wildcard TLS certificate require the DNS-01 challenge specifically, not HTTP-01?

HTTP-01 proves control of a single web server at one hostname's path — it can't prove ownership of an unbounded set of subdomains. DNS-01 proves control of the DNS zone itself by requiring a specific TXT record, which is the only way to prove ownership of `*.example.com` as a whole.

### What's split-horizon DNS and why would you use it?

The same domain name resolves to different answers depending on the requester — e.g. internal employees get a private VPC IP, external clients get the public IP (or nothing). Used for internal tools/admin panels that should be reachable on the corporate network without being fully public.

------------------------------------------------------------------------

❌ DNS propagation is an unpredictable waiting period you just have to tolerate.

✔ It's a direct, plannable consequence of TTL — lower the TTL before a change, wait out the old cache window, then change, then raise it back.

------------------------------------------------------------------------

❌ DNSSEC encrypts DNS traffic so no one can see your queries.

✔ DNSSEC proves authenticity/integrity (the answer is genuine and unmodified) — it does not provide confidentiality; queries stay plaintext.

------------------------------------------------------------------------

❌ SPF alone is enough to stop email spoofing of your domain.

✔ SPF only authorizes sending IPs — it breaks under mail forwarding and says nothing about message tampering or enforcement. DKIM (integrity) and DMARC (enforcement policy) are both needed alongside it.

------------------------------------------------------------------------

❌ A load balancer and DNS-based routing solve the same problem, so you only need one.

✔ DNS routing picks a region/cluster before a connection exists; a load balancer distributes within a cluster after resolution. They compose — most large systems use both.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
TTL/propagation      → pull-based cache expiry, not a push
                        migration playbook: lower TTL → wait → change → raise TTL

Apex + CNAME conflict → CNAME must be sole record at a name; apex needs NS/MX/TXT too
                        fix: ALIAS/ANAME or CNAME flattening (DNS host resolves it for you)

Email auth            → SPF (who can send) + DKIM (integrity, signed) + DMARC (enforcement policy)
                        none alone is sufficient — defense in depth

DNSSEC                 → authenticity/integrity via signature chain mirroring the DNS hierarchy
                          NOT confidentiality (queries still plaintext)

DNS-based routing      → round-robin / weighted / latency-based / GeoDNS / failover / anycast
                          decides destination BEFORE a connection exists — complements, not
                          replaces, a load balancer

Wildcard DNS            → *.example.com catches unmatched subdomains — convenient, but hides
                            typos/unintended names that would otherwise NXDOMAIN

Split-horizon DNS       → same name, different answer depending on who's asking
                            (internal vs external resolvers)

HTTP-01 vs DNS-01        → HTTP-01 proves control of a web server at one path
                            DNS-01 proves control of the whole zone — required for wildcard certs
```

------------------------------------------------------------------------

## Stage 2 · Week 2 Checklist

- [x] Explain why DNS propagation happens and design a safe TTL-lowering playbook for a migration
- [x] Explain why the apex domain can't be a CNAME, and name at least one workaround
- [x] Explain what SPF, DKIM, and DMARC each individually prove, and why all three are needed together
- [x] Explain what DNSSEC protects against and explicitly what it does NOT provide
- [x] Name at least four DNS-based routing strategies and when each is appropriate
- [x] Explain why DNS-based routing and a load balancer are complementary, not redundant
- [x] Explain what a wildcard DNS record is, and one downside of using it
- [x] Explain split-horizon DNS and a real use case for it
- [x] Explain why a wildcard TLS certificate requires the DNS-01 challenge instead of HTTP-01
