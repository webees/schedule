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

        # exec 空闲 → 触发 (三条 tick 都尝试, alive+concurrency 保证单例)
        if not alive("exec.yml"):
            print(f"🎯 [{i}/300] {ts} 触发 exec")
            gh("workflow", "run", "exec.yml", "-R", REPO)
        else:
            print(f"⏭️ [{i}/300] {ts} exec 运行中")

    # 续期 (无排队才触发)
    q = gh("run", "list", "-w", f"{SELF}.yml", "-s", "queued",
           "--json", "databaseId", "-q", "length", "-R", REPO)
    if not q or q == "0":
        gh("workflow", "run", f"{SELF}.yml", "-R", REPO)

    # 守护兄弟
    for t in ("tick-a", "tick-b", "tick-c"):
        if t != SELF and not alive(f"{t}.yml"):
            gh("workflow", "run", "guard.yml", "-R", REPO)
            break


if __name__ == "__main__":
    main()
