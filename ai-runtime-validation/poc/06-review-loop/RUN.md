# PoC 06 — Review Loop: Execution Guide

## Prerequisites

- `bash` 4.0+
- `jq` 1.6+

## Quick Start

```bash
cd poc/06-review-loop
./scripts/run_all.sh
```

## Step-by-Step Execution

### Step 1: Initialize Feature Lifecycle

```bash
./scripts/start_feature.sh
```

**Expected:** Transitions from `feature.requested` to `plan.ready`.

### Step 2: Test Writer Leases

```bash
./scripts/test_writer_lease.sh
```

**Expected:** Codex Implementer granted write access; Claude Planner locked out.

### Step 3: Test Approval Bindings and Forgery (INV-04)

```bash
./scripts/test_approval.sh
./scripts/test_forgery.sh
```

**Expected:** Valid approval proceeds; forged approval by Implementer rejected (`AUTHORIZATION_DENIED`).

### Step 4: Test Stale Approvals

```bash
./scripts/test_stale_approval.sh
```

**Expected:** Code change revokes `merge.approved` status.

### Step 5: Test Escalation

```bash
./scripts/test_escalation.sh
```

**Expected:** 3 consecutive `changes.requested` events trigger escalation flow.