# Schedule

[English](README_en.md) | [繁體中文](README_zh-TW.md)

🎯 精准自调度系统 — 三链驻留 + 单例执行器 + 守护者，绕过 GitHub cron 节流限制。

## ❌ 问题

GitHub Actions 的 cron 调度存在严重节流：设定每 5 分钟执行，实际间隔可达 50+ 分钟。

## ✅ 方案

三条 tick 链在 VM 内以 for 循环驻留（每轮 5 小时），对齐整分钟精准触发单例业务执行器。

## 🏗️ 架构

```
tick-a (for循环, 驻留5h) ──┐
tick-b (for循环, 驻留5h) ──┼── 每分钟全部尝试触发 ──→ exec.yml (单例)
tick-c (for循环, 驻留5h) ──┘                              │
         ▲                                                ▼
    guard.yml (单例唤醒者)                         触发外部仓库
```

## ⏱️ 时序

| 分钟 | :00 | :01 | :02 | :03 | :04 | :05 |
|------|-----|-----|-----|-----|-----|-----|
| tick-a | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 |
| tick-b | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 |
| tick-c | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 | 🎯 |
| exec | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> 三条 tick 都尝试触发，去重机制保证 exec 每分钟只执行一次

## 🔧 核心机制

### 去重 — exec 始终只有一个在跑

| 层级 | 机制 | 说明 |
|------|------|------|
| 1️⃣ | `alive("exec.yml")` | 代码级：exec 在运行就跳过触发 |
| 2️⃣ | `concurrency: exec` | 平台级：万一同时触发也只跑一个 |

### 新实例自毁 — 代码更新后旧链秒退

| 层级 | 机制 | 说明 |
|------|------|------|
| 🅰️ | `cancel-in-progress: true` | 平台级：新 run 取消旧 run |
| 🅱️ | `check_newer()` 每轮检测 | 代码级：检测到更新 run_id 则 `sys.exit` |

### 🛡️ 互守护 — guard.yml 自动唤醒死掉的链

每条 tick 在 5 小时循环结束后，会检查兄弟链是否存活：

```
tick-a 循环结束 → 检查 tick-b, tick-c 状态
  ├── 全部存活 → 无操作
  └── 发现 tick-b 死了 → 触发 guard.yml
                              │
                              ▼
                    guard.yml (concurrency: cancel-in-progress)
                    ├── 检查 tick-a → ✅ 存活, 跳过
                    ├── 检查 tick-b → 🚨 已停止, 唤醒, sleep 60s
                    └── 检查 tick-c → ✅ 存活, 跳过
```

**guard.yml 特性：**
- `cancel-in-progress: true` — 多条 tick 同时触发 guard 时只执行一次
- 交错唤醒 — 每唤起一条链后 sleep 60s，避免同时启动

### 容错 — 任意一条活着就不遗漏

```
3 条存活: 3 个尝试触发, exec 跑 1 次 ✅
2 条存活: 2 个尝试触发, exec 跑 1 次 ✅
1 条存活: 1 个尝试触发, exec 跑 1 次 ✅
0 条存活: 全灭, 手动恢复任意一条     🔄
```

## 📁 文件结构

```
.github/workflows/
├── tick-a.yml        ⏱️ 定时器 A (仅 name 不同)
├── tick-b.yml        ⏱️ 定时器 B
├── tick-c.yml        ⏱️ 定时器 C
├── exec.yml          🚀 业务执行器 (单例)
└── guard.yml         🛡️ 守护者 (单例)

scripts/
├── tick.py           ⏱️ 定时器逻辑 (~50 行, abc 共用)
└── guard.py          🛡️ 守护逻辑 (~20 行)
```

## 🚀 启动

```bash
gh workflow run tick-a.yml
sleep 60
gh workflow run tick-b.yml
sleep 60
gh workflow run tick-c.yml
```

或直接 `git push` 到 main — 三条链自动启动，旧链自动销毁。

## 🔄 全灭恢复

手动触发任意一条 tick → 守护机制自动唤起其他链。

## 📄 授权

[MIT](LICENSE)
