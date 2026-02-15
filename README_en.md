# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

> **Make GitHub Actions execute precisely every 30 seconds, bypassing cron's 5-min minimum and throttling delays.**

## Table of Contents

- [Highlights](#-highlights) · [Usage](#-usage) · [Startup](#-startup)
- [Atomic Lock](#-atomic-lock) · [Self-Healing](#%EF%B8%8F-self-healing) · [Fault Tolerance](#-fault-tolerance)
- [Files](#-files) · [Core Functions](#%EF%B8%8F-core-functions) · [Testing](#-testing)

---

## ✨ Highlights

| | |
|---|---|
| ⏱️ **Second precision** | `time.sleep(max(0.1, INTERVAL - time.time() % INTERVAL))` aligns to 30-second boundaries |
| 🔒 **Atomic dedup** | Git Ref creation is inherently atomic — dual-chain race yields exactly 1 execution |
| 🛡️ **24/7 self-healing** | Auto-renewal + mutual guard + staggered gaps, fully unattended |
| 📦 **Minimal code** | Single file tick.py, zero external dependencies |
| 🧪 **Full test suite** | 257 unit tests + 24-hour fast-forward simulation |

## 📋 Usage

> Single config: Secret `DISPATCH`, one entry per line, supports comments and blank lines. Cron uses UTC.

```
# crontab 5-field — min hour day month weekday  repo  workflow
*/5 * * * *  owner/repo  check.yml     # every 5 minutes
0   8 * * *  owner/repo  daily.yml     # daily at 08:00
0   9 * * 1  owner/repo  weekly.yml    # every Monday 09:00

# second-level — @Ns  repo  workflow
@30s         owner/repo  poll.yml      # every 30 seconds
```

Field syntax: `*` any · `*/5` step · `0,30` list · `1-5` range

`TZ_OFFSET` env var controls log time display. Default `0` (UTC), set to `8` for Beijing time.

## 🚀 Startup

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

Or `git push main` to auto-start both chains.

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

> Naming: `verb_noun`, predicates use `is_` prefix

| Category | Function | Purpose |
|----------|----------|---------|
| Tool | `gh` | Execute gh CLI commands |
| | `gh_api` | Call GitHub API (GET) |
| Parsing | `match_field` | Single cron field match (`*`, `*/N`, comma, range) |
| | `match_cron` | 5-field cron expression match with day/month offset correction |
| | `parse_dispatch` | Parse DISPATCH secret, supports comments and blank lines |
| Predicate | `is_expired` | Lock expiry check (cron/sec/legacy format compatible) |
| | `is_alive` | Check if workflow is running |
| Schedule | `scan_round` | Scan current round for matching tasks (pure, no I/O) |
| | `execute_task` | Lock contention + trigger + logging |
| | `trigger_workflow` | Cross-repo workflow trigger using PAT |
| Lock | `acquire_lock` | Create Git Ref for distributed lock |
| | `sanitize_key` | Cron expression → valid ref name |
| Maintain | `clean_locks` / `clean_runs` | Clean expired locks / completed runs |
| | `check_update` | Detect newer version, exit to yield |
| | `guard_peer` | Check peer liveness, restart if dead |
| | `renew_self` | Auto-renew after round completion |

## 🧪 Testing

> Covers: pure function verification, lock expiry checks, end-to-end DISPATCH parsing, 24-hour fast-forward scheduling simulation.

```bash
python3 test_tick.py
```

## 📄 License

[MIT](LICENSE)
