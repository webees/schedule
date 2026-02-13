# Schedule

[简体中文](README.md) | [繁體中文](README_zh-TW.md)

Precise self-scheduling system — three resident chains + singleton executor + guardian, bypassing GitHub cron throttling.

## Problem

GitHub Actions cron scheduling has severe throttling: a 5-minute interval can actually become 50+ minutes.

## Solution

Three tick chains reside in VMs via for-loops (~5h per cycle), aligning to exact minute boundaries to trigger a singleton business executor.

## Architecture

```
tick-a (for loop, 5h, min%3==0) ---+
tick-b (for loop, 5h, min%3==1) ---+--> exec.yml (singleton) --> external repo
tick-c (for loop, 5h, min%3==2) ---+
  ^                                         |
  +---- guard.yml (singleton reviver) <-----+
```

## Timing

```
min   :00  :01  :02  :03  :04  :05  :06  :07  :08
 a     *              *              *
 b          *              *              *
 c               *              *              *
exec  [=]  [=]  [=]  [=]  [=]  [=]  [=]  [=]  [=]
```

> `*` = tick triggers exec, `[=]` = exec runs, exactly once per minute

## Core Mechanisms

**Minute-aligned precision** — each loop iteration sleeps to the next whole minute

```python
time.sleep(60 - time.time() % 60)
```

**Triple deduplication** — ensures exec is never triggered twice

```
1. min%3 == offset    only one tick may trigger per minute
2. alive("exec.yml")  check exec status before triggering
3. concurrency: exec  platform-level guarantee of single instance
```

**Self-destroy on update** — old chains exit when new code is pushed

```
cancel-in-progress: true   platform: new run cancels old run
check_newer() per loop     code: detect newer run_id then sys.exit
```

**Mutual guardianship** — revive dead sibling chains

```
tick-a detects tick-b dead --> trigger guard.yml (singleton)
tick-c detects tick-b dead --> trigger guard.yml (dropped by cancel-in-progress)
guard runs once --> revives tick-b
```

## Files

```
.github/workflows/
  tick-a.yml        timer A (only name differs)
  tick-b.yml        timer B
  tick-c.yml        timer C
  exec.yml          executor (singleton)
  guard.yml         guardian (singleton)

scripts/
  tick.py           timer logic (~50 lines, shared by a/b/c)
  guard.py          guardian logic (~20 lines)
```

## Startup

```bash
gh workflow run tick-a.yml
sleep 60
gh workflow run tick-b.yml
sleep 60
gh workflow run tick-c.yml
```

Or just `git push` to main — all three chains start automatically.

## Full Recovery

Manually trigger any single tick — the guardian mechanism automatically revives the others.

## License

MIT
