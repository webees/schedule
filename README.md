# Schedule

[English](README_en.md) | [繁體中文](README_zh-TW.md)

> 🎯 **让 GitHub Actions 每分钟精确触发一次。**

## ✨ 亮点

- ⏱️ **分钟级精度** — 突破 GitHub cron 5 分钟最小间隔 + 节流延迟
- 🔒 **Git Ref 原子锁** — 双链竞态触发，服务端保证只有 1 个 exec 执行
- 🛡️ **自愈架构** — 互守护 + 自续期，7×24 无人值守
- 📦 **极简实现** — 2 个 Python 脚本 (56 + 20 行)，零外部依赖

## ❌ 问题

GitHub Actions cron 最小间隔 5 分钟，实际调度延迟可达 **50+ 分钟**。

## ✅ 方案

双 tick 链在 VM 内以 for 循环驻留 5 小时，每分钟对齐整点，通过 **Git Ref 原子锁** 竞争触发单例执行器。

## 🏗️ 架构

```
tick-a (for循环, 驻留5h) ──┐
                           ├── 原子锁竞争 ──→ exec.yml (单例) ──→ 外部仓库
tick-b (for循环, 驻留5h) ──┘
         ↕ 互守护
    guard.yml (唤醒者)
```

## ⏱️ 时序

| 分钟 | :00 | :01 | :02 | :03 | :04 | :05 |
|------|-----|-----|-----|-----|-----|-----|
| tick-a | 🔒 尝试 | 🔒 尝试 | 🔒 尝试 | 🔒 尝试 | 🔒 尝试 | 🔒 尝试 |
| tick-b | 🔒 尝试 | 🔒 尝试 | 🔒 尝试 | 🔒 尝试 | 🔒 尝试 | 🔒 尝试 |
| 获锁者 | 🎯 a | 🎯 b | 🎯 a | 🎯 b | 🎯 a | 🎯 b |
| exec | ✅ 1次 | ✅ 1次 | ✅ 1次 | ✅ 1次 | ✅ 1次 | ✅ 1次 |

> 谁先抢到锁谁触发，**每分钟必定且仅有 1 次 exec**

## 🔧 核心机制

### 🔒 Git Ref 原子锁 — 精确一次的核心

```python
# 每分钟创建唯一 tag: refs/tags/lock/exec-202602140445
# GitHub API 保证: 同名 ref 只能创建一次

tick-a: POST /git/refs → 201 Created  ✅ 获锁 → 触发 exec
tick-b: POST /git/refs → 422 Conflict ❌ 已存在 → 跳过
```

| 特性 | 说明 |
|------|------|
| 原子性 | GitHub 服务端保证，不可能两个同时成功 |
| 无竞态 | 不依赖 `alive()` 检查，无 API 延迟问题 |
| 自清理 | 旧 lock tag 每 30 轮自动删除 |

### 🛡️ 自愈

| 机制 | 说明 |
|------|------|
| **错开续期** | tick-a=300 轮(5h)，tick-b=330 轮(5.5h)，永不同时空窗 |
| **自续期** | 轮次结束后自动触发下一轮 |
| **互守护** | tick 结束时检查兄弟，死亡则触发 guard 唤醒 |
| **新实例自毁** | `cancel-in-progress: true` + 代码级 run_id 检测 |

```
小时:  0        5     5.5      10    10.5
tick-a: |== 300轮 ==|续期|== 300轮 ==|续期...
tick-b: |=== 330轮 ===|续期|=== 330轮 ===|续期...
                   ↑ 永不同时到达续期空窗
```

### 容错

```
2 条存活: 2 个竞争锁, exec 跑 1 次 ✅
1 条存活: 1 个直接获锁, exec 跑 1 次 ✅
0 条存活: 手动触发任意一条 tick       🔄
```

## 📁 文件结构

```
.github/workflows/
├── tick-a.yml      ⏱️ 定时器 A (仅 name 不同)
├── tick-b.yml      ⏱️ 定时器 B
├── exec.yml        🚀 业务执行器 (单例)
└── guard.yml       🛡️ 守护者

scripts/
├── tick.py         ⏱️ 定时器 + 原子锁 (56 行)
└── guard.py        🛡️ 守护逻辑 (20 行)
```

## 🚀 启动

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

或直接 `git push` 到 main — 双链自动启动。

## 📄 授权

[MIT](LICENSE)
