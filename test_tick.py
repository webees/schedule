"""
test_tick.py — tick.py 纯逻辑函数的单元测试

运行: python3 test_tick.py
零依赖, 仅使用标准库 assert + time
"""
import os, time

# ══════════════════════════════════════════════════
#  导入前设置环境变量 (tick.py 模块级需要)
# ══════════════════════════════════════════════════

os.environ.setdefault("SELF", "tick-a")
os.environ.setdefault("REPO", "test/repo")
os.environ.setdefault("RUN_ID", "1")
os.environ.setdefault("DISPATCH", "")

from tick import match_field, match_cron, parse_dispatch, is_expired, sanitize_key, FIELD_MIN

passed = 0
failed = 0

def test(name, expr, expected):
    """执行单个测试用例"""
    global passed, failed
    if expr == expected:
        passed += 1
    else:
        failed += 1
        print(f"  ❌ {name}: 期望 {expected}, 实际 {expr}")

def make_time(min=0, hour=0, mday=1, mon=1, wday_py=0):
    """
    构造 time.struct_time 用于测试
    wday_py: Python 格式 (0=Mon, 6=Sun)
    """
    return time.struct_time((2026, mon, mday, hour, min, 0, wday_py, 1, 0))

# ══════════════════════════════════════════════════
#  match_field 测试
# ══════════════════════════════════════════════════

print("▶ match_field: 通配符 *")
test("* 匹配 0",       match_field("*", 0),  True)
test("* 匹配 59",      match_field("*", 59), True)
test("* 匹配 31",      match_field("*", 31), True)

print("▶ match_field: 步进 */N (field_min=0, 分/时/周)")
test("*/5 匹配 0",     match_field("*/5", 0),  True)
test("*/5 匹配 5",     match_field("*/5", 5),  True)
test("*/5 匹配 10",    match_field("*/5", 10), True)
test("*/5 匹配 55",    match_field("*/5", 55), True)
test("*/5 不匹配 1",   match_field("*/5", 1),  False)
test("*/5 不匹配 3",   match_field("*/5", 3),  False)
test("*/5 不匹配 59",  match_field("*/5", 59), False)
test("*/15 匹配 0",    match_field("*/15", 0),  True)
test("*/15 匹配 15",   match_field("*/15", 15), True)
test("*/15 匹配 30",   match_field("*/15", 30), True)
test("*/15 匹配 45",   match_field("*/15", 45), True)
test("*/15 不匹配 14", match_field("*/15", 14), False)
test("*/1 匹配任意",   match_field("*/1", 37),  True)
test("*/2 匹配 0",     match_field("*/2", 0),   True)
test("*/2 匹配 2",     match_field("*/2", 2),   True)
test("*/2 不匹配 1",   match_field("*/2", 1),   False)
test("*/2 不匹配 3",   match_field("*/2", 3),   False)
test("*/10 匹配 0",    match_field("*/10", 0),   True)
test("*/10 匹配 50",   match_field("*/10", 50),  True)
test("*/10 不匹配 5",  match_field("*/10", 5),   False)

print("▶ match_field: 步进 */N (field_min=1, 日/月)")
# day-of-month: 1-31, field_min=1
# */3 应匹配 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31
test("*/3 day 匹配 1",   match_field("*/3", 1,  1), True)
test("*/3 day 匹配 4",   match_field("*/3", 4,  1), True)
test("*/3 day 匹配 7",   match_field("*/3", 7,  1), True)
test("*/3 day 匹配 10",  match_field("*/3", 10, 1), True)
test("*/3 day 匹配 31",  match_field("*/3", 31, 1), True)
test("*/3 day 不匹配 2", match_field("*/3", 2,  1), False)
test("*/3 day 不匹配 3", match_field("*/3", 3,  1), False)
test("*/3 day 不匹配 5", match_field("*/3", 5,  1), False)
test("*/3 day 不匹配 6", match_field("*/3", 6,  1), False)
# */2 day: 1, 3, 5, 7, ...
test("*/2 day 匹配 1",   match_field("*/2", 1,  1), True)
test("*/2 day 匹配 3",   match_field("*/2", 3,  1), True)
test("*/2 day 匹配 5",   match_field("*/2", 5,  1), True)
test("*/2 day 匹配 31",  match_field("*/2", 31, 1), True)
test("*/2 day 不匹配 2", match_field("*/2", 2,  1), False)
test("*/2 day 不匹配 4", match_field("*/2", 4,  1), False)
# */1 day: 每天
test("*/1 day 匹配 1",   match_field("*/1", 1,  1), True)
test("*/1 day 匹配 15",  match_field("*/1", 15, 1), True)
# month: 1-12, field_min=1
# */2 month: 1, 3, 5, 7, 9, 11
test("*/2 month 匹配 1",    match_field("*/2", 1,  1), True)
test("*/2 month 匹配 3",    match_field("*/2", 3,  1), True)
test("*/2 month 匹配 11",   match_field("*/2", 11, 1), True)
test("*/2 month 不匹配 2",  match_field("*/2", 2,  1), False)
test("*/2 month 不匹配 12", match_field("*/2", 12, 1), False)
# */6 month: 1, 7
test("*/6 month 匹配 1",   match_field("*/6", 1,  1), True)
test("*/6 month 匹配 7",   match_field("*/6", 7,  1), True)
test("*/6 month 不匹配 6", match_field("*/6", 6,  1), False)

print("▶ match_field: 精确匹配")
test("5 匹配 5",       match_field("5", 5),   True)
test("5 不匹配 4",     match_field("5", 4),   False)
test("5 不匹配 6",     match_field("5", 6),   False)
test("0 匹配 0",       match_field("0", 0),   True)
test("0 不匹配 1",     match_field("0", 1),   False)
test("59 匹配 59",     match_field("59", 59), True)
test("31 匹配 31",     match_field("31", 31), True)

