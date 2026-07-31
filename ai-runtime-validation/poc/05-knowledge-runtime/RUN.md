# PoC 05 — Knowledge Runtime: Execution Guide

## Prerequisites

- `bash` 4.0+
- `jq` 1.6+
- Simulated git environment (`fixtures/git-repo`)

## Quick Start

```bash
cd poc/05-knowledge-runtime
./scripts/run_all.sh
```

## Step-by-Step Execution

### Step 1: Generate Knowledge Snapshot

```bash
./scripts/generate_snapshot.sh
```

**Expected:** Snapshot with 6 domains generated.

### Step 2: Test Fact Classification & Provenance

```bash
./scripts/test_fact_classification.sh
./scripts/test_provenance.sh
```

**Expected:** Facts classified; unproven confirmed facts rejected/demoted.

### Step 3: Trigger Knowledge Compression

```bash
./scripts/trigger_compression.sh
```

**Expected:** Large context >128 KiB compressed effectively.

### Step 4: Simulate Merge Evolution

```bash
./scripts/simulate_evolution.sh
```

**Expected:** Merge event triggers `knowledge.evolution.started` and purges transient facts.

### Step 5: Test Cache Taxonomy

```bash
./scripts/test_cache_isolation.sh
```

**Expected:** Independent writes to Cache Registry show strict isolation between Knowledge Cache and other caches.