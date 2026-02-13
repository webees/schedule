# Schedule

精准自调度系统 — 三链互守 + 单例唤醒者，绕过 GitHub cron 节流限制。

## 问题

GitHub cron 调度对计划任务有严重节流：设定 5 分钟，实际 50+ 分钟。

## 方案

三条独立自调度链 + 一个唤醒者，互为守护进程。

### 架构

```
tick-a ──sleep 180s──→ 触发自己 ──→ 检测 b/c 存活 ──→ 死? → revive
tick-b ──sleep 180s──→ 触发自己 ──→ 检测 a/c 存活 ──→ 死? → revive
tick-c ──sleep 180s──→ 触发自己 ──→ 检测 a/b 存活 ──→ 死? → revive
                                                           ↓
                                                    guard.yml (单例)
                                                    ├── 检测 a/b/c
                                                    └── 交错唤起死掉的链 (间隔 60s)
```

### 时序图

```
时间:  0s     60s    120s   180s   240s   300s   360s
tick-a: ██████████████████░░░░░░██████████████████░░░░░░██
tick-b: ░░░░░░██████████████████████░░░░░░██████████████████
tick-c: ░░░░░░░░░░░░██████████████████░░░░░░░░░░░░██████████

等效: 每 ~60 秒有一个 tick 触发
```

### 防竞态设计

```
旧 (有竞态):
  tick-a 发现 b 死 → 直接触发 b
  tick-c 发现 b 死 → 也触发 b   ← 重复!

新 (无竞态):
  tick-a 发现 b 死 → 触发 revive
  tick-c 发现 b 死 → 触发 revive ← 被 cancel-in-progress 丢弃
  revive 单例运行 → 唤起 b      ← 无竞态
```

### 防雪崩设计

```
自调度前检查:
  已有排队的 run? → 跳过自触发 (防止 queue 堆积)
```

## 文件说明

| 文件 | 作用 | concurrency |
|------|------|-------------|
| `tick-a.yml` | 自调度链 A, 守护 B/C | `tick-a`, 不取消 |
| `tick-b.yml` | 自调度链 B, 守护 A/C | `tick-b`, 不取消 |
| `tick-c.yml` | 自调度链 C, 守护 A/B | `tick-c`, 不取消 |
| `guard.yml` | 单例唤醒者 | `revive`, 取消重复 |

## 启动

交错 60 秒手动触发三条链:

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml && sleep 60 && gh workflow run tick-c.yml
```

## 全灭恢复

极端情况 (GitHub 平台故障) 导致三链同时断裂时，手动触发任意一条链即可恢复全部 (守护机制自动唤起其他链)。

## 适用场景

为私有仓库提供精准定时触发:

```
public/schedule (本仓库)          private/k3s (目标仓库)
┌───────────────┐                ┌──────────────────┐
│ tick-a/b/c    │── dispatch ──→ │ 🤖 巡检 (self-hosted) │
│ 每 ~60s 一次  │                │ 零计费              │
└───────────────┘                └──────────────────┘
```

需要 Personal Access Token (PAT) 实现跨仓库触发。
