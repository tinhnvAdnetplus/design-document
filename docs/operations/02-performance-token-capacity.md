# 22 — Performance, Tokens, and Capacity

## Purpose

This chapter defines efficiency goals, context budgets, queue capacity, and
performance trade-offs.

## Performance model

End-to-end feature time consists of planning, implementation, review, merge,
and synchronization. The runtime can reduce coordination overhead and repeated
context cost; it cannot guarantee model reasoning or external CI duration.

| Segment | Runtime lever | Non-runtime dependency |
| --- | --- | --- |
| root orientation | persistent cache | model behavior |
| fork setup | bounded packet, tmux lifecycle | CLI startup |
| implementation | isolated worktree, local tools | code complexity |
| review | diff-scoped packet | reviewer reasoning |
| merge | deterministic Git gateway | conflicts/CI |
| synchronization | changed-range analysis | repository size |

## Token optimization rules

1. Keep stable project context in a bounded Knowledge Cache.
2. Fork feature contexts rather than append every feature to root history.
3. Send event references, not full transcripts or diffs.
4. Prefer Git commit/path references over repeated source inclusion.
5. Select relevant facts by evidence and component, not recency alone.
6. Set byte/token budgets and reject or partition oversized packets.
7. Record observed adapter token usage when available.
8. Do not optimize by omitting safety, review, or Git verification evidence.

## Capacity controls

| Resource | Bound | Backpressure response |
| --- | --- | --- |
| active feature sessions | configuration | refuse/queue new feature request |
| writers per worktree | 1 | deny lease |
| integration merges | 1 | queue merge intent |
| pending delivery notices | per session | surface overload |
| cache bytes/facts | per root | summarize/rebuild |
| event payload bytes | per event | attachment/reference required |
| terminal captures | per session/time | truncate/redact |
| state database size | retention policy | archive/prune verified data |

## SLO examples

| Indicator | Example objective |
| --- | --- |
| event durable acceptance | 99% under 250 ms local |
| terminal notification | 95% under 2 s when ready |
| failure detection | terminal absence under 60 s |
| fresh reconstruction | root ready under 5 min |
| cache freshness | zero integrated commits behind for planning |
| invalid merge prevention | 100% rejection in test suite |

Values need calibration per hardware, repository, and CLI deployment. They are
not model-quality claims.

## Benchmark methodology

Use repeatable synthetic repositories plus representative sanitized repositories
where permitted. Run warm root/fork, cold session, resume, and lost-resume
reconstruction scenarios. Capture host resource use, packet bytes, latency
percentiles, queue depth, and model-provided token values. Separate network and
CI time from local runtime overhead.

## Trade-offs

A larger cache can lower orientation work but raises prompt cost and staleness
risk. More parallel features improve throughput but increase integration
conflict and reviewer queueing. This design favors bounded concurrency and
evidence-based context selection over maximum task fan-out.

## Future improvements

Adaptive packet selection may use dependency graphs and learned relevance
scores, provided results remain explainable, provenance-linked, bounded, and
subject to the same privacy policy.

## V2 cache and scheduler capacity

Prompt, Conversation, Resume, and Knowledge Cache layers have independent
budgets and retention. Conversation Cache bytes are normally zero because the
layer is disabled. Scheduler capacity is measured by eligible delivery age and
queue depth, not by treating stateful sessions as pooled workers. Knowledge
Compression must reduce packet cost while retaining provenance for every
published fact.
