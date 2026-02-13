# Schedule

[简体中文](README.md) | [English](README_en.md)

> **讓 GitHub Actions 每分鐘精確執行一次，突破 cron 5 分鐘最小間隔與節流延遲。**

## ✨ 亮點

| | |
|---|---|
| ⏱️ **分鐘級精度** | `time.sleep(60 - time.time() % 60)` 對齊整分鐘邊界 |
| 🔒 **原子級去重** | Git Ref 創建天然原子，雙鏈競態只有 1 個 exec |
| 🛡️ **7×24 自癒** | 自續期 + 互守護 + 錯開空窗，無人值守 |
| 📦 **極簡程式碼** | tick.py 46 行 + guard.py 8 行，零外部依賴 |

---

## 架構

```
tick-a (for 迴圈, 駐留 5h) ──┐
                             ├── Git Ref 原子鎖 ──→ exec.yml ──→ 外部倉庫
tick-b (for 迴圈, 駐留 5.5h) ┘
         ↕ 互守護
    guard.yml
```

## 原子鎖

每分鐘兩條 tick 同時嘗試創建同名 Git Ref，GitHub 伺服端保證只有一個成功：

```
tick-a: POST /git/refs → 201 Created  ✅ 獲鎖 → 觸發 exec
tick-b: POST /git/refs → 422 Conflict ❌ 已存在 → 跳過
```

| 特性 | 說明 |
|------|------|
| 原子性 | 同名 ref 不可能被創建兩次 |
| 無競態 | 不依賴狀態查詢，無 API 延遲窗口 |
| 自清理 | 舊 lock tag 每 30 輪自動刪除 |

## 自癒

| 機制 | 說明 |
|------|------|
| 錯開續期 | tick-a 300 輪 / tick-b 330 輪，永不同時空窗 |
| 自續期 | 輪次結束自動 `workflow_dispatch` 下一輪 |
| 互守護 | 每分鐘檢查兄弟存活，死亡則觸發 guard 喚醒 |
| 自毀 | `cancel-in-progress` + run_id 偵測，新程式碼推送秒切換 |

| 小時 | 0 | 5 | 5.5 | 10 | 10.5 |
|------|---|---|-----|----|----- |
| tick-a | 🟢 運行 | 🔄 續期 | 🟢 運行 | 🟢 運行 | 🔄 續期 |
| tick-b | 🟢 運行 | 🟢 運行 | 🔄 續期 | 🟢 運行 | 🟢 運行 |

> 至少有 1 條鏈在線

## 容錯

| 場景 | 結果 |
|------|------|
| 雙鏈存活 | 2 競爭鎖 → exec 1 次 ✅ |
| 單鏈存活 | 1 直接獲鎖 → exec 1 次 ✅ |
| 全滅 | 手動觸發任意 tick 🔄 |

## 檔案

```
.github/workflows/
├── tick-a.yml    定時器 A (300 輪 ≈ 5h)
├── tick-b.yml    定時器 B (330 輪 ≈ 5.5h)
├── exec.yml      業務執行器
└── guard.yml     守護者

scripts/
├── tick.py       定時器 + 原子鎖 (46 行)
└── guard.py      守護邏輯 (8 行)
```

## 啟動

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

或 `git push main` 自動啟動雙鏈。

## 授權

[MIT](LICENSE)
