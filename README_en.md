# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

> 🎯 **Make GitHub Actions trigger precisely every minute.**

## ✨ Highlights

- ⏱️ **Minute-level precision** — bypass GitHub cron's 5-min minimum + throttling delays
- 🔒 **Git Ref atomic lock** — dual-chain race, server-side guarantee of exactly 1 exec
- 🛡️ **Self-healing** — mutual guardianship + auto-renewal, 7×24 unattended
- 📦 **Minimal** — 2 Python scripts (56 + 20 lines), zero external dependencies

## ❌ Problem

GitHub Actions cron has a 5-minute minimum interval, with actual delays reaching **50+ minutes**.

## ✅ Solution

Dual tick chains reside in VMs via for-loops (~5h each), aligning to exact minute boundaries, competing through **Git Ref atomic locks** to trigger a singleton executor.

## 🏗️ Architecture

```
tick-a (for loop, 5h resident) ──┐
                                 ├── atomic lock race ──→ exec.yml (singleton) ──→ external repos
tick-b (for loop, 5h resident) ──┘
         ↕ mutual guard
    guard.yml (reviver)
```

## 🔧 Core Mechanisms

### 🔒 Git Ref Atomic Lock

```python
# Create unique tag per minute: refs/tags/lock/exec-202602140445
# GitHub API guarantees: same ref can only be created once

tick-a: POST /git/refs → 201 Created  ✅ lock acquired → trigger exec
tick-b: POST /git/refs → 422 Conflict ❌ exists → skip
```

### 🛡️ Self-Healing

| Mechanism | Description |
|-----------|-------------|
| **Staggered renewal** | tick-a=300 rounds(5h), tick-b=330 rounds(5.5h), never gap simultaneously |
| **Auto-renewal** | Triggers next cycle after rounds complete |
| **Mutual guard** | Each tick checks its sibling on exit, revives if dead |
| **Self-destroy** | `cancel-in-progress: true` + code-level run_id detection |

```
hours: 0        5     5.5      10    10.5
tick-a: |== 300r ==|renew|== 300r ==|renew...
tick-b: |=== 330r ===|renew|=== 330r ===|renew...
                   ↑ never gap at the same time
```

## 📁 Files

```
.github/workflows/
├── tick-a.yml / tick-b.yml   ⏱️ Timers
├── exec.yml                  🚀 Business executor (singleton)
└── guard.yml                 🛡️ Guardian

scripts/
├── tick.py    ⏱️ Timer + atomic lock (56 lines)
└── guard.py   🛡️ Guardian logic (20 lines)
```

## 🚀 Startup

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

Or just `git push` to main — both chains start automatically.

## 📄 License

[MIT](LICENSE)