print("▶ match_field: 逗号分隔")
test("1,15 匹配 1",    match_field("1,15", 1),  True)
test("1,15 匹配 15",   match_field("1,15", 15), True)
test("1,15 不匹配 2",  match_field("1,15", 2),  False)
test("1,15 不匹配 14", match_field("1,15", 14), False)
test("0,30 匹配 0",    match_field("0,30", 0),  True)
test("0,30 匹配 30",   match_field("0,30", 30), True)
test("0,30 不匹配 15", match_field("0,30", 15), False)
test("1,2,3 匹配 1",   match_field("1,2,3", 1), True)
test("1,2,3 匹配 2",   match_field("1,2,3", 2), True)
test("1,2,3 匹配 3",   match_field("1,2,3", 3), True)
test("1,2,3 不匹配 4", match_field("1,2,3", 4), False)

print("▶ match_field: 范围 a-b")
test("1-5 匹配 1",     match_field("1-5", 1), True)
test("1-5 匹配 3",     match_field("1-5", 3), True)
test("1-5 匹配 5",     match_field("1-5", 5), True)
test("1-5 不匹配 0",   match_field("1-5", 0), False)
test("1-5 不匹配 6",   match_field("1-5", 6), False)
test("0-0 匹配 0",     match_field("0-0", 0), True)
test("0-0 不匹配 1",   match_field("0-0", 1), False)
test("10-20 匹配 10",  match_field("10-20", 10), True)
test("10-20 匹配 15",  match_field("10-20", 15), True)
test("10-20 匹配 20",  match_field("10-20", 20), True)
test("10-20 不匹配 9", match_field("10-20", 9),  False)
test("10-20 不匹配 21",match_field("10-20", 21), False)

print("▶ match_field: 逗号 + 范围混合")
test("1,3-5,10 匹配 1",   match_field("1,3-5,10", 1),  True)
test("1,3-5,10 匹配 3",   match_field("1,3-5,10", 3),  True)
test("1,3-5,10 匹配 4",   match_field("1,3-5,10", 4),  True)
test("1,3-5,10 匹配 5",   match_field("1,3-5,10", 5),  True)
test("1,3-5,10 匹配 10",  match_field("1,3-5,10", 10), True)
test("1,3-5,10 不匹配 0", match_field("1,3-5,10", 0),  False)
test("1,3-5,10 不匹配 2", match_field("1,3-5,10", 2),  False)
test("1,3-5,10 不匹配 6", match_field("1,3-5,10", 6),  False)
test("1,3-5,10 不匹配 9", match_field("1,3-5,10", 9),  False)
test("0,10-20,30 匹配 0",   match_field("0,10-20,30", 0),  True)
test("0,10-20,30 匹配 15",  match_field("0,10-20,30", 15), True)
test("0,10-20,30 匹配 30",  match_field("0,10-20,30", 30), True)
test("0,10-20,30 不匹配 5", match_field("0,10-20,30", 5),  False)
test("0,10-20,30 不匹配 25",match_field("0,10-20,30", 25), False)

# ══════════════════════════════════════════════════
#  match_cron 测试
# ══════════════════════════════════════════════════

print("▶ match_cron: 全通配符")
test("* * * * * 任意时间",
    match_cron(["*","*","*","*","*"], make_time(30, 12, 15, 6, 2)), True)
test("* * * * * 边界 00:00",
    match_cron(["*","*","*","*","*"], make_time(0, 0, 1, 1, 0)), True)

print("▶ match_cron: 精确时间")
test("0 8 * * * 匹配 08:00",
    match_cron(["0","8","*","*","*"], make_time(0, 8)), True)
test("0 8 * * * 不匹配 08:01",
    match_cron(["0","8","*","*","*"], make_time(1, 8)), False)
test("0 8 * * * 不匹配 09:00",
    match_cron(["0","8","*","*","*"], make_time(0, 9)), False)
test("30 12 * * * 匹配 12:30",
    match_cron(["30","12","*","*","*"], make_time(30, 12)), True)
test("30 12 * * * 不匹配 12:31",
    match_cron(["30","12","*","*","*"], make_time(31, 12)), False)

print("▶ match_cron: 步进 */N")
test("*/5 * * * * 匹配 :00",
    match_cron(["*/5","*","*","*","*"], make_time(0)), True)
test("*/5 * * * * 匹配 :05",
    match_cron(["*/5","*","*","*","*"], make_time(5)), True)
test("*/5 * * * * 匹配 :55",
    match_cron(["*/5","*","*","*","*"], make_time(55)), True)
test("*/5 * * * * 不匹配 :03",
    match_cron(["*/5","*","*","*","*"], make_time(3)), False)
test("*/15 * * * * 匹配 :00",
    match_cron(["*/15","*","*","*","*"], make_time(0)), True)
test("*/15 * * * * 匹配 :45",
    match_cron(["*/15","*","*","*","*"], make_time(45)), True)
test("*/15 * * * * 不匹配 :10",
    match_cron(["*/15","*","*","*","*"], make_time(10)), False)

print("▶ match_cron: 星期 (cron: 0=Sun, Python: 0=Mon)")
# Python wday: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
# Cron wday:   1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 0=Sun
# 转换: (py_wday + 1) % 7
test("* * * * 1 匹配周一 (py=0)",
    match_cron(["*","*","*","*","1"], make_time(wday_py=0)), True)
test("* * * * 1 不匹配周二 (py=1)",
    match_cron(["*","*","*","*","1"], make_time(wday_py=1)), False)
test("* * * * 0 匹配周日 (py=6)",
    match_cron(["*","*","*","*","0"], make_time(wday_py=6)), True)
test("* * * * 0 不匹配周一 (py=0)",
    match_cron(["*","*","*","*","0"], make_time(wday_py=0)), False)
test("* * * * 5 匹配周五 (py=4)",
    match_cron(["*","*","*","*","5"], make_time(wday_py=4)), True)
test("* * * * 6 匹配周六 (py=5)",
    match_cron(["*","*","*","*","6"], make_time(wday_py=5)), True)
test("* * * * 1-5 匹配周一到周五 (py=0)",
    match_cron(["*","*","*","*","1-5"], make_time(wday_py=0)), True)
