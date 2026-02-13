"""tick.py — 双链定时器 + Git Ref 原子锁"""
import os, subprocess as sp, sys, time

SELF, REPO, RUN = os.environ["SELF"], os.environ["REPO"], int(os.environ["RUN_ID"])
P, N = f"/repos/{REPO}", 300 + (ord(SELF[-1]) - ord("a")) * 30  # a=300 b=330
PEER = "tick-b" if SELF == "tick-a" else "tick-a"

def gh(*a):
    r = sp.run(["gh", *a], capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def api(*a): return gh("api", *a)[0]

def lock(m):
    sha = api(f"{P}/git/ref/heads/main", "-q", ".object.sha")
    if not sha: return False, "no sha"
    out, err, rc = gh("api", f"{P}/git/refs", "-f", f"ref=refs/tags/lock/exec-{m}", "-f", f"sha={sha}")
    return rc == 0, err if rc else "ok"

def clean():
    now = time.strftime('%Y%m%d%H%M', time.gmtime())
    for ref in api(f"{P}/git/refs/tags/lock", "-q", ".[].ref").splitlines():
        if ref.rsplit("-", 1)[-1] < now:
            gh("api", "-X", "DELETE", f"{P}/git/{ref}")

def alive(w): return gh("run", "list", "-w", f"{w}.yml", "--json", "status",
                        "-q", ".[0].status", "-R", REPO, "--limit", "1")[0] in ("in_progress", "queued")

def run(wf): gh("workflow", "run", f"{wf}.yml", "-R", REPO)

clean()
print(f"🚀 {SELF} run={RUN} n={N}")
for i in range(1, N + 1):
    for rid in gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress",
                  "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO)[0].splitlines():
        if rid and int(rid) > RUN: sys.exit(print(f"🛑 #{rid} 更新, 退出"))
    time.sleep(60 - time.time() % 60)
    t, m = time.strftime('%H:%M:%S', time.gmtime()), time.strftime('%Y%m%d%H%M', time.gmtime())
    won, reason = lock(m)
    print(f"{'🎯' if won else '⏭️'} [{i}/{N}] {t} {'获锁→exec' if won else f'锁已占({reason})'}")
    if won: run("exec")
    if i % 5 == 0 and not alive(PEER): print(f"🛡️ {PEER} 已死, 唤醒"); run("guard")
    if i % 30 == 0: clean()

if not alive(SELF): run(SELF)
clean()
