# Schedule

[English](README_en.md) | [繁體中文](README_zh-TW.md)

🎯 精准自调度系统 — 三链驻留 + 单例执行器 + 守护者，绕过 GitHub cron 节流限制。

## ❌ 问题

GitHub Actions 的 cron 调度存在严重节流：设定每 5 分钟执行，实际间隔可达 50+ 分钟。

## ✅ 方案

三条 tick 链在 VM 内以 for 循环驻留（每轮 5 小时），对齐整分钟精准触发单例业务执行器。

## 🏗️ 架构

```
tick-a (for循环, 驻留5h, 负责 min%3==0) ──┐
tick-b (for循环, 驻留5h, 负责 min%3==1) ──┼── 每分钟恰好一个触发 ──→ exec.yml (单例)
tick-c (for循环, 驻留5h, 负责 min%3==2) ──┘                              │
         ▲                                                               ▼
    guard.yml (单例唤醒者)                                        触发外部仓库
```

## ⏱️ 时序

| 分钟 | :00 | :01 | :02 | :03 | :04 | :05 | :06 | :07 | :08 |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| tick-a | 🎯 | | | 🎯 | | | 🎯 | | |
| tick-b | | 🎯 | | | 🎯 | | | 🎯 | |
| tick-c | | | 🎯 | | | 🎯 | | | 🎯 |
| exec | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> 每分钟恰好一条 tick 触发 exec，零重复，零遗漏

## 🔧 核心机制

### 精准对齐

```python
time.sleep(60 - time.time() % 60)  # 对齐到整分钟边界
```

### 三重去重

| 层级 | 机制 | 说明 |
|------|------|------|
| 1️⃣ | `min%3 == offset` | 每分钟只有一条 tick 有权触发 |
| 2️⃣ | `alive("exec.yml")` | 触发前检查 exec 是否已在运行 |
| 3️⃣ | `concurrency: exec` | 万一双触发，平台级保证只跑一个 |

### 新实例自毁

| 层级 | 机制 | 说明 |
|------|------|------|
| 🅰️ | `cancel-in-progress: true` | 平台级：新 run 取消旧 run |
| 🅱️ | `check_newer()` 每轮检测 | 代码级：检测到更新 run_id 则 `sys.exit` |

### 互守护

```
tick-a 发现 tick-b 死了 ──→ 触发 guard.yml
tick-c 发现 tick-b 死了 ──→ 触发 guard.yml ──→ 被 cancel-in-progress 丢弃
guard 单例运行 ──→ 检查所有 tick ──→ 交错唤起死掉的链
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