test("* * * * 1-5 匹配周五 (py=4)",
    match_cron(["*","*","*","*","1-5"], make_time(wday_py=4)), True)
test("* * * * 1-5 不匹配周六 (py=5)",
    match_cron(["*","*","*","*","1-5"], make_time(wday_py=5)), False)
test("* * * * 1-5 不匹配周日 (py=6)",
    match_cron(["*","*","*","*","1-5"], make_time(wday_py=6)), False)

print("▶ match_cron: 日/月 步进偏移")
# */3 day: 1, 4, 7, 10, ...
test("* * */3 * * 匹配 day=1",
    match_cron(["*","*","*/3","*","*"], make_time(mday=1)), True)
test("* * */3 * * 匹配 day=4",
    match_cron(["*","*","*/3","*","*"], make_time(mday=4)), True)
test("* * */3 * * 匹配 day=7",
    match_cron(["*","*","*/3","*","*"], make_time(mday=7)), True)
test("* * */3 * * 不匹配 day=2",
    match_cron(["*","*","*/3","*","*"], make_time(mday=2)), False)
test("* * */3 * * 不匹配 day=3",
    match_cron(["*","*","*/3","*","*"], make_time(mday=3)), False)
# */2 month: 1, 3, 5, 7, 9, 11
test("* * * */2 * 匹配 month=1",
    match_cron(["*","*","*","*/2","*"], make_time(mon=1)), True)
test("* * * */2 * 匹配 month=3",
    match_cron(["*","*","*","*/2","*"], make_time(mon=3)), True)
test("* * * */2 * 匹配 month=11",
    match_cron(["*","*","*","*/2","*"], make_time(mon=11)), True)
test("* * * */2 * 不匹配 month=2",
    match_cron(["*","*","*","*/2","*"], make_time(mon=2)), False)
test("* * * */2 * 不匹配 month=12",
    match_cron(["*","*","*","*/2","*"], make_time(mon=12)), False)

print("▶ match_cron: 组合表达式")
# 每周一到周五 08:00
test("0 8 * * 1-5 匹配 Mon 08:00",
    match_cron(["0","8","*","*","1-5"], make_time(0, 8, wday_py=0)), True)
test("0 8 * * 1-5 不匹配 Sun 08:00",
    match_cron(["0","8","*","*","1-5"], make_time(0, 8, wday_py=6)), False)
test("0 8 * * 1-5 不匹配 Mon 09:00",
    match_cron(["0","8","*","*","1-5"], make_time(0, 9, wday_py=0)), False)
# 每月 1号和 15号 00:00
test("0 0 1,15 * * 匹配 day=1 00:00",
    match_cron(["0","0","1,15","*","*"], make_time(0, 0, 1)), True)
test("0 0 1,15 * * 匹配 day=15 00:00",
    match_cron(["0","0","1,15","*","*"], make_time(0, 0, 15)), True)
test("0 0 1,15 * * 不匹配 day=2 00:00",
    match_cron(["0","0","1,15","*","*"], make_time(0, 0, 2)), False)
# 每季度第一天 09:00 (1月/4月/7月/10月 1日)
test("0 9 1 1,4,7,10 * 匹配 Jan 1 09:00",
    match_cron(["0","9","1","1,4,7,10","*"], make_time(0, 9, 1, 1)), True)
test("0 9 1 1,4,7,10 * 匹配 Oct 1 09:00",
    match_cron(["0","9","1","1,4,7,10","*"], make_time(0, 9, 1, 10)), True)
test("0 9 1 1,4,7,10 * 不匹配 Feb 1 09:00",
    match_cron(["0","9","1","1,4,7,10","*"], make_time(0, 9, 1, 2)), False)

# ══════════════════════════════════════════════════
#  parse_dispatch 测试
# ══════════════════════════════════════════════════

def parse_with(dispatch_str):
    """临时设置 DISPATCH 环境变量并解析"""
    old = os.environ.get("DISPATCH", "")
    os.environ["DISPATCH"] = dispatch_str
    result = parse_dispatch()
    os.environ["DISPATCH"] = old
    return result

print("▶ parse_dispatch: 空输入")
cron, sec = parse_with("")
test("空字符串 cron 为空", len(cron), 0)
test("空字符串 sec 为空",  len(sec),  0)

print("▶ parse_dispatch: 标准 crontab")
cron, sec = parse_with("*/5 * * * * owner/repo check.yml")
test("单条 cron 数量",     len(cron), 1)
test("cron key",           cron[0][0], "*/5 * * * *")
test("cron fields",        cron[0][1], ["*/5", "*", "*", "*", "*"])
test("cron repo",          cron[0][2], "owner/repo")
test("cron wf",            cron[0][3], "check.yml")
test("cron lock_id 不含特殊字符", cron[0][4].isalnum(), True)

print("▶ parse_dispatch: 秒级语法")
cron, sec = parse_with("@30s owner/repo poll.yml")
test("单条 sec 数量",     len(sec), 1)
test("sec 间隔",          sec[0][0], 30)
test("sec repo",          sec[0][1], "owner/repo")
test("sec wf",            sec[0][2], "poll.yml")

print("▶ parse_dispatch: 多条混合")
dispatch = "\n".join([
    "*/5 * * * * owner/repo1 check.yml",
    "@30s owner/repo2 poll.yml",
    "0 8 * * * owner/repo3 daily.yml",
    "@10s owner/repo4 fast.yml",
])
cron, sec = parse_with(dispatch)
test("混合 cron 数量", len(cron), 2)
test("混合 sec 数量",  len(sec),  2)
test("cron[0] key",    cron[0][0], "*/5 * * * *")
test("cron[1] key",    cron[1][0], "0 8 * * *")
test("sec[0] 间隔",   sec[0][0], 30)
test("sec[1] 间隔",   sec[1][0], 10)

