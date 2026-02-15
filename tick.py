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
INTERVAL   = 30                                    # 每轮间隔 (秒)
ROUNDS     = 600 + (ord(SELF[-1]) - ord("a")) * 60  # 总轮次: a=600(5h) b=660(5.5h)
DEBUG      = os.environ.get("DEBUG", "") == "1"      # 调试模式: 显示详细错误信息
TZ_OFFSET  = int(os.environ.get("TZ_OFFSET", "0"))   # 日志时区偏移 (小时): 8 = UTC+8

# ══════════════════════════════════════════════════
#  工具 — CLI 包装
# ══════════════════════════════════════════════════

def gh(*args):
    """执行 gh CLI 命令, 返回 (stdout, stderr, returncode)"""
    r = sp.run(["gh", *args], capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def gh_api(*args):
    """调用 GitHub API (GET), 返回 stdout"""
    return gh("api", *args)[0]

# ══════════════════════════════════════════════════
#  判断 — 谓词函数
# ══════════════════════════════════════════════════

def is_alive(wf):
    """检查指定 workflow 是否正在运行或排队中"""
    return gh("run", "list", "-w", f"{wf}.yml", "--json", "status",
              "-q", ".[0].status", "-R", REPO, "--limit", "1")[0] in ("in_progress", "queued")

def is_expired(lock_tag, now_epoch, now_minute):
    """
    判断锁标签是否过期
    lock_tag: "{name}-{slot}" 格式
    返回 True 表示过期
    """
    tag = lock_tag.rsplit("-", 1)[-1]
    if len(tag) == 12 and tag.isdigit():  # cron: 202602140805
        return tag < now_minute
    elif tag.isdigit():                   # sec: epoch//N
        # 从锁名提取间隔 N (s{N}x{J}-slot 格式中的 N)
        ref_name = lock_tag.rsplit("-", 1)[0]  # e.g. "s30x0"
        try:
            interval_sec = int(ref_name[1:].split("x")[0])  # 30
            return int(tag) * interval_sec < now_epoch - 300
        except (ValueError, IndexError):
            return True  # 无法解析则视为过期
    return False

# ══════════════════════════════════════════════════
#  锁 — 基于 Git Ref 的分布式互斥
#
#  原理: 两条 tick 同时 POST 创建同名 ref
#        GitHub 保证只有一个 201, 另一个 422
#        201 = 获锁 → 执行调度
#        422 = 锁已存在 → 跳过
# ══════════════════════════════════════════════════

SHA = None  # 缓存 main 分支 SHA, 每轮刷新一次

def refresh_sha():
    """刷新 main 分支 SHA 缓存"""
    global SHA
    SHA = gh_api(f"{API}/git/ref/heads/main", "-q", ".object.sha")

def acquire_lock(name, slot):
    """
    尝试创建 refs/tags/lock/{name}-{slot}
    返回 (是否获锁, 原因)
    """
    if not SHA: return False, "no-sha"
    _, err, rc = gh("api", f"{API}/git/refs",
                    "-f", f"ref=refs/tags/lock/{name}-{slot}",
                    "-f", f"sha={SHA}")
    if rc == 0:
        return True, "ok"
    # 注意: err 可能含仓库名, 仅 DEBUG 模式才暴露
    return False, err if DEBUG else "exists"

def sanitize_key(key):
    """将 cron 表达式转为合法的 ref 名称: 非字母数字替换为 x"""
    return "".join(c if c.isalnum() else "x" for c in key)

# ══════════════════════════════════════════════════
#  解析 — crontab 5 字段 + 秒级语法
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

def match_field(expr, value, field_min=0):
    """单个 cron 字段是否匹配当前值"""
    if expr == "*": return True
    if expr.startswith("*/"): return (value - field_min) % int(expr[2:]) == 0
    # 支持逗号和范围的组合: "1,3-5,10"
    for part in expr.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            if int(lo) <= value <= int(hi): return True
        elif value == int(part): return True
    return False

#  分/时 从 0 开始, 日/月 从 1 开始, 周 从 0 开始
FIELD_MIN = [0, 0, 1, 1, 0]

def match_cron(fields, now):
    """5 字段 cron 表达式是否匹配当前时间"""
    # fields: [分, 时, 日, 月, 周]
    # now: time.struct_time (gmtime)
    vals = [now.tm_min, now.tm_hour, now.tm_mday, now.tm_mon, (now.tm_wday + 1) % 7]
    #                                                          ^^ Python wday 0=Mon → cron 0=Sun
    return all(match_field(f, v, o) for f, v, o in zip(fields, vals, FIELD_MIN))

def parse_dispatch():
    """
    解析 DISPATCH, 返回两个列表:
      cron_entries: [(key, fields, repo, wf, lock_id), ...]
      sec_entries:  [(n, repo, wf), ...]
    """
    cron, sec = [], []
    for line in os.environ.get("DISPATCH", "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        # @30s owner/repo workflow.yml
        if len(parts) == 3 and parts[0].startswith("@") and parts[0].endswith("s"):
            try: sec.append((int(parts[0][1:-1]), parts[1], parts[2]))
            except ValueError: pass
        # */5 * * * * owner/repo workflow.yml
        elif len(parts) == 7:
            key = " ".join(parts[:5])
            # 预计算 lock_id: 非字母数字统一替换为 x
            cron.append((key, parts[:5], parts[5], parts[6], sanitize_key(key)))
    return cron, sec

CRON_ENTRIES, SEC_ENTRIES = parse_dispatch()

# ══════════════════════════════════════════════════
#  调度 — 竞锁 + 触发 + 日志
# ══════════════════════════════════════════════════

BAR = "═" * 50

PAT_ENV = {**os.environ, "GH_TOKEN": os.environ.get("PAT", "")}

def trigger_workflow(repo, wf):
    """触发目标 workflow (使用 PAT 跨仓库), 返回 (是否成功, 错误信息)"""
    r = sp.run(["gh", "workflow", "run", wf, "-R", repo],
               capture_output=True, text=True, env=PAT_ENV)
    return r.returncode == 0, r.stderr.strip()

def scan_round(epoch, last_minute, last_slot, cron_entries, sec_entries, on_fire):
    """
    纯调度逻辑 (不含 I/O), 返回更新后的 (last_minute, last_slot)

    on_fire(idx, show, repo, wf): 当任务需要触发时回调
    """
    now = time.gmtime(epoch)
    minute_key = time.strftime('%Y%m%d%H%M', now)

    # cron 任务: 同一分钟内只调度一次
    if minute_key != last_minute:
        last_minute = minute_key
        for idx, (key, fields, repo, wf, lock_id) in enumerate(cron_entries):
            if match_cron(fields, now):
                on_fire(idx, key, repo, wf)

    # 秒级任务: epoch // n 作为时间槽, 去重
    for j, (interval_sec, repo, wf) in enumerate(sec_entries):
        slot = epoch // interval_sec
        if last_slot.get(j) == slot:
            continue
        last_slot[j] = slot
        on_fire(len(cron_entries) + j, f"@{interval_sec}s", repo, wf)

    return last_minute, last_slot

def execute_task(round_num, time_str, idx, label, show, repo, wf):
    """竞锁 + 触发 + 日志 (通用)"""
    won, reason = acquire_lock(*label)
    tag = f"{round_num}/{ROUNDS} 🕐 {time_str} #{idx} 🏷️ {show}"
    if won:
        ok, err = trigger_workflow(repo, wf)
        status = '✅' if ok else ('❌ ' + err if DEBUG else '❌')
        print(f"🎯 {tag} {status}")
    else:
        print(f"⏭️ {tag} ❌ {reason}")

# ══════════════════════════════════════════════════
#  维护 — 清理 + 守护 + 续期
# ══════════════════════════════════════════════════

def clean_locks():
    """删除所有过期的 lock ref"""
    now_epoch = int(time.time())
    now_minute = time.strftime('%Y%m%d%H%M', time.gmtime())
    raw = gh_api(f"{API}/git/refs/tags/lock", "-q", ".[].ref")
    if not raw or raw.startswith("{"):
        return  # 无锁或 API 返回错误 JSON (404)
    for ref in raw.splitlines():
        lock_tag = ref.rsplit("/", 1)[-1]  # {name}-{slot}
        if is_expired(lock_tag, now_epoch, now_minute):
            gh("api", "-X", "DELETE", f"{API}/git/{ref}")

def clean_runs():
    """删除已完成的 workflow run, 保留当前运行中的"""
    ids = gh("run", "list", "-R", REPO, "--status", "completed",
             "--limit", "100", "--json", "databaseId",
             "-q", f".[] | select(.databaseId != {RUN}) | .databaseId")[0].split()
    for rid in ids:
        sp.Popen(["gh", "run", "delete", rid, "-R", REPO],
                 stdout=sp.DEVNULL, stderr=sp.DEVNULL)

def check_update():
    """检测是否有更新的 run_id, 有则退出让位"""
    for rid in gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress",
                  "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO)[0].splitlines():
        try:
            if rid and int(rid) > RUN:
                sys.exit(print(f"🛑 #{rid} 更新, 退出"))
        except ValueError:
            pass

def guard_peer():
    """检查兄弟存活, 死亡则重启"""
    if not is_alive(PEER):
        print(f"🛡️ {PEER} 已死, 唤醒")
        gh("workflow", "run", f"{PEER}.yml", "-R", REPO)

def renew_self():
    """轮次结束后自动续期"""
    if not is_alive(SELF):
        print(f"🔄 轮次结束, 续期")
        gh("workflow", "run", f"{SELF}.yml", "-R", REPO)
    print(f"✅ {SELF} 完成")

def print_banner():
    """启动时打印运行信息和任务列表"""
    print(BAR)
    print(f"  {SELF} | id={RUN}")
    print(BAR)
    for idx, (key, _, _, _, _) in enumerate(CRON_ENTRIES):
        print(f"  #{idx}  {key}")
    for idx, (interval_sec, _, _) in enumerate(SEC_ENTRIES):
        print(f"  #{len(CRON_ENTRIES) + idx}  @{interval_sec}s")
    if CRON_ENTRIES or SEC_ENTRIES:
        print(BAR)

# ══════════════════════════════════════════════════
#  主循环
#
#  每 30 秒:
#    1. 运维: 版本检测 + 互守护 + 清理锁/run
#    2. sleep 对齐到 30 秒边界
#    3a. cron 任务: 每分钟调度一次
#    3b. 秒级任务: 按 @Ns 间隔调度
# ══════════════════════════════════════════════════

if __name__ == "__main__":

    print_banner()

    last_minute    = None
    last_slot = {}  # 秒级任务去重: {j: last_slot_value}

    for round_num in range(1, ROUNDS + 1):

        # ① 运维: 版本检测 + 互守护 + 清理
        check_update()
        guard_peer()
        clean_locks()
        clean_runs()

        # ② 对齐 30 秒边界
        time.sleep(max(0.1, INTERVAL - time.time() % INTERVAL))
        epoch      = int(time.time())
        now        = time.gmtime(epoch)
        time_str   = time.strftime('%H:%M:%S', time.gmtime(epoch + TZ_OFFSET * 3600))
        minute_key = time.strftime('%Y%m%d%H%M', now)  # cron 匹配始终用 UTC
        refresh_sha()  # 每轮刷新一次 SHA, 供所有 acquire_lock() 复用

        # ③ 调度 (统一使用 scan_round, 与测试共享同一份逻辑)
        def on_fire(idx, show, repo, wf):
            # 计算锁标签: cron 用 sanitized_key+idx, sec 用 s{N}x{J}
            if idx < len(CRON_ENTRIES):
                label = (f"{CRON_ENTRIES[idx][4]}{idx}", minute_key)
            else:
                j = idx - len(CRON_ENTRIES)
                label = (f"s{SEC_ENTRIES[j][0]}x{j}", str(epoch // SEC_ENTRIES[j][0]))
            execute_task(round_num, time_str, idx, label, show, repo, wf)
        last_minute, last_slot = scan_round(
            epoch, last_minute, last_slot, CRON_ENTRIES, SEC_ENTRIES, on_fire)

    renew_self()
