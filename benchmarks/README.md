# Phase 3 Event Store Benchmarks

Run from the repository root with the production package on `PYTHONPATH`:

```bash
PYTHONPATH=src python3 benchmarks/event_store_benchmark.py --samples 150
```

The benchmark exports CSV, JSON, and Markdown. It measures file open, buffered
write, flush, fsync, SQLite WAL commit, close, bounded batch commit, projection,
replay, and end-to-end durable acceptance. The command exits non-zero when the
unchanged 50 ms group-commit p99 target is missed.
