"""tick.py — 三链定时器 + Git Ref 原子锁 (env: SELF, REPO, RUN_ID)"""
import os, subprocess, sys, time

SELF, REPO, RUN = os.environ["SELF"], os.environ["REPO"], int(os.environ["RUN_ID"])
P = f"/repos/{REPO}"


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    return r.stdout.strip(), r.returncode


def api(*a): return gh("api", *a)[0]


def lock(m):
    sha = api(f"{P}/git/ref/heads/main", "-q", ".object.sha")
    return sha and gh("api", f"{P}/git/refs", "-f",
                      f"ref=refs/tags/lock/exec-{m}", "-f", f"sha={sha}")[1] == 0


def clean():
    now = time.strftime('%Y%m%d%H%M', time.gmtime())
    for ref in api(f"{P}/git/refs/tags/lock", "-q", ".[].ref").splitlines():
        if ref.rsplit("-", 1)[-1] < now:
            gh("api", "-X", "DELETE", f"{P}/git/{ref}")


def dispatch(wf):
    gh("workflow", "run", f"{wf}.yml", "-R", REPO)


def alive(wf):
    return gh("run", "list", "-w", f"{wf}.yml", "--json", "status",
              "-q", ".[0].status", "-R", REPO, "--limit", "1")[0] in ("in_progress", "queued")


ROUNDS = 300 + (ord(SELF[-1]) - ord("a")) * 30  # a=300(5h) b=330(5.5h) 错开续期

print(f"🚀 {SELF} run={RUN} rounds={ROUNDS}")
for i in range(1, ROUNDS + 1):
    # 自毁检测
    for rid in gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress",
                  "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO)[0].splitlines():
        if rid and int(rid) > RUN: sys.exit(print(f"🛑 #{rid} 更新, 退出"))

    time.sleep(60 - time.time() % 60)
    t, m = time.strftime('%H:%M:%S', time.gmtime()), time.strftime('%Y%m%d%H%M', time.gmtime())

    won = lock(m)
    print(f"{'🎯' if won else '⏭️'} [{i}/300] {t} {'获锁 → exec' if won else '锁已占'}")
    if won: dispatch("exec")
    if i % 30 == 0: clean()

# 续期 + 守护
dispatch(SELF)
for x in ("tick-a", "tick-b"):
    if x != SELF and not alive(x):
        dispatch("guard"); break
clean()
