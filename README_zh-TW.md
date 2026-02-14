# Schedule

[简体中文](README.md) | [English](README_en.md)

> **讓 GitHub Actions 每 30 秒精確執行一次，突破 cron 5 分鐘最小間隔與節流延遲。**

## ✨ 亮點

| | |
|---|---|
| ⏱️ **秒級精度** | `time.sleep(30 - time.time() % 30)` 對齊 30 秒邊界 |
| 🔒 **原子級去重** | Git Ref 創建天然原子，雙鏈競態只有 1 次執行 |
| 🛡️ **7×24 自癒** | 自續期 + 互守護 + 錯開空窗，無人值守 |
| 📦 **極簡程式碼** | 單檔案 tick.py，零外部依賴 |
| 🧪 **完備測試** | 257 個單元測試 + 24 小時快進模擬驗證 |

---

## 架構

```
tick-a (5h,   600 rounds) ──┐
                             ├── Git Ref 原子鎖 ──→ 外部倉庫
tick-b (5.5h, 660 rounds) ──┘
       ↕ 互守護
```

## 原子鎖

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

## 自癒

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

## 容錯

| 場景 | 結果 |
|------|------|
| 雙鏈存活 | 2 競爭鎖 → 執行 1 次 ✅ |
| 單鏈存活 | 1 直接獲鎖 → 執行 1 次 ✅ |
| 全滅 | `git push main` 或手動觸發任意 tick 🔄 |

## 檔案

```
.github/workflows/
├── tick-a.yml          定時器 A (600 輪 ≈ 5h)
└── tick-b.yml          定時器 B (660 輪 ≈ 5.5h)

tick.py                 定時器 + 原子鎖 + 調度器
test_tick.py            單元測試 (257 用例, 含快進模擬)
AGENTS.md               AI 編碼準則
```

## 核心函數

| 函數 | 職責 |
|------|------|
| `match_field(expr, value, field_min)` | 單個 cron 字段匹配 (`*`, `*/N`, 逗號, 範圍) |
| `match_cron(fields, now)` | 5 字段 cron 表達式匹配，含日/月偏移修正 |
| `parse_dispatch()` | 解析 DISPATCH secret，支援註釋和空行 |
| `is_expired(lock_tag, now_epoch, now_min)` | 鎖過期判斷 (cron/秒級/舊格式兼容) |
| `sanitize_key(key)` | cron 表達式 → 合法 ref 名稱 |
| `schedule_round(epoch, ...)` | 純調度邏輯 (無 I/O)，支援快進模擬測試 |

## 擴展

唯一配置：Secret `DISPATCH`，每行一條，支援註釋 (`#`) 和空行：

**crontab 5 字段** (最小粒度 1 分鐘):

```
分 時 日 月 週  倉庫  工作流
```

**秒級語法** (任意間隔):

```
@Ns  倉庫  工作流
```

字段語法同 crontab：`*` 任意 / `*/5` 每 5 / `0,30` 指定 / `1-5` 範圍

示例：

```
# 每 5 分鐘檢查
*/5 * * * *  owner/repo  check.yml

# 每天 08:00 日報
0   8 * * *  owner/repo  daily.yml

# 每 30 秒輪詢
@30s         owner/repo  poll.yml
```

> **添加任務只改 Secret，不改任何程式碼。**

## 測試

```bash
python3 test_tick.py
```

覆蓋：純函數驗證、鎖過期判斷、端到端 DISPATCH 解析、24 小時快進調度模擬。

## 啟動

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

或 `git push main` 自動啟動雙鏈。

## 授權

[MIT](LICENSE)
