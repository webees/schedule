"""tick.py — 三链定时器 (env: SELF, REPO, RUN_ID)"""
import os, subprocess, sys, time

SELF = os.environ["SELF"]
REPO = os.environ["REPO"]
RUN  = int(os.environ["RUN_ID"])
OFF  = ord(SELF[-1]) - ord("a")  # a→0 b→1 c→2


def gh(*a):
    return subprocess.run(["gh", *a], capture_output=True, text=True).stdout.strip()


def alive(wf):
    return gh("run", "list", "-w", wf, "--json", "status",
              "-q", ".[0].status", "-R", REPO, "--limit", "1") in ("in_progress", "queued")


def main():
    print(f"🚀 {SELF} (off={OFF} run={RUN})")

    for _ in range(300):  # 300 轮 ≈ 5h
        # 新实例检测 → 自毁
        for rid in gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress",
                       "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO).splitlines():
            if rid and int(rid) > RUN:
                sys.exit(print(f"🛑 新实例 #{rid}, 退出"))

        # 对齐整分钟
        time.sleep(60 - time.time() % 60)

        # 轮到我 + exec 空闲 → 触发
        if time.gmtime().tm_min % 3 == OFF and not alive("exec.yml"):
            print(f"🎯 {time.strftime('%H:%M:%S', time.gmtime())} exec")
            gh("workflow", "run", "exec.yml", "-R", REPO)

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
