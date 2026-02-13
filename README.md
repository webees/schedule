# Schedule

[English](README_en.md) | [繁體中文](README_zh-TW.md)

> **让 GitHub Actions 每分钟精确执行一次，突破 cron 5 分钟最小间隔与节流延迟。**

## ✨ 亮点

| | |
|---|---|
| ⏱️ **分钟级精度** | `time.sleep(60 - time.time() % 60)` 对齐整分钟边界 |
| 🔒 **原子级去重** | Git Ref 创建天然原子，双链竞态只有 1 个 exec |
| 🛡️ **7×24 自愈** | 自续期 + 互守护 + 错开空窗，无人值守 |
| 📦 **极简代码** | tick.py 46 行 + guard.py 8 行，零外部依赖 |

---

## 架构

```
tick-a (for 循环, 驻留 5h) ──┐
                             ├── Git Ref 原子锁 ──→ exec.yml ──→ 外部仓库
tick-b (for 循环, 驻留 5.5h) ┘
         ↕ 互守护
    guard.yml
```

## 原子锁

每分钟两条 tick 同时尝试创建同名 Git Ref，GitHub 服务端保证只有一个成功：

```
tick-a: POST /git/refs → 201 Created  ✅ 获锁 → 触发 exec
tick-b: POST /git/refs → 422 Conflict ❌ 已存在 → 跳过
```

| 特性 | 说明 |
|------|------|
| 原子性 | 同名 ref 不可能被创建两次 |
| 无竞态 | 不依赖状态查询，无 API 延迟窗口 |
| 自清理 | 旧 lock tag 每 30 轮自动删除 |

## 自愈

| 机制 | 说明 |
|------|------|
| 错开续期 | tick-a 300 轮 / tick-b 330 轮，永不同时空窗 |
| 自续期 | 轮次结束自动 `workflow_dispatch` 下一轮 |
| 互守护 | 每 5 分钟检查兄弟存活，死亡则触发 guard 唤醒 |
| 自毁 | `cancel-in-progress` + run_id 检测，新代码推送秒切换 |

| 小时 | 0 | 5 | 5.5 | 10 | 10.5 |
|------|---|---|-----|----|----- |
| tick-a | 🟢 运行 | 🔄 续期 | 🟢 运行 | 🟢 运行 | 🔄 续期 |
| tick-b | 🟢 运行 | 🟢 运行 | 🔄 续期 | 🟢 运行 | 🟢 运行 |

> 至少有 1 条链在线

## 容错

| 场景 | 结果 |
|------|------|
| 双链存活 | 2 竞争锁 → exec 1 次 ✅ |
| 单链存活 | 1 直接获锁 → exec 1 次 ✅ |
| 全灭 | 手动触发任意 tick 🔄 |

## 文件

```
.github/workflows/
├── tick-a.yml    定时器 A (300 轮 ≈ 5h)
├── tick-b.yml    定时器 B (330 轮 ≈ 5.5h)
├── exec.yml      业务执行器
└── guard.yml     守护者

scripts/
├── tick.py       定时器 + 原子锁 (46 行)
└── guard.py      守护逻辑 (8 行)
```

## 启动

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

或 `git push main` 自动启动双链。

## 授权

[MIT](LICENSE)
