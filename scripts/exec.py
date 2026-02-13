"""exec.py — 业务执行器 (env: INTERVAL)"""
import os, time

INTERVAL = os.environ["INTERVAL"]
print(f"🚀 exec | {INTERVAL} | {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC")

if INTERVAL == "1m":
    pass  # TODO: 每分钟业务

if INTERVAL == "5m":
    pass  # TODO: 每5分钟业务
