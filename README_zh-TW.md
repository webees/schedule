# Schedule

[简体中文](README.md) | [English](README_en.md)

> **讓 GitHub Actions 每 30 秒精確執行一次，突破 cron 5 分鐘最小間隔與節流延遲。**

## 目錄

- [亮點](#-亮點) · [使用](#-使用) · [啟動](#-啟動)
- [原子鎖](#-原子鎖) · [自癒](#-自癒) · [容錯](#-容錯)
- [檔案](#-檔案) · [核心函數](#-核心函數) · [測試](#-測試)

---

## ✨ 亮點

| | |
|---|---|
| ⏱️ **秒級精度** | `time.sleep(max(0.1, INTERVAL - time.time() % INTERVAL))` 對齊 30 秒邊界 |
| 🔒 **原子級去重** | Git Ref 創建天然原子，雙鏈競態只有 1 次執行 |
| 🛡️ **7×24 自癒** | 自續期 + 互守護 + 錯開空窗，無人值守 |
| 📦 **極簡程式碼** | 單檔案 tick.py，零外部依賴 |
| 🧪 **完備測試** | 257 個單元測試 + 24 小時快進模擬驗證 |

## 📋 使用

唯一配置：Secret `DISPATCH`，每行一條，支援註釋 (`#`) 和空行。

**crontab 5 字段** (最小粒度 1 分鐘)：

```
分 時 日 月 週  倉庫  工作流
```

**秒級語法** (任意間隔)：

```
@Ns  倉庫  工作流
```

字段語法同 crontab：`*` 任意 / `*/5` 每 5 / `0,30` 指定 / `1-5` 範圍

示例：

```
# 每 5 分鐘檢查
*/5 * * * *  owner/repo  check.yml

# 每天 08:00 (UTC) 日報
0   8 * * *  owner/repo  daily.yml

# 每 30 秒輪詢
@30s         owner/repo  poll.yml
```

> **添加任務只改 Secret，不改任何程式碼。cron 表達式始終使用 UTC 時區。**

**日誌時區**：`TZ_OFFSET` 環境變數控制日誌中的時間顯示，預設 `0` (UTC)，設為 `8` 則顯示北京時間。

## 🚀 啟動

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

或 `git push main` 自動啟動雙鏈。

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

## 🛡️ 自癒

| 機制 | 說明 |
|------|------|
| 錯開續期 | tick-a 600 輪 / tick-b 660 輪，永不同時空窗 |
| 自續期 | 輪次結束自動 `workflow_dispatch` 下一輪 |
| 互守護 | 每輪 (30s) 檢查兄弟存活，死亡則直接重啟 |
| 自毀 | `cancel-in-progress` + run_id 偵測，新程式碼推送秒切換 |

| 小時 | 0 | 5 | 5.5 | 10 | 10.5 |
|------|---|---|-----|-----|------|
| tick-a | 🟢 運行 | 🔄 續期 | 🟢 運行 | 🟢 運行 | 🔄 續期 |
| tick-b | 🟢 運行 | 🟢 運行 | 🔄 續期 | 🟢 運行 | 🟢 運行 |

> 至少有 1 條鏈在線

## 🔄 容錯

| 場景 | 結果 |
|------|------|
| 雙鏈存活 | 2 競爭鎖 → 執行 1 次 ✅ |
| 單鏈存活 | 1 直接獲鎖 → 執行 1 次 ✅ |
| 全滅 | `git push main` 或手動觸發任意 tick 🔄 |

## 📁 檔案

```
.github/workflows/
├── tick-a.yml          定時器 A (600 輪 ≈ 5h)
└── tick-b.yml          定時器 B (660 輪 ≈ 5.5h)

tick.py                 定時器 + 原子鎖 + 調度器
test_tick.py            單元測試 (257 用例, 含快進模擬)
AGENTS.md               AI 編碼準則
.env                    本地任務配置 (與 Secret DISPATCH 同步)
.gitignore              排除 .env
```

## ⚙️ 核心函數

> 命名規則：`動詞_名詞`，謂詞用 `is_` 前綴

**工具**

| 函數 | 職責 |
|------|------|
| `gh` | 執行 gh CLI 命令 |
| `gh_api` | 調用 GitHub API (GET) |

**解析**

| 函數 | 職責 |
|------|------|
| `match_field` | 單個 cron 字段匹配 (`*`, `*/N`, 逗號, 範圍) |
| `match_cron` | 5 字段 cron 表達式匹配，含日/月偏移修正 |
| `parse_dispatch` | 解析 DISPATCH secret，支援註釋和空行 |

**判斷**

| 函數 | 職責 |
|------|------|
| `is_expired` | 鎖過期判斷 (cron/秒級/舊格式兼容) |
| `is_alive` | 檢查 workflow 是否正在運行 |

**調度**

| 函數 | 職責 |
|------|------|
| `scan_round` | 掃描本輪匹配的任務 (純函數，無 I/O) |
| `execute_task` | 競鎖 + 觸發 + 日誌 |
| `trigger_workflow` | 使用 PAT 跨倉庫觸發 workflow |

**鎖**

| 函數 | 職責 |
|------|------|
| `acquire_lock` | 創建 Git Ref 獲取分散式鎖 |
| `sanitize_key` | cron 表達式 → 合法 ref 名稱 |

**維護**

| 函數 | 職責 |
|------|------|
| `clean_locks` / `clean_runs` | 清理過期鎖 / 已完成的 run |
| `check_update` | 檢測更新版本，有則退出讓位 |
| `guard_peer` | 檢查兄弟存活，死亡則重啟 |
| `renew_self` | 輪次結束後自動續期 |

## 🧪 測試

```bash
python3 test_tick.py
```

覆蓋：純函數驗證、鎖過期判斷、端到端 DISPATCH 解析、24 小時快進調度模擬。

## 📄 授權

[MIT](LICENSE)
