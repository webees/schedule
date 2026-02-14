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
    return gh("run", "list", "-w", f"{wf}.yml", "--json", "status",
              "-q", ".[0].status", "-R", REPO, "--limit", "1")[0] in ("in_progress", "queued")

def trigger(repo, wf):
    """触发目标 workflow, 返回是否成功"""
    _, err, rc = gh("workflow", "run", wf, "-R", repo)
    if rc: print(f"    stderr: {err[:200]}")
    return rc == 0

# ══════════════════════════════════════════════════
#  原子锁 — 基于 Git Ref 的分布式互斥
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
    SHA = api_get(f"{API}/git/ref/heads/main", "-q", ".object.sha")

def lock(name, slot):
    """
    尝试创建 refs/tags/lock/{name}-{slot}
    返回 (是否获锁, 原因)
    """
    if not SHA: return False, "no sha"
    _, err, rc = gh("api", f"{API}/git/refs",
                    "-f", f"ref=refs/tags/lock/{name}-{slot}",
                    "-f", f"sha={SHA}")
    return rc == 0, err if rc else "ok"

def is_expired(lock_tag, now_epoch, now_min):
    """
    判断锁标签是否过期
    lock_tag: "{name}-{slot}" 格式
    返回 True 表示过期
    """
    tag = lock_tag.rsplit("-", 1)[-1]
    if len(tag) == 12 and tag.isdigit():  # cron: 202602140805
        return tag < now_min
    elif tag.isdigit():                   # sec: epoch//N
        # 从锁名提取间隔 N (s{N}x{J}-slot 格式中的 N)
        ref_name = lock_tag.rsplit("-", 1)[0]  # e.g. "s30x0"
        try:
            n = int(ref_name[1:].split("x")[0])  # 30
            return int(tag) * n < now_epoch - 300
        except (ValueError, IndexError):
            return True  # 无法解析则视为过期
    return False

def sanitize_key(key):
    """将 cron 表达式转为合法的 ref 名称: 非字母数字替换为 x"""
    return "".join(c if c.isalnum() else "x" for c in key)

def clean_locks():
    """删除所有过期的 lock ref"""
    now_epoch = int(time.time())
    now_min   = time.strftime('%Y%m%d%H%M', time.gmtime())
    raw = api_get(f"{API}/git/refs/tags/lock", "-q", ".[].ref")
    if not raw or raw.startswith("{"):
        return  # 无锁或 API 返回错误 JSON (404)
    for ref in raw.splitlines():
        lock_tag = ref.rsplit("/", 1)[-1]  # {name}-{slot}
        if is_expired(lock_tag, now_epoch, now_min):
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
#  主循环
#
#  每 30 秒:
#    1. 检测是否有新版本 run → 有则退出
#    2. 检查兄弟存活, 死则直接重启
#    3. 清理过期锁
#    4. sleep 对齐到 30 秒边界
#    5a. cron 任务: 每分钟调度一次
#    5b. 秒级任务: 按 @Ns 间隔调度
# ══════════════════════════════════════════════════

BAR = "═" * 50

def schedule_round(epoch, last_m, last_slot, cron_entries, sec_entries, on_fire):
    """
    纯调度逻辑 (不含 I/O), 返回更新后的 (last_m, last_slot)

    on_fire(idx, show, repo, wf): 当任务需要触发时回调
    """
    now = time.gmtime(epoch)
    m   = time.strftime('%Y%m%d%H%M', now)

    # cron 任务: 同一分钟内只调度一次
    if m != last_m:
        last_m = m
        for idx, (key, fields, repo, wf, lock_id) in enumerate(cron_entries):
            if match_cron(fields, now):
                on_fire(idx, key, repo, wf)

    # 秒级任务: epoch // n 作为时间槽, 去重
    for j, (n, repo, wf) in enumerate(sec_entries):
        slot = epoch // n
        if last_slot.get(j) == slot:
            continue
        last_slot[j] = slot
        on_fire(len(cron_entries) + j, f"@{n}s", repo, wf)

    return last_m, last_slot

