"""tick.py — 三链定时器 (env: SELF, REPO, RUN_ID)"""
import os, subprocess, sys, time

SELF = os.environ["SELF"]
REPO = os.environ["REPO"]
RUN  = int(os.environ["RUN_ID"])


def gh(*a):
    return subprocess.run(["gh", *a], capture_output=True, text=True).stdout.strip()


def alive(wf):
    return gh("run", "list", "-w", wf, "--json", "status",
              "-q", ".[0].status", "-R", REPO, "--limit", "1") in ("in_progress", "queued")


def try_lock(minute):
    """原子锁: 创建 git ref, 201=获锁, 422=已占"""
    sha = gh("api", f"/repos/{REPO}/git/ref/heads/main", "-q", ".object.sha")
    if not sha:
        return False
    r = subprocess.run(
        ["gh", "api", f"/repos/{REPO}/git/refs",
         "-f", f"ref=refs/tags/lock/exec-{minute}", "-f", f"sha={sha}"],
        capture_output=True, text=True)
    return r.returncode == 0


def cleanup_locks():
    """清理旧 lock tag"""
    refs = gh("api", f"/repos/{REPO}/git/refs/tags/lock",
              "-q", ".[].ref", "--paginate")
    now = time.strftime('%Y%m%d%H%M', time.gmtime())
    for ref in refs.splitlines():
        minute = ref.rsplit("-", 1)[-1]  # exec-202602140430 → 202602140430
        if minute < now:
            gh("api", "-X", "DELETE", f"/repos/{REPO}/git/{ref}")


def main():
    print(f"🚀 {SELF} (run={RUN})")

    for i in range(1, 301):  # 300 轮 ≈ 5h
        # 新实例检测 → 自毁
        for rid in gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress",
                       "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO).splitlines():
            if rid and int(rid) > RUN:
                sys.exit(print(f"🛑 新实例 #{rid}, 退出"))

        # 对齐整分钟
        time.sleep(60 - time.time() % 60)
        ts = time.strftime('%H:%M:%S', time.gmtime())
        minute = time.strftime('%Y%m%d%H%M', time.gmtime())

        # 原子锁竞争: 3 条 tick 同时尝试创建同名 ref, 只有 1 个成功
        if try_lock(minute):
            print(f"🎯 [{i}/300] {ts} 获锁, 触发 exec")
            gh("workflow", "run", "exec.yml", "-R", REPO)
        else:
            print(f"⏭️ [{i}/300] {ts} 锁已被占")

        # 每 30 轮清理旧锁
        if i % 30 == 0:
            cleanup_locks()

    # 续期
    if not alive(f"{SELF}.yml"):
        gh("workflow", "run", f"{SELF}.yml", "-R", REPO)

    # 守护兄弟
    for t in ("tick-a", "tick-b", "tick-c"):
        if t != SELF and not alive(f"{t}.yml"):
            gh("workflow", "run", "guard.yml", "-R", REPO)
            break

    cleanup_locks()


if __name__ == "__main__":
    main()
