# Schedule

[简体中文](README.md) | [English](README_en.md)

精準自調度系統 — 三鏈駐留 + 單例執行器 + 守護者，繞過 GitHub cron 節流限制。

## 問題

GitHub Actions 的 cron 調度存在嚴重節流：設定每 5 分鐘執行，實際間隔可達 50+ 分鐘。

## 方案

三條 tick 鏈在 VM 內以 for 迴圈駐留（每輪 5 小時），對齊整分鐘精準觸發單例業務執行器。

## 架構

```
tick-a (for loop, 5h, min%3==0) ---+
tick-b (for loop, 5h, min%3==1) ---+--> exec.yml (singleton) --> external repo
tick-c (for loop, 5h, min%3==2) ---+
  ^                                         |
  +---- guard.yml (singleton reviver) <-----+
```

## 時序

```
min   :00  :01  :02  :03  :04  :05  :06  :07  :08
 a     *              *              *
 b          *              *              *
 c               *              *              *
exec  [=]  [=]  [=]  [=]  [=]  [=]  [=]  [=]  [=]
```

> `*` = tick 觸發 exec, `[=]` = exec 執行, 每分鐘恰好一次

## 核心機制

**精準對齊** — 每輪迴圈 sleep 到整分鐘邊界

```python
time.sleep(60 - time.time() % 60)
```

**三重去重** — 確保 exec 不被重複觸發

```
1. min%3 == offset    每分鐘只有一條 tick 有權觸發
2. alive("exec.yml")  觸發前檢查 exec 是否已在運行
3. concurrency: exec  萬一雙觸發, 平台級保證只跑一個
```

**新實例自毀** — 程式碼更新後舊鏈自動退出

```
cancel-in-progress: true   平台級: 新 run 取消舊 run
check_newer() per loop     程式碼級: 偵測到更新 run_id 則 sys.exit
```

**互守護** — 兄弟鏈死亡時觸發 guard 喚醒

```
tick-a detects tick-b dead --> trigger guard.yml (singleton)
tick-c detects tick-b dead --> trigger guard.yml (dropped by cancel-in-progress)
guard runs once --> revives tick-b
```

## 檔案結構

```
.github/workflows/
  tick-a.yml        timer A (only name differs)
  tick-b.yml        timer B
  tick-c.yml        timer C
  exec.yml          executor (singleton)
  guard.yml         guardian (singleton)

scripts/
  tick.py           timer logic (~50 lines, shared by a/b/c)
  guard.py          guardian logic (~20 lines)
```

## 啟動

```bash
gh workflow run tick-a.yml
sleep 60
gh workflow run tick-b.yml
sleep 60
gh workflow run tick-c.yml
```

或直接 `git push` 到 main — 三條鏈自動啟動。

## 全滅恢復

手動觸發任意一條 tick，守護機制自動喚起其他鏈。

## 授權

MIT
