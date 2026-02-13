"""tick.py — 双链定时器 + Git Ref 原子锁"""
import os, subprocess as sp, sys, time

SELF, REPO, RUN = os.environ["SELF"], os.environ["REPO"], int(os.environ["RUN_ID"])
P, N = f"/repos/{REPO}", 300 + (ord(SELF[-1]) - ord("a")) * 30  # a=300 b=330

def gh(*a): r = sp.run(["gh", *a], capture_output=True, text=True); return r.stdout.strip(), r.returncode
def api(*a): return gh("api", *a)[0]
def run(*a): gh("workflow", "run", f"{a[0]}.yml", "-R", REPO)

def lock(m):
    sha = api(f"{P}/git/ref/heads/main", "-q", ".object.sha")
    return sha and gh("api", f"{P}/git/refs", "-f", f"ref=refs/tags/lock/exec-{m}", "-f", f"sha={sha}")[1] == 0

def clean():
    for ref in api(f"{P}/git/refs/tags/lock", "-q", ".[].ref").splitlines():
        if ref.rsplit("-", 1)[-1] < time.strftime('%Y%m%d%H%M', time.gmtime()):
            gh("api", "-X", "DELETE", f"{P}/git/{ref}")

print(f"🚀 {SELF} run={RUN} n={N}")
for i in range(1, N + 1):
    for rid in gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress",
                  "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO)[0].splitlines():
        if rid and int(rid) > RUN: sys.exit(print(f"🛑 #{rid} 更新, 退出"))
    time.sleep(60 - time.time() % 60)
    t, m = time.strftime('%H:%M:%S', time.gmtime()), time.strftime('%Y%m%d%H%M', time.gmtime())
    w = lock(m)
    print(f"{'🎯' if w else '⏭️'} [{i}/{N}] {t} {'获锁→exec' if w else '锁已占'}")
    if w: run("exec")
    if i % 30 == 0: clean()

run(SELF)
peer = "tick-b" if SELF == "tick-a" else "tick-a"
if gh("run", "list", "-w", f"{peer}.yml", "--json", "status", "-q", ".[0].status",
      "-R", REPO, "--limit", "1")[0] not in ("in_progress", "queued"): run("guard")
clean()
