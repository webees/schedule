# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

Precise self-scheduling system — three resident chains + singleton executor + guardian, bypassing GitHub cron throttling.

## Problem

GitHub Actions cron scheduling has severe throttling: a 5-minute interval can actually become 50+ minutes.

## Solution

Three tick chains reside in VMs via for-loops (~5h per cycle), aligning to exact minute boundaries to trigger a singleton business executor.

## Architecture

```
tick-a (for-loop, 5h resident, owns min%3==0) ──┐
tick-b (for-loop, 5h resident, owns min%3==1) ──┼── exactly one trigger/min ──→ exec.yml (singleton)
tick-c (for-loop, 5h resident, owns min%3==2) ──┘                                    │
         ▲                                                                           ▼
    guard.yml (singleton reviver)                                           trigger external repos
```

## Core Mechanisms

### Minute-Aligned Precision

```python
wait = 60 - (time.time() % 60)
time.sleep(wait)
```

### Triple Deduplication

```
1. Minute ownership: min%3 == offset → only one tick may trigger per minute
2. Status check: verify exec is not in_progress/queued before triggering
3. Concurrency: exec.yml group=exec → at most one instance runs
```

### Old Instance Cleanup

```python
# On startup, cancel other in_progress runs of the same workflow
gh run list → find other in_progress runs → gh run cancel
```

### Mutual Guardianship

```
tick-a detects tick-b is dead → triggers guard.yml → guard revives tick-b
```

## Files

```
.github/workflows/
  tick-a/b/c.yml      Timers (only name differs, logic shared via tick.py)
  exec.yml             Business executor (singleton)
  guard.yml            Guardian

scripts/
  tick.py              Timer core logic
  guard.py             Guardian logic
```

## Startup

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml && sleep 60 && gh workflow run tick-c.yml
```

## Full Recovery

Manually trigger any single tick — the guardian mechanism automatically revives the others.

## License

MIT
