"""guard.py — 守护者 (env: REPO)"""
import os, subprocess, time

REPO = os.environ["REPO"]


def gh(*a):
    return subprocess.run(["gh", *a], capture_output=True, text=True).stdout.strip()


for t in ("tick-a", "tick-b", "tick-c"):
    s = gh("run", "list", "-w", f"{t}.yml", "--json", "status",
           "-q", ".[0].status", "-R", REPO, "--limit", "1")
    if s not in ("in_progress", "queued"):
        print(f"🚨 {t} 唤醒")
        gh("workflow", "run", f"{t}.yml", "-R", REPO)
        time.sleep(60)
    else:
        print(f"✅ {t}")