print("▶ parse_dispatch: 空行和注释")
dispatch = "\n".join([
    "# 这是一行注释",
    "",
    "  ",
    "*/5 * * * * owner/repo check.yml",
    "# 另一行注释",
    "@30s owner/repo poll.yml",
    "",
])
cron, sec = parse_with(dispatch)
test("过滤后 cron 数量", len(cron), 1)
test("过滤后 sec 数量",  len(sec),  1)

print("▶ parse_dispatch: 无效输入")
# 字段数不对
cron, sec = parse_with("*/5 * * * owner/repo check.yml")  # 6 字段
test("6字段被跳过 cron", len(cron), 0)
test("6字段被跳过 sec",  len(sec),  0)
# @Ns 非数字
cron, sec = parse_with("@abcs owner/repo poll.yml")
test("@abcs 被跳过 sec", len(sec), 0)
# 只有 2 个字段
cron, sec = parse_with("@30s owner/repo")  # 缺工作流
test("2字段被跳过 sec", len(sec), 0)

print("▶ parse_dispatch: lock_id 唯一性")
dispatch = "\n".join([
    "*/5 * * * * owner/repo1 a.yml",
    "*/5 * * * * owner/repo2 b.yml",
])
cron, sec = parse_with(dispatch)
test("相同表达式 lock_id 相同", cron[0][4], cron[1][4])
# (lock_id 自身相同, 但主循环中拼接 idx 后不同 → 这是设计正确性)

print("▶ parse_dispatch: 各种秒级间隔")
dispatch = "\n".join([
    "@1s owner/repo a.yml",
    "@10s owner/repo b.yml",
    "@30s owner/repo c.yml",
    "@60s owner/repo d.yml",
    "@300s owner/repo e.yml",
])
cron, sec = parse_with(dispatch)
test("sec 数量", len(sec), 5)
test("@1s",   sec[0][0], 1)
test("@10s",  sec[1][0], 10)
test("@30s",  sec[2][0], 30)
test("@60s",  sec[3][0], 60)
test("@300s", sec[4][0], 300)

# ══════════════════════════════════════════════════
#  FIELD_MIN 常量验证
# ══════════════════════════════════════════════════

print("▶ FIELD_MIN 常量")
test("分钟 min=0", FIELD_MIN[0], 0)
test("小时 min=0", FIELD_MIN[1], 0)
test("日 min=1",   FIELD_MIN[2], 1)
test("月 min=1",   FIELD_MIN[3], 1)
test("周 min=0",   FIELD_MIN[4], 0)
test("长度=5",     len(FIELD_MIN), 5)

# ══════════════════════════════════════════════════
#  边界条件 / 回归测试
# ══════════════════════════════════════════════════

print("▶ 回归: */N day-of-month 偏移 (曾有 bug)")
# 之前 value % N == 0 对 day=1 永远不匹配 */3
test("*/3 day=1 (必须匹配)", match_field("*/3", 1, 1), True)
test("*/3 day=3 (不应匹配)", match_field("*/3", 3, 1), False)
test("*/5 day=1 (必须匹配)", match_field("*/5", 1, 1), True)
test("*/5 day=6 (必须匹配)", match_field("*/5", 6, 1), True)
test("*/5 day=11 (必须匹配)",match_field("*/5", 11,1), True)
test("*/5 day=5 (不应匹配)", match_field("*/5", 5, 1), False)

print("▶ 回归: 多条 @30s 不应互相吞掉 (曾有 bug)")
dispatch = "\n".join([
    "@30s owner/repo1 a.yml",
    "@30s owner/repo2 b.yml",
])
cron, sec = parse_with(dispatch)
test("两条 @30s 都被解析", len(sec), 2)
test("sec[0] repo", sec[0][1], "owner/repo1")
test("sec[1] repo", sec[1][1], "owner/repo2")
# (运行时 last_slot 用 j 索引区分, 不再冲突)

print("▶ 回归: 相同 cron 表达式不同目标 (曾有 bug)")
dispatch = "\n".join([
    "*/5 * * * * owner/repo1 a.yml",
    "*/5 * * * * owner/repo2 b.yml",
])
cron, sec = parse_with(dispatch)
test("两条都被解析", len(cron), 2)
test("repo 不同", cron[0][2] != cron[1][2], True)
# (运行时 lock_id 拼接 idx → lock_id0 vs lock_id1, 不再冲突)

print("▶ 边界: 午夜跨天")
test("59 23 * * * 匹配 23:59",
    match_cron(["59","23","*","*","*"], make_time(59, 23)), True)
test("0 0 * * * 匹配 00:00",
    match_cron(["0","0","*","*","*"], make_time(0, 0)), True)

print("▶ 边界: 月末")
test("* * 31 * * 匹配 day=31",
    match_cron(["*","*","31","*","*"], make_time(mday=31)), True)
test("* * 31 * * 不匹配 day=30",
    match_cron(["*","*","31","*","*"], make_time(mday=30)), False)

print("▶ 边界: 12月")
test("* * * 12 * 匹配 month=12",
    match_cron(["*","*","*","12","*"], make_time(mon=12)), True)
test("* * * 12 * 不匹配 month=11",
    match_cron(["*","*","*","12","*"], make_time(mon=11)), False)

# ══════════════════════════════════════════════════
#  is_expired 测试
# ══════════════════════════════════════════════════

NOW_EPOCH = 1708000000  # 固定测试时间点
NOW_MIN   = "202602150800"

print("▶ is_expired: cron 锁 (12位时间戳)")
test("过去的分钟已过期",     is_expired("xx5xxxxxxx0-202602150759", NOW_EPOCH, NOW_MIN), True)
test("很早的时间已过期",     is_expired("xx5xxxxxxx0-202602140000", NOW_EPOCH, NOW_MIN), True)
test("当前分钟未过期",       is_expired("xx5xxxxxxx0-202602150800", NOW_EPOCH, NOW_MIN), False)
test("未来分钟未过期",       is_expired("xx5xxxxxxx0-202602150801", NOW_EPOCH, NOW_MIN), False)
test("刚过去1分钟已过期",   is_expired("lockid1-202602150759", NOW_EPOCH, NOW_MIN), True)

