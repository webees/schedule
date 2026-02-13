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

## Timing

```
Minute: :00   :01   :02   :03   :04   :05   :06
tick-a:  🎯                 🎯                 🎯     ← min%3==0
tick-b:        🎯                 🎯                   ← min%3==1
tick-c:              🎯                 🎯             ← min%3==2
exec:    █    █    █    █    █    █    █              ← once per minute, singleton
```

## Core Mechanisms

### Minute-Aligned Precision

```bash
# Align each loop iteration to the next whole minute
SEC=$(date -u '+%-S')
WAIT=$((60 - SEC))
sleep $WAIT
```

### Triple Deduplication

```
1. Minute ownership: min%3 == offset → only one tick may trigger per minute
2. Status check: verify exec is not in_progress/queued before triggering
3. Concurrency: exec.yml group=exec → at most one instance runs
```

### Mutual Guardianship

```
tick-a detects tick-b is dead → triggers guard.yml
tick-c detects tick-b is dead → also triggers guard.yml → dropped by cancel-in-progress
guard runs as singleton → checks all ticks → revives dead chains
```

## Files

| File | Purpose | Lifecycle |
|------|---------|-----------|
| `tick-a/b/c.yml` | Timer (for-loop resident) | ~5h/cycle, auto-renews |
| `exec.yml` | Business executor (singleton) | ~30s per trigger |
| `guard.yml` | Guardian (revives dead ticks) | On-demand |

> tick-a/b/c are logically identical — only `name:` differs. Identity is derived dynamically via `github.workflow`.

## Startup

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml && sleep 60 && gh workflow run tick-c.yml
```

## Full Recovery

If all chains die (e.g., GitHub outage), manually trigger any single tick — the guardian mechanism automatically revives the others.

## License

MIT
