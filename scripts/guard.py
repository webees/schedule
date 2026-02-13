"""guard.py — 守护者"""
import os, subprocess as sp, time
R = os.environ["REPO"]
gh = lambda *a: sp.run(["gh", *a], capture_output=True, text=True).stdout.strip()
for t in ("tick-a", "tick-b"):
    s = gh("run", "list", "-w", f"{t}.yml", "--json", "status", "-q", ".[0].status", "-R", R, "--limit", "1")
    print(f"{'🚨' if s not in ('in_progress','queued') else '✅'} {t}")
    if s not in ("in_progress", "queued"): gh("workflow", "run", f"{t}.yml", "-R", R); time.sleep(60)
