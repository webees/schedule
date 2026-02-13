"""guard.py — 守护者: 检查所有 tick, 唤起死掉的链

环境变量:
  REPO — 仓库 (owner/repo)
"""
import json, os, subprocess, time

REPO = os.environ["REPO"]


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    return r.stdout.strip()


def main():
    revived = 0
    for t in ("tick-a", "tick-b", "tick-c"):
        s = gh("run", "list", "-w", f"{t}.yml", "--json", "status", "-q", ".[0].status", "-R", REPO, "--limit", "1")
        if s not in ("in_progress", "queued"):
            print(f"🚨 {t} 已停止, 唤醒中...")
            gh("workflow", "run", f"{t}.yml", "-R", REPO)
            revived += 1
            time.sleep(60)  # 交错启动
        else:
            print(f"✅ {t} 存活 (status: {s})")
    print(f"📊 本次唤醒: {revived} 条链")


if __name__ == "__main__":
    main()
