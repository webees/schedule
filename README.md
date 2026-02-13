# Schedule

精准自调度系统 — 三链驻留 + 单例执行器 + 守护者。

## 问题

GitHub cron 调度有严重节流：设定 5 分钟，实际 50+ 分钟。

## 方案

三条 tick 链在 VM 内驻留循环 (5h/轮), 对齐整分钟精准触发单例业务执行器。

## 架构

```
tick-a (for循环, 驻留5h, 负责 min%3==0) ──┐
tick-b (for循环, 驻留5h, 负责 min%3==1) ──┼── 每分钟恰好一个触发 ──→ exec.yml (单例)
tick-c (for循环, 驻留5h, 负责 min%3==2) ──┘                              │
         ▲                                                               ▼
    guard.yml (单例唤醒者)                                        触发外部仓库
```

## 时序

```
分钟:  :00   :01   :02   :03   :04   :05   :06
tick-a: 🎯                 🎯                 🎯      ← min%3==0
tick-b:       🎯                 🎯                    ← min%3==1
tick-c:             🎯                 🎯              ← min%3==2
exec:   █    █    █    █    █    █    █               ← 每分钟一次, 单例
```

## 去重机制

```
1. 分钟分配: 每分钟只有一条 tick 有权触发 (min%3 == offset)
2. 状态检查: tick 触发前检查 exec 是否 in_progress/queued → 跳过
3. concurrency: exec.yml group=exec, 万一双触发也只跑一个
```

## 文件

| 文件 | 作用 | 生命周期 |
|------|------|---------|
| `tick-a/b/c.yml` | 定时器 (for 循环驻留) | ~5h/轮, 自动续期 |
| `exec.yml` | 业务执行器 (单例) | 每次触发 ~30s |
| `guard.yml` | 守护者 (唤醒死掉的 tick) | 按需 |

## 启动

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml && sleep 60 && gh workflow run tick-c.yml
```

## 全灭恢复

手动触发任意一条 tick → 守护机制自动唤起其他链。

## 资源消耗

| 组件 | VM 启动次数/天 | 总分钟/天 |
|------|--------------|----------|
| tick-a/b/c (各) | ~5 次 | ~1440 min (24h 驻留) |
| exec | ~1440 次 | ~720 min (每次 ~30s) |
| guard | 偶尔 | ~0 |
| **总计** | | **~5,040 min** |

公开仓库无限制, 零费用。
