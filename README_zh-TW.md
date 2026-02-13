# Schedule

[简体中文](README.md) | [English](README_en.md)

> 🎯 **讓 GitHub Actions 每分鐘精確觸發一次。**

## ✨ 亮點

- ⏱️ **分鐘級精度** — 突破 GitHub cron 5 分鐘最小間隔 + 節流延遲
- 🔒 **Git Ref 原子鎖** — 雙鏈競態觸發，伺服端保證只有 1 個 exec 執行
- 🛡️ **自癒架構** — 互守護 + 自續期，7×24 無人值守
- 📦 **極簡實現** — 2 個 Python 腳本 (56 + 20 行)，零外部依賴

## ❌ 問題

GitHub Actions cron 最小間隔 5 分鐘，實際調度延遲可達 **50+ 分鐘**。

## ✅ 方案

雙 tick 鏈在 VM 內以 for 迴圈駐留 5 小時，每分鐘對齊整點，透過 **Git Ref 原子鎖** 競爭觸發單例執行器。

## 🏗️ 架構

```
tick-a (for迴圈, 駐留5h) ──┐
                           ├── 原子鎖競爭 ──→ exec.yml (單例) ──→ 外部倉庫
tick-b (for迴圈, 駐留5h) ──┘
         ↕ 互守護
    guard.yml (喚醒者)
```

## 🔧 核心機制

### 🔒 Git Ref 原子鎖

```python
# 每分鐘建立唯一 tag: refs/tags/lock/exec-202602140445
# GitHub API 保證: 同名 ref 只能建立一次

tick-a: POST /git/refs → 201 Created  ✅ 獲鎖 → 觸發 exec
tick-b: POST /git/refs → 422 Conflict ❌ 已存在 → 跳過
```

### 🛡️ 自癒

| 機制 | 說明 |
|------|------|
| **錯開續期** | tick-a=300 輪(5h)，tick-b=330 輪(5.5h)，永不同時空窗 |
| **自續期** | 輪次結束後自動觸發下一輪 |
| **互守護** | tick 結束時檢查兄弟，死亡則觸發 guard 喚醒 |
| **新實例自毀** | `cancel-in-progress: true` + 程式碼級 run_id 偵測 |

| 小時 | 0 | 5 | 5.5 | 10 | 10.5 | 11 |
|------|---|---|-----|----|----- |----|
| tick-a | 🟢 300輪運行中 | 🔄 續期 | 🟢 運行中 | 🟢 運行中 | 🔄 續期 | 🟢 |
| tick-b | 🟢 330輪運行中 | 🟢 運行中 | 🔄 續期 | 🟢 運行中 | 🟢 運行中 | 🔄 |

> 續期時刻永遠錯開，至少有 1 條鏈在線

## 📁 檔案結構

```
.github/workflows/
├── tick-a.yml / tick-b.yml   ⏱️ 定時器
├── exec.yml                  🚀 業務執行器 (單例)
└── guard.yml                 🛡️ 守護者

scripts/
├── tick.py    ⏱️ 定時器 + 原子鎖 (56 行)
└── guard.py   🛡️ 守護邏輯 (20 行)
```

## 🚀 啟動

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml
```

或直接 `git push` 到 main — 雙鏈自動啟動。

## 📄 授權

[MIT](LICENSE)
