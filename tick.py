"""
tick.py — 双链定时器 + Git Ref 原子锁 + crontab 调度

架构:
  tick-a ──┐
           ├── 原子锁竞争 ──→ 获锁者触发外部 workflow
  tick-b ──┘

配置:
  Secret DISPATCH, 每行一条任务, 支持两种格式:
    crontab:  */5 * * * *  owner/repo  check.yml
    秒级:     @30s         owner/repo  poll.yml
"""
import os, subprocess as sp, sys, time

# ══════════════════════════════════════════════════
#  环境变量
# ══════════════════════════════════════════════════

SELF = os.environ["SELF"]                          # 自身 workflow: tick-a | tick-b
REPO = os.environ["REPO"]                          # 当前仓库: owner/repo
RUN  = int(os.environ["RUN_ID"])                   # 当前 run id, 用于新版本检测
PEER = "tick-b" if SELF == "tick-a" else "tick-a"  # 兄弟 workflow
API  = f"/repos/{REPO}"                            # GitHub API 前缀
IV   = 30                                          # 每轮间隔 (秒)
N    = 600 + (ord(SELF[-1]) - ord("a")) * 60       # 总轮次: a=600(5h) b=660(5.5h)

# ══════════════════════════════════════════════════
#  基础工具
# ══════════════════════════════════════════════════