print("▶ is_expired: sec 锁 (s{N}x{J} 格式)")
# s30x0: 间隔30秒, slot = epoch // 30
# 过期条件: slot * 30 < now_epoch - 300
old_slot = (NOW_EPOCH - 600) // 30  # 10分钟前的 slot
new_slot = NOW_EPOCH // 30           # 当前 slot
recent_slot = (NOW_EPOCH - 100) // 30  # 100秒前的 slot

test("10分钟前 s30 已过期",  is_expired(f"s30x0-{old_slot}", NOW_EPOCH, NOW_MIN), True)
test("当前 s30 未过期",      is_expired(f"s30x0-{new_slot}", NOW_EPOCH, NOW_MIN), False)
test("100秒前 s30 未过期",   is_expired(f"s30x0-{recent_slot}", NOW_EPOCH, NOW_MIN), False)

# s10x1: 间隔10秒
old_slot_10 = (NOW_EPOCH - 600) // 10
new_slot_10 = NOW_EPOCH // 10
test("10分钟前 s10 已过期",  is_expired(f"s10x1-{old_slot_10}", NOW_EPOCH, NOW_MIN), True)
test("当前 s10 未过期",      is_expired(f"s10x1-{new_slot_10}", NOW_EPOCH, NOW_MIN), False)

# s60x2: 间隔60秒
old_slot_60 = (NOW_EPOCH - 600) // 60
new_slot_60 = NOW_EPOCH // 60
test("10分钟前 s60 已过期",  is_expired(f"s60x2-{old_slot_60}", NOW_EPOCH, NOW_MIN), True)
test("当前 s60 未过期",      is_expired(f"s60x2-{new_slot_60}", NOW_EPOCH, NOW_MIN), False)

# s300x0: 间隔300秒
old_slot_300 = (NOW_EPOCH - 900) // 300
new_slot_300 = NOW_EPOCH // 300
test("15分钟前 s300 已过期", is_expired(f"s300x0-{old_slot_300}", NOW_EPOCH, NOW_MIN), True)
test("当前 s300 未过期",     is_expired(f"s300x0-{new_slot_300}", NOW_EPOCH, NOW_MIN), False)

print("▶ is_expired: 旧格式兼容 (s{N} 无 x)")
old_slot_s30 = (NOW_EPOCH - 600) // 30
new_slot_s30 = NOW_EPOCH // 30
test("旧格式 s30 过期锁",   is_expired(f"s30-{old_slot_s30}", NOW_EPOCH, NOW_MIN), True)
test("旧格式 s30 当前锁",   is_expired(f"s30-{new_slot_s30}", NOW_EPOCH, NOW_MIN), False)

print("▶ is_expired: 无法解析的锁名")
test("非标准锁名视为过期",  is_expired("unknown-12345", NOW_EPOCH, NOW_MIN), True)
test("空名称视为过期",      is_expired("-12345", NOW_EPOCH, NOW_MIN), True)

print("▶ is_expired: 非数字 tag")
test("非数字 tag 不过期",   is_expired("s30x0-abc", NOW_EPOCH, NOW_MIN), False)
test("空 tag 不过期",       is_expired("s30x0-", NOW_EPOCH, NOW_MIN), False)
test("无分隔符不过期",      is_expired("s30x0", NOW_EPOCH, NOW_MIN), False)

print("▶ is_expired: 边界 - 恰好 5 分钟")
boundary_slot = (NOW_EPOCH - 300) // 30  # 恰好 5 分钟前
# slot * 30 = (NOW_EPOCH - 300) // 30 * 30 ≈ NOW_EPOCH - 300
# 条件: slot * 30 < now_epoch - 300 → 取决于整除余数
boundary_val = boundary_slot * 30
test("恰好5分钟边界 (精确计算)",
    is_expired(f"s30x0-{boundary_slot}", NOW_EPOCH, NOW_MIN),
    boundary_val < NOW_EPOCH - 300)
# 5分钟+1秒 → 肯定过期
definite_old = (NOW_EPOCH - 301) // 30
test("5分钟+1秒 过期",
    is_expired(f"s30x0-{definite_old}", NOW_EPOCH, NOW_MIN), True)

# ══════════════════════════════════════════════════
#  sanitize_key 测试
# ══════════════════════════════════════════════════

print("▶ sanitize_key: 基本转换")
# "*/5 * * * *" → 每个非alnumchar变x: * / 5 空 * 空 * 空 * 空 * = "xx5xxxxxxxx" (11字符)
test("*/5 * * * *",     sanitize_key("*/5 * * * *"),     "xx5xxxxxxxx")
test("0 8 * * *",       sanitize_key("0 8 * * *"),       "0x8xxxxxx")
test("0 9 * * 1",       sanitize_key("0 9 * * 1"),       "0x9xxxxx1")
test("*/15 * * * *",    sanitize_key("*/15 * * * *"),    "xx15xxxxxxxx")
test("0 0 1,15 * *",   sanitize_key("0 0 1,15 * *"),   "0x0x1x15xxxx")

print("▶ sanitize_key: 纯字母数字不变")
test("纯数字",          sanitize_key("12345"),           "12345")
test("纯字母",          sanitize_key("abc"),             "abc")
test("混合",            sanitize_key("abc123"),          "abc123")

print("▶ sanitize_key: 特殊字符全替换")
test("斜杠",            sanitize_key("a/b"),             "axb")
test("点",              sanitize_key("a.b"),             "axb")
test("连字符",          sanitize_key("a-b"),             "axb")
test("多个特殊字符",    sanitize_key("*/* * * * *"),     "xxxxxxxxxxx")

# ══════════════════════════════════════════════════
#  模拟运行测试 — 快进时钟验证调度正确性
# ══════════════════════════════════════════════════

from tick import scan_round

