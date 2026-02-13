"""tick.py — 定时器核心逻辑

环境变量:
  SELF     — tick 名称 (tick-a / tick-b / tick-c)
  REPO     — 仓库 (owner/repo)
  RUN_ID   — 当前 run ID (用于排除自己)
"""
import json, os, subprocess, time

SELF   = os.environ["SELF"]
REPO   = os.environ["REPO"]
RUN_ID = os.environ["RUN_ID"]
OFFSET = {"a": 0, "b": 1, "c": 2}[SELF[-1]]
ROUNDS = 300  # 300 轮 × ~60s ≈ 5h


def gh(*args):
    """调用 gh CLI, 返回 stdout"""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    return r.stdout.strip()


def gh_json(*args):
    """调用 gh CLI, 返回 JSON"""
    out = gh(*args)
    return json.loads(out) if out else []


def run_status(workflow):
    """获取 workflow 最新 run 的 status"""
    runs = gh_json("run", "list", "-w", workflow, "--json", "status", "-q", ".[0].status", "-R", REPO, "--limit", "1")
    return runs if isinstance(runs, str) else ""


def cancel_old():
    """取消同名旧实例"""
    print(f"🧹 清理 {SELF} 旧实例...")
    ids = gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress", "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO)
    for rid in ids.splitlines():
        if rid and rid != RUN_ID:
            gh("run", "cancel", rid, "-R", REPO)
            print(f"  取消: #{rid}")


def trigger_exec():
    """检查并触发 exec"""
    s = run_status("exec.yml")
    if s not in ("in_progress", "queued"):
        print(f"🎯 {time.strftime('%H:%M:%S', time.gmtime())} 触发 exec")
        gh("workflow", "run", "exec.yml", "-R", REPO)
    else:
        print(f"⏭️ {time.strftime('%H:%M:%S', time.gmtime())} exec 运行中, 跳过")


def renew():
    """自调度下一周期"""
    queued = gh("run", "list", "-w", f"{SELF}.yml", "-s", "queued", "--json", "databaseId", "-q", "length", "-R", REPO)
    if queued == "0" or not queued:
        gh("workflow", "run", f"{SELF}.yml", "-R", REPO)
        print("🔄 已触发下一周期")


def guard():
    """检查兄弟链"""
    for t in ("tick-a", "tick-b", "tick-c"):
        if t == SELF:
            continue
        s = run_status(f"{t}.yml")
        if s not in ("in_progress", "queued"):
            print(f"⚠️ {t} 已停止, 触发 guard")
            gh("workflow", "run", "guard.yml", "-R", REPO)
            break


def main():
    cancel_old()
    print(f"🚀 {SELF} 启动 (offset={OFFSET})")

    for i in range(1, ROUNDS + 1):
        # 对齐到整分钟
        now = time.time()
        wait = 60 - (now % 60)
        if 0 < wait <= 60:
            time.sleep(wait)

        # 只在属于自己的分钟触发
        minute = time.gmtime().tm_min
        if minute % 3 == OFFSET:
            trigger_exec()

    renew()
    guard()
    print(f"✅ {SELF} 本轮结束")


if __name__ == "__main__":
    main()