def dispatch(i, t, idx, label, show, repo, wf):
    """竞锁 + 触发 + 日志 (通用)"""
    won, reason = lock(*label)
    tag = f"[{i}/{N}] {t} #{idx}"
    if won:
        ok = trigger(repo, wf)
        print(f"🎯 {tag} {show} {'✅' if ok else '❌'}")
    else:
        print(f"⏭️ {tag} {show} 锁已占({reason})")

if __name__ == "__main__":

    clean_locks()
    last_m    = None
    last_slot = {}  # 秒级任务去重: {j: last_slot_value}
    print(BAR)
    print(f"  {SELF} | 运行={RUN} | 轮次={N} | 任务={len(CRON_ENTRIES) + len(SEC_ENTRIES)}")
    print(BAR)
    for idx, (key, _, _, _, _) in enumerate(CRON_ENTRIES):
        print(f"  #{idx}  {key}")
    for idx, (n, _, _) in enumerate(SEC_ENTRIES):
        print(f"  #{len(CRON_ENTRIES) + idx}  @{n}s")
    if CRON_ENTRIES or SEC_ENTRIES:
        print(BAR)

    for i in range(1, N + 1):

        # ① 新版本检测: 存在更新的 run_id → 立即退出让位
        for rid in gh("run", "list", "-w", f"{SELF}.yml", "-s", "in_progress",
                      "--json", "databaseId", "-q", ".[].databaseId", "-R", REPO)[0].splitlines():
            try:
                if rid and int(rid) > RUN:
                    sys.exit(print(f"🛑 #{rid} 更新, 退出"))
            except ValueError:
                pass

        # ② 互守护: 每轮检查兄弟, 死亡则直接重启
        if not alive(PEER):
            print(f"🛡️ {PEER} 已死, 唤醒")
            gh("workflow", "run", f"{PEER}.yml", "-R", REPO)

        # ③ 清理过期锁
        clean_locks()

        # ④ 对齐 30 秒边界 (运维操作在前, 调度在后 → 时间更精确)
        time.sleep(IV - time.time() % IV or 0.1)
        epoch = int(time.time())
        now   = time.gmtime(epoch)
        t     = time.strftime('%H:%M:%S', now)
        m     = time.strftime('%Y%m%d%H%M', now)
        refresh_sha()  # 每轮刷新一次 SHA, 供所有 lock() 复用

        # ⑤a cron 任务: 同一分钟内只调度一次
        if m != last_m:
            last_m = m
            for idx, (key, fields, repo, wf, lock_id) in enumerate(CRON_ENTRIES):
                if match_cron(fields, now):
                    # lock_id 拼接索引, 避免相同 cron 表达式的不同任务共享锁
                    dispatch(i, t, idx, (f"{lock_id}{idx}", m), key, repo, wf)

        # ⑤b 秒级任务: epoch // n 作为时间槽, 本地+锁双重去重
        for j, (n, repo, wf) in enumerate(SEC_ENTRIES):
            slot = epoch // n
            if last_slot.get(j) == slot:
                continue  # 同一时间槽内不重复尝试
            last_slot[j] = slot
            # lock 名称拼接索引, 避免相同间隔的不同任务共享锁
            dispatch(i, t, len(CRON_ENTRIES) + j, (f"s{n}x{j}", str(slot)), f"@{n}s", repo, wf)

    # ══════════════════════════════════════════════════
    #  续期 — 轮次结束后自动启动下一轮
    # ══════════════════════════════════════════════════

    if not alive(SELF):
        print(f"🔄 轮次结束, 续期")
        gh("workflow", "run", f"{SELF}.yml", "-R", REPO)
    clean_locks()
    print(f"✅ {SELF} 完成")
