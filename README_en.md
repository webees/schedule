# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

> **Make GitHub Actions execute precisely every 30 seconds, bypassing cron's 5-min minimum and throttling delays.**

## Table of Contents

- [Highlights](#-highlights) · [Architecture](#%EF%B8%8F-architecture) · [Atomic Lock](#-atomic-lock) · [Self-Healing](#%EF%B8%8F-self-healing) · [Fault Tolerance](#-fault-tolerance)
- [Files](#-files) · [Core Functions](#%EF%B8%8F-core-functions) · [Extension](#-extension) · [Testing](#-testing) · [Startup](#-startup)

---

## ✨ Highlights

| | |
|---|---|
| ⏱️ **Second precision** | `time.sleep(max(0.1, INTERVAL - time.time() % INTERVAL))` aligns to 30-second boundaries |
| 🔒 **Atomic dedup** | Git Ref creation is inherently atomic — dual-chain race yields exactly 1 execution |
| 🛡️ **24/7 self-healing** | Auto-renewal + mutual guard + staggered gaps, fully unattended |
| 📦 **Minimal code** | Single file tick.py, zero external dependencies |
| 🧪 **Full test suite** | 257 unit tests + 24-hour fast-forward simulation |

## 🏗️ Architecture

```
tick-a ──┐
         ├── atomic lock race ──→ winner triggers external workflow
tick-b ──┘
```

## 🔒 Atomic Lock

Both ticks attempt to create the same Git Ref each round. GitHub guarantees only one succeeds:

```
tick-a: POST /git/refs → 201 Created  ✅ lock acquired → trigger target
tick-b: POST /git/refs → 422 Conflict ❌ exists → skip
```

| Property | Description |
|----------|-------------|
| Atomic | Same ref cannot be created twice |
| Race-free | No status polling, no API delay window |
| Self-cleaning | Old lock tags auto-deleted every round |

## 🛡️ Self-Healing

| Mechanism | Description |
|-----------|-------------|
| Staggered renewal | tick-a 600 rounds / tick-b 660 rounds, never gap simultaneously |
| Auto-renewal | `workflow_dispatch` next cycle on completion |
| Mutual guard | Check sibling every round (30s), restart directly if dead |
| Self-destroy | `cancel-in-progress` + run_id detection, instant switch on push |

| Hour | 0 | 5 | 5.5 | 10 | 10.5 |
|------|---|---|-----|-----|------|
| tick-a | 🟢 running | 🔄 renew | 🟢 running | 🟢 running | 🔄 renew |
| tick-b | 🟢 running | 🟢 running | 🔄 renew | 🟢 running | 🟢 running |

> At least 1 chain is always online

## 🔄 Fault Tolerance

| Scenario | Result |
|----------|--------|
| Both alive | 2 race → exec 1 time ✅ |
| One alive | 1 direct lock → exec 1 time ✅ |
| Both dead | `git push main` or manual trigger any tick 🔄 |

## 📁 Files

```
.github/workflows/
├── tick-a.yml          Timer A (600 rounds ≈ 5h)
└── tick-b.yml          Timer B (660 rounds ≈ 5.5h)

tick.py                 Timer + atomic lock + dispatcher
test_tick.py            Unit tests (257 cases, incl. fast-forward sim)
AGENTS.md               AI coding guidelines
.env                    Local task config (syncs with Secret DISPATCH)
.gitignore              Excludes .env
```

## ⚙️ Core Functions

| Function | Purpose |
|----------|---------|
| `match_field(expr, value, field_min)` | Single cron field match (`*`, `*/N`, comma, range) |
| `match_cron(fields, now)` | 5-field cron expression match with day/month offset correction |
| `parse_dispatch()` | Parse DISPATCH secret, supports comments and blank lines |
| `schedule_round(epoch, ...)` | Pure scheduling logic (no I/O), supports fast-forward simulation |
| `dispatch(round_num, time_str, ...)` | Lock contention + trigger + logging |
| `trigger(repo, wf)` | Cross-repo workflow trigger using PAT |
| `is_expired(lock_tag, now_epoch, now_minute)` | Lock expiry check (cron/sec/legacy format compatible) |
| `sanitize_key(key)` | Cron expression → valid ref name |
| `clean_locks()` / `clean_runs()` | Clean expired locks / completed runs |
| `check_update()` | Detect newer version, exit to yield |
| `guard_peer()` | Check peer liveness, restart if dead |
| `self_renew()` | Auto-renew after round completion |

## 🔌 Extension

Single config: Secret `DISPATCH`, one entry per line, supports comments (`#`) and blank lines:

**Crontab 5-field** (minimum 1 minute):

```
min hour day month weekday  repo  workflow
```

**Second-level syntax** (any interval):

```
@Ns  repo  workflow
```

Field syntax same as crontab: `*` any / `*/5` every 5 / `0,30` specific / `1-5` range

Example:

```
# Health check every 5 minutes
*/5 * * * *  owner/repo  check.yml

# Daily report at 08:00
0   8 * * *  owner/repo  daily.yml

# Poll every 30 seconds
@30s         owner/repo  poll.yml
```

> **Adding tasks only requires changing the Secret, no code changes.**

## 🧪 Testing

```bash
python3 test_tick.py
```

Covers: pure function verification, lock expiry checks, end-to-end DISPATCH parsing, 24-hour fast-forward scheduling simulation.

## 🚀 Startup

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

Or `git push main` to auto-start both chains.

## 📄 License

[MIT](LICENSE)
