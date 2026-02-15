# Schedule

[English](README_en.md) | [繁體中文](README_zh-TW.md)

> **基于 GitHub Actions 的轻量调度器，支持 crontab + 秒级语法，单文件零依赖。**

## 目录

- [特性](#-特性) · [使用](#-使用) · [启动](#-启动)
- [原子锁](#-原子锁) · [高可用](#-高可用)
- [文件](#-文件) · [核心函数](#-核心函数) · [测试](#-测试)

---

## ✨ 特性

| | |
|---|---|
| ⏱️ **秒级精度** | `time.sleep(max(0.1, INTERVAL - time.time() % INTERVAL))` 对齐 30 秒边界 |
| 🔒 **原子去重** | Git Ref 创建天然原子，双链竞态只有 1 次执行 |
| 🛡️ **持续可用** | 自续期 + 互守护 + 错开空窗，无人值守 |
| 📦 **极简代码** | 单文件 tick.py，零外部依赖 |
| 🧪 **完备测试** | 257 个单元测试 + 24 小时快进模拟验证 |

## 📋 使用

> 唯一配置：Secret `DISPATCH`，每行一条，支持注释和空行。cron 使用 UTC 时区。

```
# crontab 5 字段 — 分 时 日 月 周  仓库  工作流
*/5 * * * *  owner/repo  check.yml     # 每 5 分钟
0   8 * * *  owner/repo  daily.yml     # 每天 08:00
0   9 * * 1  owner/repo  weekly.yml    # 每周一 09:00

# 秒级语法 — @Ns  仓库  工作流
@30s         owner/repo  poll.yml      # 每 30 秒
```

字段语法：`*` 任意 · `*/5` 步进 · `0,30` 枚举 · `1-5` 范围

`TZ_OFFSET` 环境变量控制日志时间显示，默认 `0` (UTC)，设为 `8` 显示北京时间。

## 🚀 启动

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

或 `git push main` 自动启动双链。

## 🔒 原子锁

每轮两条 tick 同时尝试创建同名 Git Ref，GitHub 服务端保证只有一个成功：

```
tick-a: POST /git/refs → 201 Created  ✅ 获锁 → 触发目标
tick-b: POST /git/refs → 422 Conflict ❌ 已存在 → 跳过
```

| 特性 | 说明 |
|------|------|
| 原子性 | 同名 ref 不可能被创建两次 |
| 无竞态 | 不依赖状态查询，无 API 延迟窗口 |
| 自清理 | 旧 lock tag 每轮自动删除 |

| 场景 | 结果 |
|------|------|
| 双链存活 | 2 竞争锁 → 执行 1 次 ✅ |
| 单链存活 | 1 直接获锁 → 执行 1 次 ✅ |
| 全灭 | `git push main` 或手动触发任意 tick 🔄 |

## �️ 高可用

| 机制 | 说明 |
|------|------|
| 错开续期 | tick-a 600 轮 / tick-b 660 轮，永不同时空窗 |
| 自动续期 | 轮次结束自动 `workflow_dispatch` 下一轮 |
| 互相守护 | 每轮 (30s) 检查兄弟存活，死亡则直接重启 |
| 新版退出 | `cancel-in-progress` + run_id 检测，新代码推送秒切换 |

| 小时 | 0 | 5 | 5.5 | 10 | 10.5 |
|------|---|---|-----|-----|------|
| tick-a | 🟢 运行 | 🔄 续期 | 🟢 运行 | 🟢 运行 | 🔄 续期 |
| tick-b | 🟢 运行 | 🟢 运行 | 🔄 续期 | 🟢 运行 | 🟢 运行 |

> 至少有 1 条链在线

## �📁 文件

```
.github/workflows/
├── tick-a.yml          定时器 A (600 轮 ≈ 5h)
└── tick-b.yml          定时器 B (660 轮 ≈ 5.5h)

tick.py                 定时器 + 原子锁 + 调度器
test_tick.py            单元测试 (257 用例, 含快进模拟)
AGENTS.md               AI 编码准则
.env                    本地任务配置 (与 Secret DISPATCH 同步)
.gitignore              排除 .env
```

## ⚙️ 核心函数

> 命名规则：`动词_名词`，谓词用 `is_` 前缀

| 分类 | 函数 | 职责 |
|------|------|------|
| 工具 | `gh` | 执行 gh CLI 命令 |
| | `gh_api` | 调用 GitHub API (GET) |
| 解析 | `match_field` | 单个 cron 字段匹配 (`*`, `*/N`, 逗号, 范围) |
| | `match_cron` | 5 字段 cron 表达式匹配，含日/月偏移修正 |
| | `parse_dispatch` | 解析 DISPATCH secret，支持注释和空行 |
| 判断 | `is_expired` | 锁过期判断 (cron/秒级/旧格式兼容) |
| | `is_alive` | 检查 workflow 是否正在运行 |
| 调度 | `scan_round` | 扫描本轮匹配的任务 (纯函数，无 I/O) |
| | `execute_task` | 竞锁 + 触发 + 日志 |
| | `trigger_workflow` | 使用 PAT 跨仓库触发 workflow |
| 锁 | `acquire_lock` | 创建 Git Ref 获取分布式锁 |
| | `sanitize_key` | cron 表达式 → 合法 ref 名称 |
| 维护 | `clean_locks` / `clean_runs` | 清理过期锁 / 已完成的 run |
| | `check_update` | 检测更新版本，有则退出让位 |
| | `guard_peer` | 检查兄弟存活，死亡则重启 |
| | `renew_self` | 轮次结束后自动续期 |

## 🧪 测试

> 覆盖：纯函数验证、锁过期判断、端到端 DISPATCH 解析、24 小时快进调度模拟。

```bash
python3 test_tick.py
```

## 📄 授权

[MIT](LICENSE)