def simulate(cron_entries, sec_entries, duration_sec, interval=30):
    """
    模拟运行调度循环, 快进时钟
    返回 {idx: fire_count} 统计
    """
    # 起始时间: 2026-02-15 00:00:00 UTC (整点, 方便验证)
    base_epoch = 1771027200  # 固定整点
    fires = {}
    last_m = None
    last_slot = {}

    def on_fire(idx, show, repo, wf):
        fires[idx] = fires.get(idx, 0) + 1

    rounds = duration_sec // interval
    for i in range(rounds):
        epoch = base_epoch + i * interval
        last_m, last_slot = scan_round(
            epoch, last_m, last_slot, cron_entries, sec_entries, on_fire)

    return fires

print("▶ 模拟: 5分钟 (10轮) — */1 * * * * 每分钟触发")
cron = [("*/1 * * * *", ["*/1","*","*","*","*"], "o/r", "a.yml", "xx1xxxxxxxx")]
fires = simulate(cron, [], 300)
# 5分钟 = 10轮 (0s, 30s, 60s, 90s, 120s, 150s, 180s, 210s, 240s, 270s)
# 分钟变化: :00, :00(dup), :01, :01(dup), :02, :02(dup), :03, :03(dup), :04, :04(dup)
# 每分钟只触发一次 → 5次
test("*/1 5分钟触发5次", fires.get(0, 0), 5)

print("▶ 模拟: 1小时 (120轮) — */5 * * * *")
cron = [("*/5 * * * *", ["*/5","*","*","*","*"], "o/r", "a.yml", "xx5xxxxxxxx")]
fires = simulate(cron, [], 3600)
# 1小时中 */5 匹配: :00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55 = 12次
test("*/5 1小时触发12次", fires.get(0, 0), 12)

print("▶ 模拟: 1小时 — */15 * * * *")
cron = [("*/15 * * * *", ["*/15","*","*","*","*"], "o/r", "a.yml", "xx15xxxxxxxx")]
fires = simulate(cron, [], 3600)
# :00, :15, :30, :45 = 4次
test("*/15 1小时触发4次", fires.get(0, 0), 4)

print("▶ 模拟: 1小时 — 0 * * * * (整点)")
cron = [("0 * * * *", ["0","*","*","*","*"], "o/r", "a.yml", "0xxxxxxxx")]
fires = simulate(cron, [], 3600)
# 只有 :00 匹配 = 1次
test("整点1小时触发1次", fires.get(0, 0), 1)

print("▶ 模拟: 5分钟 — @30s 每30秒")
sec = [(30, "o/r", "a.yml")]
fires = simulate([], sec, 300)
# 10轮, 每轮 slot 变化 → 10次
test("@30s 5分钟触发10次", fires.get(0, 0), 10)

print("▶ 模拟: 5分钟 — @60s 每60秒")
sec = [(60, "o/r", "a.yml")]
fires = simulate([], sec, 300)
# 10轮 (0s,30s,60s,90s,...270s), slot=epoch//60 每两轮变化 → 5次
test("@60s 5分钟触发5次", fires.get(0, 0), 5)

print("▶ 模拟: 5分钟 — @10s 每10秒 (interval=30s)")
sec = [(10, "o/r", "a.yml")]
fires = simulate([], sec, 300)
# 虽然 @10s 要求每10秒, 但循环间隔30s, 每轮 slot 变化 → 10次
test("@10s 5分钟触发10次", fires.get(0, 0), 10)

print("▶ 模拟: 1小时 — 混合 cron + sec")
cron = [("*/5 * * * *", ["*/5","*","*","*","*"], "o/r", "a.yml", "xx5xxxxxxxx")]
sec  = [(30, "o/r", "b.yml")]
fires = simulate(cron, sec, 3600)
test("混合: cron */5 触发12次",  fires.get(0, 0), 12)
test("混合: sec @30s 触发120次", fires.get(1, 0), 120)

print("▶ 模拟: 1小时 — 多条 cron")
cron = [
    ("*/5 * * * *",  ["*/5","*","*","*","*"],  "o/r1", "a.yml", "id0"),
    ("*/15 * * * *", ["*/15","*","*","*","*"], "o/r2", "b.yml", "id1"),
    ("0 * * * *",    ["0","*","*","*","*"],     "o/r3", "c.yml", "id2"),
]
fires = simulate(cron, [], 3600)
test("多cron: */5 触发12次",  fires.get(0, 0), 12)
test("多cron: */15 触发4次",  fires.get(1, 0), 4)
test("多cron: 整点 触发1次",  fires.get(2, 0), 1)

print("▶ 模拟: 1小时 — 多条 @Ns (相同间隔)")
sec = [
    (30, "o/r1", "a.yml"),
    (30, "o/r2", "b.yml"),
]
fires = simulate([], sec, 3600)
test("多@30s[0] 触发120次", fires.get(0, 0), 120)
test("多@30s[1] 触发120次", fires.get(1, 0), 120)

print("▶ 模拟: 1小时 — 多条 @Ns (不同间隔)")
sec = [
    (30,  "o/r1", "a.yml"),
    (60,  "o/r2", "b.yml"),
    (300, "o/r3", "c.yml"),
]
fires = simulate([], sec, 3600)
test("@30s 触发120次",  fires.get(0, 0), 120)
test("@60s 触发60次",   fires.get(1, 0), 60)
test("@300s 触发12次",  fires.get(2, 0), 12)

print("▶ 模拟: 24小时 — 0 8 * * * (每天8点)")
cron = [("0 8 * * *", ["0","8","*","*","*"], "o/r", "a.yml", "0x8xxxxxx")]
fires = simulate(cron, [], 86400)
test("每天8点触发1次", fires.get(0, 0), 1)

print("▶ 模拟: 24小时 — 0 */6 * * *")
cron = [("0 */6 * * *", ["0","*/6","*","*","*"], "o/r", "a.yml", "0xx6xxxxxxxx")]
fires = simulate(cron, [], 86400)
# 0:00, 6:00, 12:00, 18:00 = 4次
test("*/6h 24小时触发4次", fires.get(0, 0), 4)

