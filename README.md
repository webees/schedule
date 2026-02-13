# Schedule

公开仓库调度器 — 利用 GitHub Actions 无限免费分钟实现精准自调度。

## 原理

```
tick.yml 执行 → sleep 150s → gh workflow run (触发下一次) → ...循环
                                         ↑
cron */30 ─────── 兜底 (链断裂时恢复) ────┘
```

## 用途

为私有仓库提供精准定时触发 (避免 GitHub cron 节流)。
