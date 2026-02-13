# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

> **Make GitHub Actions execute precisely every minute, bypassing cron's 5-min minimum and throttling delays.**

## ✨ Highlights

| | |
|---|---|
| ⏱️ **Minute precision** | `time.sleep(60 - time.time() % 60)` aligns to exact minute boundaries |
| 🔒 **Atomic dedup** | Git Ref creation is inherently atomic — dual-chain race yields exactly 1 exec |
| 🛡️ **24/7 self-healing** | Auto-renewal + mutual guard + staggered gaps, fully unattended |
| 📦 **Minimal code** | tick.py 46 lines + guard.py 8 lines, zero external dependencies |

---

## Architecture

```
tick-a (for loop, 5h resident) ──┐
                                 ├── Git Ref atomic lock ──→ exec.yml ──→ external repos
tick-b (for loop, 5.5h resident) ┘
         ↕ mutual guard
    guard.yml
```

## Atomic Lock

Both ticks attempt to create the same Git Ref each minute. GitHub guarantees only one succeeds:

```
tick-a: POST /git/refs → 201 Created  ✅ lock acquired → trigger exec
tick-b: POST /git/refs → 422 Conflict ❌ exists → skip
```

| Property | Description |
|----------|-------------|
| Atomic | Same ref cannot be created twice |
| Race-free | No status polling, no API delay window |
| Self-cleaning | Old lock tags auto-deleted every 30 rounds |

## Self-Healing

| Mechanism | Description |
|-----------|-------------|
| Staggered renewal | tick-a 300 rounds / tick-b 330 rounds, never gap simultaneously |
| Auto-renewal | `workflow_dispatch` next cycle on completion |
| Mutual guard | Check sibling every minute, trigger guard if dead |
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
| Both dead | Manual trigger any tick 🔄 |

## Files

```
.github/workflows/
├── tick-a.yml    Timer A (300 rounds ≈ 5h)
├── tick-b.yml    Timer B (330 rounds ≈ 5.5h)
├── exec.yml      Business executor
└── guard.yml     Guardian

scripts/
├── tick.py       Timer + atomic lock (46 lines)
└── guard.py      Guardian logic (8 lines)
```

## Startup

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

Or `git push main` to auto-start both chains.

## License

[MIT](LICENSE)
