# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

> **Make GitHub Actions execute precisely every minute, bypassing cron's 5-min minimum and throttling delays.**

## ✨ Highlights

| | |
|---|---|
| ⏱️ **Minute precision** | `time.sleep(30 - time.time() % 30)` aligns to 30-second boundaries |
| 🔒 **Atomic dedup** | Git Ref creation is inherently atomic — dual-chain race yields exactly 1 execution |
| 🛡️ **24/7 self-healing** | Auto-renewal + mutual guard + staggered gaps, fully unattended |
| 📦 **Minimal code** | Single file tick.py, zero external dependencies |

---

## Architecture

```
tick-a (5h,  600 rounds) ──┐
                            ├── Git Ref atomic lock ──→ external repos
tick-b (5.5h, 660 rounds) ──┘
     ↕ mutual guard (direct restart)
```

## Atomic Lock

Both ticks attempt to create the same Git Ref each minute. GitHub guarantees only one succeeds:

```
tick-a: POST /git/refs → 201 Created  ✅ lock acquired → trigger target
tick-b: POST /git/refs → 422 Conflict ❌ exists → skip
```

| Property | Description |
|----------|-------------|
| Atomic | Same ref cannot be created twice |
| Race-free | No status polling, no API delay window |
| Self-cleaning | Old lock tags auto-deleted every 5 minutes |

## Self-Healing

| Mechanism | Description |
|-----------|-------------|
| Staggered renewal | tick-a 600 rounds / tick-b 660 rounds, never gap simultaneously |
| Auto-renewal | `workflow_dispatch` next cycle on completion |
| Mutual guard | Check sibling every round (30s), restart directly if dead |
| Self-destroy | `cancel-in-progress` + run_id detection, instant switch on push |

| Hour | 0 | 5 | 5.5 | 10 | 10.5 |
|------|---|---|-----|----|----- |
| tick-a | 🟢 running | 🔄 renew | 🟢 running | 🟢 running | 🔄 renew |
| tick-b | 🟢 running | 🟢 running | 🔄 renew | 🟢 running | 🟢 running |

> At least 1 chain is always online

## Fault Tolerance

| Scenario | Result |
|----------|--------|
| Both alive | 2 race → exec 1 time ✅ |
| One alive | 1 direct lock → exec 1 time ✅ |
| Both dead | `git push main` or manual trigger any tick 🔄 |

## Files

```
.github/workflows/
├── tick-a.yml    Timer A (600 rounds ≈ 5h)
└── tick-b.yml    Timer B (660 rounds ≈ 5.5h)

tick.py               Timer + atomic lock + dispatcher
```

## Extension

Single config: Secret `DISPATCH`, one entry per line, two formats supported:

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
*/5 * * * *  owner/repo  check.yml
0   8 * * *  owner/repo  daily.yml
@30s         owner/repo  poll.yml
```

> **Adding tasks only requires changing the Secret, no code changes.**

## Startup

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

Or `git push main` to auto-start both chains.

## License

[MIT](LICENSE)
