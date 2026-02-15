# Schedule

[简体中文](README.md) | [English](README_en.md)

> **基於 GitHub Actions 的輕量調度器，支援 crontab + 秒級語法，單檔案零依賴。**

## 目錄

- [特性](#-特性) · [使用](#-使用) · [啟動](#-啟動)
- [原子鎖](#-原子鎖) · [高可用](#-高可用)
- [檔案](#-檔案) · [函數](#-函數) · [測試](#-測試)

---

## ✨ 特性

| | |
|---|---|
| ⏱️ **秒級精度** | `time.sleep(max(0.1, INTERVAL - time.time() % INTERVAL))` 對齊 10 秒邊界 |
| 🔒 **原子去重** | Git Ref 創建天然原子，雙鏈競態只有 1 次執行 |
| 🛡️ **持續可用** | 自續期 + 互守護 + 錯開空窗，無人值守 |
| 📦 **極簡程式碼** | 單檔案 tick.py，零外部依賴 |
| 🧪 **完備測試** | 305 個單元測試 + 24 小時快進模擬驗證 |

## 📋 使用

> 唯一配置：Secret `DISPATCH`，每行一條，支援註釋和空行。cron 使用 UTC 時區。

```
# crontab 5 字段 — 分 時 日 月 週  倉庫  工作流
*/5 * * * *  owner/repo  check.yml     # 每 5 分鐘
0   8 * * *  owner/repo  daily.yml     # 每天 08:00
0   9 * * 1  owner/repo  weekly.yml    # 每週一 09:00

# 秒級語法 — @Ns  倉庫  工作流
@10s         owner/repo  poll.yml      # 每 10 秒
```

字段語法：`*` 任意 · `*/5` 步進 · `0,30` 列舉 · `1-5` 範圍。秒級最小間隔 `10s`（= 掃描週期）。

`TZ_OFFSET` 環境變數控制日誌時間顯示，預設 `0` (UTC)，設為 `8` 顯示北京時間。

## 🚀 啟動

```bash
gh workflow run guard.yml
```

guard 自動檢測並拉起未運行的 tick。也可 `git push main` 啟動。

## 🔒 原子鎖

每輪兩條 tick 同時嘗試創建同名 Git Ref，GitHub 伺服端保證只有一個成功：

```
tick-a: POST /git/refs → 201 Created  ✅ 獲鎖 → 觸發目標
tick-b: POST /git/refs → 422 Conflict ❌ 已存在 → 跳過
```

| 特性 | 說明 |
|------|------|
| 原子性 | 同名 ref 不可能被創建兩次 |
| 無競態 | 不依賴狀態查詢，無 API 延遲窗口 |
| 自清理 | 舊 lock tag 每輪自動刪除 |

| 場景 | 結果 |
|------|------|
| 雙鏈存活 | 2 競爭鎖 → 執行 1 次 ✅ |
| 單鏈存活 | 1 直接獲鎖 → 執行 1 次 ✅ |
| 全滅 | `git push main` 或手動觸發任意 tick 🔄 |

## 🛡️ 高可用

| 機制 | 說明 |
|------|------|
| 錯開運行 | tick-a 5h / tick-b 5.5h，永不同時空窗 |
| 自動守護 | `if: always()` 觸發 guard.yml，檢測並拉起死鏈 |
| 崩潰自救 | Python 崩潰、逾時、正常結束均觸發守護 |
| 新版退出 | `cancel-in-progress` + run_id 偵測，新程式碼推送秒切換 |

| 小時 | 0 | 5 | 5.5 | 10 | 10.5 |
|------|---|---|-----|-----|------|
| tick-a | 🟢 運行 | 🔄 續期 | 🟢 運行 | 🟢 運行 | 🔄 續期 |
| tick-b | 🟢 運行 | 🟢 運行 | 🔄 續期 | 🟢 運行 | 🟢 運行 |

> 至少有 1 條鏈在線

## 📁 檔案

```
.github/workflows/
├── tick-a.yml          定時器 A (5h)
├── tick-b.yml          定時器 B (5.5h)
└── guard.yml           守護: 檢測並拉起死鏈

tick.py                 定時器 + 原子鎖 + 調度器
test_tick.py            單元測試 (305 用例, 含快進模擬)
AGENTS.md               AI 編碼準則
.env                    本地任務配置 (與 Secret DISPATCH 同步)
.gitignore              排除 .env
```

## ⚙️ 函數

> 命名規則：`動詞_名詞`，謂詞用 `is_` 前綴

| 分類 | 函數 | 職責 |
|------|------|------|
| 工具 | `gh` | 執行 gh CLI 命令 |
| | `gh_api` | 調用 GitHub API (GET) |
| 解析 | `match_field` | 單個 cron 字段匹配 (`*`, `*/N`, 逗號, 範圍) |
| | `match_cron` | 5 字段 cron 表達式匹配，含日/月偏移修正 |
| | `parse_dispatch` | 解析 DISPATCH secret，支援註釋和空行 |
| 判斷 | `is_expired` | 鎖過期判斷 (cron/秒級/舊格式兼容) |
| 調度 | `scan_round` | 掃描本輪匹配的任務 (純函數，無 I/O) |
| | `execute_task` | 競鎖 + 觸發 + 日誌 |
| | `trigger_workflow` | 使用 PAT 跨倉庫觸發 workflow |
| 鎖 | `acquire_lock` | 創建 Git Ref 獲取分散式鎖 |
| | `sanitize_key` | cron 表達式 → 合法 ref 名稱 |
| 維護 | `clean_locks` / `clean_runs` | 清理過期鎖 / 已完成的 run |
| | `check_update` | 檢測更新版本，有則退出讓位 |

## 🧪 測試

> 覆蓋：純函數驗證、鎖過期判斷、端到端 DISPATCH 解析、24 小時快進調度模擬。

```bash
python3 test_tick.py
```

## 📄 授權

[MIT](LICENSE)