print("▶ 模拟: cron 去重 — 同一分钟两轮不重复")
cron = [("* * * * *", ["*","*","*","*","*"], "o/r", "a.yml", "xxxxxxxxx")]
fires = simulate(cron, [], 120)
# 120秒 = 4轮 (0s, 30s, 60s, 90s), 分钟 :00, :00(dup), :01, :01(dup) → 2次
test("每分钟去重: 4轮仅触发2次", fires.get(0, 0), 2)

print("▶ 模拟: sec 去重 — 同一 slot 不重复")
sec = [(60, "o/r", "a.yml")]
fires = simulate([], sec, 120)
# 4轮, slot 每两轮变一次 → 2次
test("@60s 去重: 4轮仅触发2次", fires.get(0, 0), 2)

print("▶ 模拟: 零任务 — 空 DISPATCH")
fires = simulate([], [], 3600)
test("零任务无触发", len(fires), 0)

print("▶ 端到端: DISPATCH → parse → simulate (1小时)")
os.environ["DISPATCH"] = "\n".join([
    "# 每5分钟检查",
    "*/5 * * * *  owner/repo1  check.yml",
    "",
    "# 每30秒轮询",
    "@30s  owner/repo2  poll.yml",
    "",
    "# 每天8点日报",
    "0 8 * * *  owner/repo3  daily.yml",
    "",
    "# 每60秒心跳",
    "@60s  owner/repo4  heartbeat.yml",
])
cron, sec = parse_dispatch()
fires = simulate(cron, sec, 3600)
test("e2e cron */5 触发12次",    fires.get(0, 0), 12)
test("e2e cron 0 8 不触发(起始0点)", fires.get(1, 0), 0)
test("e2e sec @30s 触发120次",   fires.get(len(cron) + 0, 0), 120)
test("e2e sec @60s 触发60次",    fires.get(len(cron) + 1, 0), 60)
# 恢复空 DISPATCH
os.environ["DISPATCH"] = ""

print("▶ 端到端: 复杂 DISPATCH (24小时)")
os.environ["DISPATCH"] = "\n".join([
    "*/5 * * * *   owner/repo1  check.yml",
    "*/15 * * * *  owner/repo2  report.yml",
    "0 */6 * * *   owner/repo3  sync.yml",
    "0 8 * * *     owner/repo4  daily.yml",
    "@30s          owner/repo5  poll.yml",
    "@300s         owner/repo6  slow.yml",
])
cron, sec = parse_dispatch()
fires = simulate(cron, sec, 86400)
test("e2e 24h */5 触发288次",    fires.get(0, 0), 288)   # 12/h × 24h
test("e2e 24h */15 触发96次",    fires.get(1, 0), 96)    # 4/h × 24h
test("e2e 24h */6h 触发4次",     fires.get(2, 0), 4)     # 0,6,12,18
test("e2e 24h 每天8点 触发1次",  fires.get(3, 0), 1)
test("e2e 24h @30s 触发2880次",  fires.get(len(cron) + 0, 0), 2880)  # 120/h × 24h
test("e2e 24h @300s 触发288次",  fires.get(len(cron) + 1, 0), 288)   # 12/h × 24h
os.environ["DISPATCH"] = ""

print("▶ 端到端: 只有注释和空行")
os.environ["DISPATCH"] = "# nothing\n\n  \n# also nothing"
cron, sec = parse_dispatch()
fires = simulate(cron, sec, 3600)
test("e2e 纯注释无触发", len(fires), 0)
os.environ["DISPATCH"] = ""

# ══════════════════════════════════════════════════
#  新增: match_field 边界强化
# ══════════════════════════════════════════════════

print("▶ match_field: 大步进")
test("*/30 匹配 0",     match_field("*/30", 0),  True)
test("*/30 匹配 30",    match_field("*/30", 30), True)
test("*/30 不匹配 15",  match_field("*/30", 15), False)
test("*/30 不匹配 59",  match_field("*/30", 59), False)
test("*/59 匹配 0",     match_field("*/59", 0),  True)
test("*/59 匹配 59",    match_field("*/59", 59), True)
test("*/59 不匹配 30",  match_field("*/59", 30), False)

print("▶ match_field: 单值范围")
test("5-5 匹配 5",      match_field("5-5", 5),   True)
test("5-5 不匹配 4",    match_field("5-5", 4),   False)
test("5-5 不匹配 6",    match_field("5-5", 6),   False)

print("▶ match_field: 多范围组合")
test("1-3,7-9 匹配 1",  match_field("1-3,7-9", 1),  True)
test("1-3,7-9 匹配 2",  match_field("1-3,7-9", 2),  True)
test("1-3,7-9 匹配 8",  match_field("1-3,7-9", 8),  True)
test("1-3,7-9 不匹配 5",match_field("1-3,7-9", 5),  False)

# ══════════════════════════════════════════════════
#  新增: match_cron 更多场景
# ══════════════════════════════════════════════════

print("▶ match_cron: 每半小时 0,30 * * * *")
test("0,30 匹配 :00",
    match_cron(["0,30","*","*","*","*"], make_time(0, 12)), True)
test("0,30 匹配 :30",
    match_cron(["0,30","*","*","*","*"], make_time(30, 12)), True)
test("0,30 不匹配 :15",
    match_cron(["0,30","*","*","*","*"], make_time(15, 12)), False)

print("▶ match_cron: 周末 0,6")
test("* * * * 0,6 匹配周六 (py=5)",
    match_cron(["*","*","*","*","0,6"], make_time(wday_py=5)), True)
test("* * * * 0,6 匹配周日 (py=6)",
    match_cron(["*","*","*","*","0,6"], make_time(wday_py=6)), True)
test("* * * * 0,6 不匹配周三 (py=2)",
    match_cron(["*","*","*","*","0,6"], make_time(wday_py=2)), False)

print("▶ match_cron: 年末 12月31日 23:59")
test("59 23 31 12 * 匹配年末",
    match_cron(["59","23","31","12","*"], make_time(59, 23, 31, 12)), True)
test("59 23 31 12 * 不匹配 12月30日",
    match_cron(["59","23","31","12","*"], make_time(59, 23, 30, 12)), False)

