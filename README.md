# Schedule

[English](README_en.md) | [繁體中文](README_zh-TW.md)

精准自调度系统 — 三链驻留 + 单例执行器 + 守护者，绕过 GitHub cron 节流限制。

## 问题

GitHub Actions 的 cron 调度存在严重节流：设定每 5 分钟执行，实际间隔可达 50+ 分钟。

## 方案

三条 tick 链在 VM 内以 for 循环驻留（每轮 5 小时），对齐整分钟精准触发单例业务执行器。

## 架构

```
tick-a (for loop, 5h, min%3==0) ---+
tick-b (for loop, 5h, min%3==1) ---+--> exec.yml (singleton) --> external repo
tick-c (for loop, 5h, min%3==2) ---+
  ^                                         |
  +---- guard.yml (singleton reviver) <-----+
```

## 时序

```
min   :00  :01  :02  :03  :04  :05  :06  :07  :08
 a     *              *              *
 b          *              *              *
 c               *              *              *
exec  [=]  [=]  [=]  [=]  [=]  [=]  [=]  [=]  [=]
```

> `*` = tick 触发 exec, `[=]` = exec 执行, 每分钟恰好一次

## 核心机制

**精准对齐** — 每轮循环 sleep 到整分钟边界

```python
time.sleep(60 - time.time() % 60)
```

**三重去重** — 确保 exec 不被重复触发

```
1. min%3 == offset    每分钟只有一条 tick 有权触发
2. alive("exec.yml")  触发前检查 exec 是否已在运行
3. concurrency: exec  万一双触发, 平台级保证只跑一个
```

**新实例自毁** — 代码更新后旧链自动退出

```
cancel-in-progress: true   平台级: 新 run 取消旧 run
check_newer() per loop     代码级: 检测到更新 run_id 则 sys.exit
```

**互守护** — 兄弟链死亡时触发 guard 唤醒

```
tick-a detects tick-b dead --> trigger guard.yml (singleton)
tick-c detects tick-b dead --> trigger guard.yml (dropped by cancel-in-progress)
guard runs once --> revives tick-b
```

## 文件结构

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

## 启动

```bash
gh workflow run tick-a.yml
sleep 60
gh workflow run tick-b.yml
sleep 60
gh workflow run tick-c.yml
```

或直接 `git push` 到 main 分支 — 三条链自动启动。

## 全灭恢复

手动触发任意一条 tick，守护机制自动唤起其他链。

## 授权

MIT