def gh(*args):
    """执行 gh CLI 命令, 返回 (stdout, stderr, returncode)"""
    r = sp.run(["gh", *args], capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def api_get(*args):
    """调用 GitHub API (GET), 返回 stdout"""
    return gh("api", *args)[0]

def alive(wf):
    """检查指定 workflow 是否正在运行或排队中"""
    status = gh("run", "list", "-w", f"{wf}.yml", "--json", "status",
                "-q", ".[0].status", "-R", REPO, "--limit", "1")[0]
    return status in ("in_progress", "queued")

def trigger(repo, wf):
    """触发目标 workflow, 返回是否成功"""
    r = sp.run(["gh", "workflow", "run", wf, "-R", repo],
               capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    stderr: {r.stderr.strip()[:200]}")
    return r.returncode == 0

# ══════════════════════════════════════════════════
#  原子锁 — 基于 Git Ref 的分布式互斥
#
#  原理: 两条 tick 同时 POST 创建同名 ref
#        GitHub 保证只有一个 201, 另一个 422
#        201 = 获锁 → 执行调度
#        422 = 锁已存在 → 跳过
# ══════════════════════════════════════════════════

def lock(name, slot):
    """
    尝试创建 refs/tags/lock/{name}-{slot}
    返回 (是否获锁, 原因)
    """
    sha = api_get(f"{API}/git/ref/heads/main", "-q", ".object.sha")
    if not sha:
        return False, "no sha"
    _, err, rc = gh("api", f"{API}/git/refs",
                    "-f", f"ref=refs/tags/lock/{name}-{slot}",
                    "-f", f"sha={sha}")
    return rc == 0, err if rc else "ok"

def clean_locks():
    """删除所有过期的 lock ref"""
    now = str(int(time.time()))
    for ref in api_get(f"{API}/git/refs/tags/lock", "-q", ".[].ref").splitlines():
        tag = ref.rsplit("-", 1)[-1]
        # 过期判断: 纯数字(epoch slot) 小于 now-300, 或日期格式小于当前分钟
        if tag.isdigit() and int(tag) < int(now) - 300:
            gh("api", "-X", "DELETE", f"{API}/git/{ref}")
        elif not tag.isdigit() and tag < time.strftime('%Y%m%d%H%M', time.gmtime()):
            gh("api", "-X", "DELETE", f"{API}/git/{ref}")

# ══════════════════════════════════════════════════
#  调度 — crontab 5 字段 + 秒级语法
#
#  Secret DISPATCH 格式 (每行):
#
#  标准 crontab (5 字段 + 仓库 + 工作流):
#    分 时 日 月 周  仓库  工作流
#    *      任意值
#    */5    每 5 个单位
#    3      精确匹配
#    1,15   多个值
#    1-5    范围
#
#  秒级语法 (@Ns + 仓库 + 工作流):
#    @30s   每 30 秒
#    @10s   每 10 秒
#
#  示例:
#    */5 * * * *   owner/repo  check.yml     每 5 分钟
#    0 8 * * *     owner/repo  daily.yml     每天 08:00
#    0 9 * * 1     owner/repo  weekly.yml    每周一 09:00
#    @30s          owner/repo  poll.yml      每 30 秒
# ══════════════════════════════════════════════════

def match_field(expr, value):
    """单个 cron 字段是否匹配当前值"""
    if expr == "*":
        return True
    if expr.startswith("*/"):
        return value % int(expr[2:]) == 0
    for part in expr.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            if int(lo) <= value <= int(hi):
                return True
        elif value == int(part):
            return True
    return False

def match_cron(fields, now):
    """5 字段 cron 表达式是否匹配当前时间"""
    vals = [now.tm_min, now.tm_hour, now.tm_mday, now.tm_mon, (now.tm_wday + 1) % 7]
    return all(match_field(f, v) for f, v in zip(fields, vals))

def parse_dispatch():
    """
    解析 DISPATCH, 返回两个列表:
      cron_entries: [(key, fields, repo, wf), ...]
      sec_entries:  [(n, repo, wf), ...]
    """
    cron_entries, sec_entries = [], []
    for line in os.environ.get("DISPATCH", "").splitlines():
        parts = line.split()
        # @30s owner/repo workflow.yml
        if len(parts) == 3 and parts[0].startswith("@") and parts[0].endswith("s"):
            try:
                n = int(parts[0][1:-1])
                sec_entries.append((n, parts[1], parts[2]))
            except ValueError:
                pass
        # */5 * * * * owner/repo workflow.yml
        elif len(parts) == 7:
            key = " ".join(parts[:5])
            cron_entries.append((key, parts[:5], parts[5], parts[6]))
    return cron_entries, sec_entries

CRON_ENTRIES, SEC_ENTRIES = parse_dispatch()

# ══════════════════════════════════════════════════
#  主循环
#
#  每 30 秒:
#    1. 检测是否有新版本 run → 有则退出
#    2. sleep 对齐到 30 秒边界
#    3a. cron 任务: 每分钟调度一次
#    3b. 秒级任务: 按 @Ns 间隔调度
#    4. 检查兄弟存活, 死则直接重启
#    5. 清理过期锁
# ══════════════════════════════════════════════════

clean_locks()
last_m = None
print("══════════════════════════════════════════════════")
print(f"  {SELF} | 运行={RUN} | 轮次={N} | 任务={len(CRON_ENTRIES) + len(SEC_ENTRIES)}")
print("══════════════════════════════════════════════════")
for idx, (key, fields, _, _) in enumerate(CRON_ENTRIES):
    print(f"  #{idx}  {key}")
for idx, (n, _, _) in enumerate(SEC_ENTRIES):
    print(f"  #{len(CRON_ENTRIES) + idx}  @{n}s")
print("══════════════════════════════════════════════════")

for i in range(1, N + 1):

    # ① 新版本检测: 存在更新的 run_id → 立即退出让位
    for rid in gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress",
                  "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO)[0].splitlines():
        try:
            if rid and int(rid) > RUN:
                sys.exit(print(f"🛑 #{rid} 更新, 退出"))
        except ValueError:
            pass

    # ② 对齐 30 秒边界
    time.sleep(IV - time.time() % IV or 0.1)
    now   = time.gmtime()
    epoch = int(time.time())
    t     = time.strftime('%H:%M:%S', now)
    m     = time.strftime('%Y%m%d%H%M', now)

    # ③a cron 任务: 同一分钟内只调度一次
    if m != last_m:
        last_m = m
        for idx, (key, fields, repo, wf) in enumerate(CRON_ENTRIES):
            if not match_cron(fields, now):
                continue
            lock_name = key.replace(" ", "").replace("/", "").replace("*", "x")
            won, reason = lock(lock_name, m)
            status = "获锁→dispatch" if won else f"锁已占({reason})"
            print(f"{'🎯' if won else '⏭️'} [{i}/{N}] {t} #{idx} {key} {status}")
            if won:
                ok = trigger(repo, wf)
                print(f"  {'✅' if ok else '❌'} #{idx}")

    # ③b 秒级任务: epoch // n 作为时间槽, 锁去重
    for j, (n, repo, wf) in enumerate(SEC_ENTRIES):
        slot = epoch // n
        lock_name = f"s{n}"
        won, reason = lock(lock_name, str(slot))
        if won:
            idx = len(CRON_ENTRIES) + j
            ok = trigger(repo, wf)
            print(f"{'🎯' if won else '⏭️'} [{i}/{N}] {t} #{idx} @{n}s {'✅' if ok else '❌'}")

    # ④ 互守护: 每轮检查兄弟, 死亡则直接重启
    if not alive(PEER):
        print(f"🛡️ {PEER} 已死, 唤醒")
        gh("workflow", "run", f"{PEER}.yml", "-R", REPO)

    # ⑤ 清理过期锁 (每 5 分钟)
    if i % 10 == 0:
        clean_locks()

# ══════════════════════════════════════════════════
#  续期 — 轮次结束后自动启动下一轮
# ══════════════════════════════════════════════════

if not alive(SELF):
    gh("workflow", "run", f"{SELF}.yml", "-R", REPO)
clean_locks()
