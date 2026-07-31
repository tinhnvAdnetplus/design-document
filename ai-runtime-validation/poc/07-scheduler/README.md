# PoC 07: 07-scheduler

## Objective
Validate the Eligibility Scheduler and Dispatcher design — that event deliveries and command intents are selected by priority/policy/capacity without blocking on agent responses and without treating sessions as a worker pool.

## Scope
This PoC covers:
- Dispatcher routing of eligible event notices to registered sessions.
- Eligibility Scheduler selecting queued work by priority, retry schedule, leases, and policy.
- Durable Delivery Queue retaining notices until terminal outcome.
- Proper handling of Priority classes: critical, high, normal, low.
- Delivery SLAs with ack deadlines.
- Bounded retry with backoff then escalation.
- Session Registry reporting identity, lifecycle, capacity.
- Non-blocking orchestration loop.

## Architecture Assumptions Being Validated
1. Dispatcher routes eligible event notices to registered sessions.
2. Eligibility Scheduler selects queued work by priority, retry schedule, leases, and policy.
3. Durable Delivery Queue retains notices until terminal outcome.
4. Priority classes: critical, high, normal, low.
5. Delivery SLAs with ack deadlines (30s for cancellation, 2min for implementation, etc.).
6. Bounded retry with backoff then escalation.
7. Session Registry reports identity, lifecycle, capacity.
8. Non-blocking: orchestration loop never waits for agent task completion (INV-07).
9. Sessions are registered stateful actors, NOT a worker pool.
10. Scheduler fairness test (T-19).

## Success Criteria
- Dispatcher successfully queues and routes events by priority.
- Event producers never block on consumer processing (INV-07).
- Durable Delivery Queue correctly implements backoff and SLA tracking.
- Session Registry accurately tracks session capacity.
