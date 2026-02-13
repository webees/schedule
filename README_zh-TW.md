# Schedule

[简体中文](README.md) | [English](README_en.md)

🎯 精準自調度系統 — 三鏈駐留 + 單例執行器 + 守護者，繞過 GitHub cron 節流限制。

## ❌ 問題

GitHub Actions 的 cron 調度存在嚴重節流：設定每 5 分鐘執行，實際間隔可達 50+ 分鐘。

## ✅ 方案

三條 tick 鏈在 VM 內以 for 迴圈駐留（每輪 5 小時），對齊整分鐘精準觸發單例業務執行器。

## 🏗️ 架構

```
tick-a (for迴圈, 駐留5h, 負責 min%3==0) ──┐
tick-b (for迴圈, 駐留5h, 負責 min%3==1) ──┼── 每分鐘恰好一個觸發 ──→ exec.yml (單例)
tick-c (for迴圈, 駐留5h, 負責 min%3==2) ──┘                              │
         ▲                                                               ▼
    guard.yml (單例喚醒者)                                        觸發外部倉庫
```

## ⏱️ 時序

| 分鐘 | :00 | :01 | :02 | :03 | :04 | :05 | :06 | :07 | :08 |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| tick-a | 🎯 | | | 🎯 | | | 🎯 | | |
| tick-b | | 🎯 | | | 🎯 | | | 🎯 | |
| tick-c | | | 🎯 | | | 🎯 | | | 🎯 |
| exec | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 🔧 核心機制

### 三重去重

| 層級 | 機制 | 說明 |
|------|------|------|
| 1️⃣ | `min%3 == offset` | 每分鐘只有一條 tick 有權觸發 |
| 2️⃣ | `alive("exec.yml")` | 觸發前檢查 exec 是否已在運行 |
| 3️⃣ | `concurrency: exec` | 萬一雙觸發，平台級保證只跑一個 |

### 新實例自毀

| 層級 | 機制 | 說明 |
|------|------|------|
| 🅰️ | `cancel-in-progress: true` | 平台級：新 run 取消舊 run |
| 🅱️ | `check_newer()` 每輪偵測 | 程式碼級：偵測到更新 run_id 則 `sys.exit` |

## 📁 檔案結構

```
.github/workflows/
├── tick-a/b/c.yml    ⏱️ 定時器 (僅 name 不同, 邏輯共用 tick.py)
├── exec.yml          🚀 業務執行器 (單例)
└── guard.yml         🛡️ 守護者 (單例)

scripts/
├── tick.py           ⏱️ 定時器邏輯 (~50 行)
└── guard.py          🛡️ 守護邏輯 (~20 行)
```

## 🚀 啟動

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml && sleep 60 && gh workflow run tick-c.yml
```

或直接 `git push` 到 main — 三條鏈自動啟動。

## 📄 授權

[MIT](LICENSE)
