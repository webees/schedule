# Schedule

[简体中文](README.md) | [English](README_en.md)

精準自調度系統 — 三鏈駐留 + 單例執行器 + 守護者，繞過 GitHub cron 節流限制。

## 問題

GitHub Actions 的 cron 調度存在嚴重節流：設定每 5 分鐘執行，實際間隔可達 50+ 分鐘。

## 方案

三條 tick 鏈在 VM 內以 for 迴圈駐留（每輪 5 小時），對齊整分鐘精準觸發單例業務執行器。

## 架構

```
tick-a (for迴圈, 駐留5h, 負責 min%3==0) ──┐
tick-b (for迴圈, 駐留5h, 負責 min%3==1) ──┼── 每分鐘恰好一個觸發 ──→ exec.yml (單例)
tick-c (for迴圈, 駐留5h, 負責 min%3==2) ──┘                              │
         ▲                                                               ▼
    guard.yml (單例喚醒者)                                        觸發外部倉庫
```

## 時序

```
分鐘:  :00   :01   :02   :03   :04   :05   :06
tick-a: 🎯                 🎯                 🎯      ← min%3==0
tick-b:       🎯                 🎯                    ← min%3==1
tick-c:             🎯                 🎯              ← min%3==2
exec:   █    █    █    █    █    █    █               ← 每分鐘一次, 單例
```

## 核心機制

### 精準對齊

```bash
# 每次迴圈對齊到整分鐘
SEC=$(date -u '+%-S')
WAIT=$((60 - SEC))
sleep $WAIT
```

### 三重去重

```
1. 分鐘分配: min%3 == offset → 每分鐘只有一條 tick 有權觸發
2. 狀態檢查: 觸發前檢查 exec 是否 in_progress/queued → 跳過
3. concurrency: exec.yml group=exec → 萬一雙觸發也只跑一個
```

### 互守護

```
tick-a 發現 tick-b 死了 → 觸發 guard.yml
tick-c 發現 tick-b 死了 → 也觸發 guard.yml → 被 cancel-in-progress 丟棄
guard 單例運行 → 檢查所有 tick → 喚起死掉的鏈
```

## 檔案

| 檔案 | 作用 | 生命週期 |
|------|------|---------|
| `tick-a/b/c.yml` | 定時器 (for 迴圈駐留) | ~5h/輪, 自動續期 |
| `exec.yml` | 業務執行器 (單例) | 每次觸發 ~30s |
| `guard.yml` | 守護者 (喚醒死掉的 tick) | 按需 |

> tick-a/b/c 三個檔案邏輯完全一致, 僅 `name:` 不同, 透過 `github.workflow` 動態推導身份。

## 啟動

```bash
gh workflow run tick-a.yml && sleep 60 && gh workflow run tick-b.yml && sleep 60 && gh workflow run tick-c.yml
```

## 全滅恢復

手動觸發任意一條 tick → 守護機制自動喚起其他鏈。

## 授權

MIT
