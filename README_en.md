# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

🎯 Precise self-scheduling system — three resident chains + singleton executor + guardian, bypassing GitHub cron throttling.

## ❌ Problem

GitHub Actions cron scheduling has severe throttling: a 5-minute interval can actually become 50+ minutes.

## ✅ Solution

Three tick chains reside in VMs via for-loops (~5h per cycle), aligning to exact minute boundaries to trigger a singleton business executor.

## 🏗️ Architecture

```
tick-a (for loop, 5h resident) ──┐
tick-b (for loop, 5h resident) ──┼── all attempt every minute ──→ exec.yml (singleton)
tick-c (for loop, 5h resident) ──┘                                       │
         ▲                                                               ▼
    guard.yml (singleton reviver)                               trigger external repos
```

## ⏱️ Timing

| Min | :00 | :01 | :02 | :03 | :04 | :05 |
|-----|-----|-----|-----|-----|-----|-----|
| tick-a | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 |
| tick-b | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 |
| tick-c | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 |
| exec | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> All three ticks attempt every minute; dedup guarantees exec runs exactly once

## 🔧 Core Mechanisms

### Deduplication

| Layer | Mechanism | Description |
|-------|-----------|-------------|
| 1️⃣ | `alive("exec.yml")` | Code: skip if exec is already running |
| 2️⃣ | `concurrency: exec` | Platform: singleton guarantee |

### Self-Destroy on Update

| Layer | Mechanism | Description |
|-------|-----------|-------------|
| 🅰️ | `cancel-in-progress: true` | Platform: new run cancels old run |
| 🅱️ | `check_newer()` per loop | Code: detect newer run_id → `sys.exit` |

### Fault Tolerance

```
3 alive: 3 attempt, exec runs 1  ✅
2 alive: 2 attempt, exec runs 1  ✅
1 alive: 1 attempt, exec runs 1  ✅
0 alive: manual recovery needed  🔄
```

## 📁 Files

```
.github/workflows/
├── tick-a/b/c.yml    ⏱️ Timers (only name differs, logic shared via tick.py)
├── exec.yml          🚀 Business executor (singleton)
└── guard.yml         🛡️ Guardian (singleton)

scripts/
├── tick.py           ⏱️ Timer logic (~50 lines)
└── guard.py          🛡️ Guardian logic (~20 lines)
```

## 🚀 Startup

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml && sleep 60 && gh workflow run tick-c.yml
```

Or just `git push` to main — all three chains start automatically.

## 📄 License

[MIT](LICENSE)
