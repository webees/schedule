# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

🎯 Precise self-scheduling system — three resident chains + singleton executor + guardian, bypassing GitHub cron throttling.

## ❌ Problem

GitHub Actions cron scheduling has severe throttling: a 5-minute interval can actually become 50+ minutes.

## ✅ Solution

Three tick chains reside in VMs via for-loops (~5h per cycle), aligning to exact minute boundaries to trigger a singleton business executor.

## 🏗️ Architecture

```
tick-a (for loop, 5h resident, min%3==0) ──┐
tick-b (for loop, 5h resident, min%3==1) ──┼── exactly 1 trigger/min ──→ exec.yml (singleton)
tick-c (for loop, 5h resident, min%3==2) ──┘                                    │
         ▲                                                                      ▼
    guard.yml (singleton reviver)                                      trigger external repos
```

## ⏱️ Timing

| Min | :00 | :01 | :02 | :03 | :04 | :05 | :06 | :07 | :08 |
|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| tick-a | 🎯 | | | 🎯 | | | 🎯 | | |
| tick-b | | 🎯 | | | 🎯 | | | 🎯 | |
| tick-c | | | 🎯 | | | 🎯 | | | 🎯 |
| exec | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 🔧 Core Mechanisms

### Triple Deduplication

| Layer | Mechanism | Description |
|-------|-----------|-------------|
| 1️⃣ | `min%3 == offset` | Only one tick may trigger per minute |
| 2️⃣ | `alive("exec.yml")` | Check exec status before triggering |
| 3️⃣ | `concurrency: exec` | Platform-level singleton guarantee |

### Self-Destroy on Update

| Layer | Mechanism | Description |
|-------|-----------|-------------|
| 🅰️ | `cancel-in-progress: true` | Platform: new run cancels old run |
| 🅱️ | `check_newer()` per loop | Code: detect newer run_id → `sys.exit` |

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