print("▶ match_cron: 多小时 */8")
test("0 */8 * * * 匹配 00:00",
    match_cron(["0","*/8","*","*","*"], make_time(0, 0)), True)
test("0 */8 * * * 匹配 08:00",
    match_cron(["0","*/8","*","*","*"], make_time(0, 8)), True)
test("0 */8 * * * 匹配 16:00",
    match_cron(["0","*/8","*","*","*"], make_time(0, 16)), True)
test("0 */8 * * * 不匹配 04:00",
    match_cron(["0","*/8","*","*","*"], make_time(0, 4)), False)

# ══════════════════════════════════════════════════
#  新增: is_expired 强化
# ══════════════════════════════════════════════════

print("▶ is_expired: cron 同分钟边界")
# 当前分钟的锁不应过期
test("cron 当前分钟 (相等) 不过期",
    is_expired("id-202602150800", NOW_EPOCH, "202602150800"), False)
# 下一分钟的锁不应过期
test("cron 下一分钟 不过期",
    is_expired("id-202602150801", NOW_EPOCH, "202602150800"), False)

print("▶ is_expired: 极短间隔 s1x0")
old_s1 = (NOW_EPOCH - 600) // 1
new_s1 = NOW_EPOCH // 1
test("s1x0 10分钟前 过期", is_expired(f"s1x0-{old_s1}", NOW_EPOCH, NOW_MIN), True)
test("s1x0 当前 未过期",   is_expired(f"s1x0-{new_s1}", NOW_EPOCH, NOW_MIN), False)

print("▶ is_expired: 大间隔 s3600x0")
old_s3600 = (NOW_EPOCH - 7200) // 3600
new_s3600 = NOW_EPOCH // 3600
test("s3600x0 2小时前 过期", is_expired(f"s3600x0-{old_s3600}", NOW_EPOCH, NOW_MIN), True)
# 大间隔: 当前 slot 起始可能 >300s 前, 动态计算期望
new_expected = new_s3600 * 3600 < NOW_EPOCH - 300
test("s3600x0 当前 (动态验证)", is_expired(f"s3600x0-{new_s3600}", NOW_EPOCH, NOW_MIN), new_expected)

print("▶ is_expired: 多索引 s30x5")
old_s30_5 = (NOW_EPOCH - 600) // 30
new_s30_5 = NOW_EPOCH // 30
test("s30x5 过期", is_expired(f"s30x5-{old_s30_5}", NOW_EPOCH, NOW_MIN), True)
test("s30x5 当前", is_expired(f"s30x5-{new_s30_5}", NOW_EPOCH, NOW_MIN), False)

# ══════════════════════════════════════════════════
#  新增: sanitize_key 强化
# ══════════════════════════════════════════════════

print("▶ sanitize_key: 边界")
test("空字符串",       sanitize_key(""),           "")
test("单字符 *",       sanitize_key("*"),           "x")
test("单字符 0",       sanitize_key("0"),           "0")
test("逗号表达式",     sanitize_key("1,15"),        "1x15")
test("范围+逗号",      sanitize_key("0 9 1-5 1,7 *"), "0x9x1x5x1x7xx")

# ══════════════════════════════════════════════════
#  新增: parse_dispatch 强化
# ══════════════════════════════════════════════════

print("▶ parse_dispatch: 多余空格")
cron, sec = parse_with("*/5  *  *  *  *   owner/repo   check.yml")
# split() 按任意空白分割, 多余空格应被忽略
test("多余空格也是7段", len(cron), 1)

print("▶ parse_dispatch: 超多字段被跳过")
cron, sec = parse_with("*/5 * * * * * * * owner/repo check.yml")
test("10字段跳过 cron", len(cron), 0)

print("▶ parse_dispatch: @0s 被解析为0")
cron, sec = parse_with("@0s owner/repo a.yml")
test("@0s 间隔为0", len(sec), 1)
test("@0s 值",      sec[0][0], 0)

print("▶ parse_dispatch: 大量任务")
lines = [f"*/5 * * * * owner/repo{i} w{i}.yml" for i in range(50)]
cron, sec = parse_with("\n".join(lines))
test("50条 cron 全解析", len(cron), 50)

# ══════════════════════════════════════════════════
#  新增: 模拟强化
# ══════════════════════════════════════════════════

print("▶ 模拟: 30分钟 — 0,30 * * * *")
cron = [("0,30 * * * *", ["0,30","*","*","*","*"], "o/r", "a.yml", "0x30xxxxxxxx")]
fires = simulate(cron, [], 3600)
# :00 和 :30 各触发1次 = 2次/小时
test("0,30每小时触发2次", fires.get(0, 0), 2)

print("▶ 模拟: 7天 — 周一 0 9 * * 1")
# base_epoch 2026-02-15 00:00:00 是周日 (wday_py=6)
# 周一是 +1天, 只触发1次
cron = [("0 9 * * 1", ["0","9","*","*","1"], "o/r", "a.yml", "0x9xxxxx1")]
fires = simulate(cron, [], 7 * 86400)
test("周一cron 7天触发1次", fires.get(0, 0), 1)

print("▶ 模拟: 48小时 — 0 8 * * * (应触发2天)")
cron = [("0 8 * * *", ["0","8","*","*","*"], "o/r", "a.yml", "0x8xxxxxx")]
fires = simulate(cron, [], 172800)
test("每天8点 48小时触发2次", fires.get(0, 0), 2)

print("▶ 模拟: 大间隔 sec — @3600s (每小时)")
sec = [(3600, "o/r", "a.yml")]
fires = simulate([], sec, 86400)
# 86400/30 = 2880轮, slot = epoch//3600, 每120轮变一次 → 24次
test("@3600s 24小时触发24次", fires.get(0, 0), 24)

# ══════════════════════════════════════════════════
#  结果汇总
# ══════════════════════════════════════════════════

print(BAR := "═" * 50)
total = passed + failed
print(f"  测试完成: {total} 个用例, ✅ {passed} 通过, ❌ {failed} 失败")
print(BAR)
exit(failed)
