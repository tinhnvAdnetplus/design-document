# PoC 04 — Capability Registry: Execution Guide

## Prerequisites

- `bash` 4.0+
- `jq` 1.6+
- tmux 3.0+ (for adapter context testing)
- All fixture files in `fixtures/` directory

## Quick Start

```bash
cd poc/04-capability-registry
./scripts/run_all.sh
```

## Step-by-Step Execution

### Step 1: Register Adapter Capabilities

```bash
./scripts/register_capability.sh fixtures/claude_capability.json
./scripts/register_capability.sh fixtures/codex_capability.json
```

**Expected:** Both documents registered. Registry reports 2 active adapters.

### Step 2: Query Registry

```bash
./scripts/query_registry.sh claude
./scripts/query_registry.sh codex
```

**Expected:** Returns registered capability documents with version, supported operations.

### Step 3: Test Gate Decisions

```bash
./scripts/test_gate_decisions.sh
```

**Expected:**
- Fork request with `native_fork=true` → native fork path
- Fork request with `synthetic_fork=true` → synthetic fork path
- Resume request with `resume=true` → resume permitted
- Resume request without `resume=true` → fresh reconstruction selected

### Step 4: Test Revalidation

```bash
./scripts/test_revalidation.sh
```

**Expected:** Simulated startup, restart, and adapter upgrade all trigger fresh `capabilities()` calls.

### Step 5: Test Mismatch

```bash
./scripts/test_mismatch.sh
```

**Expected:** When adapter behavior contradicts declaration, status becomes `ADAPTER_UNAVAILABLE`.

## Cleanup

```bash
rm -rf ../../tmp/capability-registry-*
```