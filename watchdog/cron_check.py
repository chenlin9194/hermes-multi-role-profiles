#!/usr/bin/env python3
"""
Cron 兜底检查 — 验证 watchdog 主进程存活 + 心跳新鲜度。
在 WSL 环境中替代 systemd watchdog，当主进程异常时自动重启。
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

WATCHDOG_DIR = Path.home() / ".hermes" / "watchdog"
PID_FILE = WATCHDOG_DIR / "watcher.pid"
HEARTBEAT_FILE = WATCHDOG_DIR / "heartbeat"
LOG_FILE = WATCHDOG_DIR / "watchdog.log"
MAX_HEARTBEAT_AGE = 120  # 2分钟未更新视为失联


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{ts} [cron] {msg}\n")


def need_restart(reason):
    log(f"需要重启: {reason}")

    # 杀旧进程（如果有）
    try:
        with open(PID_FILE) as f:
            data = json.load(f)
        old_pid = data.get("pid")
        if old_pid:
            log(f"杀掉旧 PID {old_pid}")
            try:
                os.kill(old_pid, 9)
                time.sleep(1)
            except ProcessLookupError:
                pass
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # 清理残留
    PID_FILE.unlink(missing_ok=True)

    # 启动新 watchdog
    watchdog_script = str(WATCHDOG_DIR / "watchdog.py")
    log(f"启动: {sys.executable} {watchdog_script}")
    try:
        subprocess.Popen(
            [sys.executable, watchdog_script],
            stdout=open(LOG_FILE, "a"),
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        log("✅ watchdog 已启动")
    except Exception as e:
        log(f"❌ 启动失败: {e}")


def main():
    if not PID_FILE.exists():
        return need_restart("PID 文件不存在")

    try:
        with open(PID_FILE) as f:
            data = json.load(f)
        pid = data.get("pid")
        if not pid:
            return need_restart("PID 文件格式异常")
    except (json.JSONDecodeError, KeyError, OSError) as e:
        return need_restart(f"读取 PID 文件失败: {e}")

    # 空信号检查进程存活
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return need_restart(f"PID {pid} 不存在")
    except PermissionError:
        log(f"权限不足，跳过 PID {pid} 检查")
        return

    # 检查心跳新鲜度
    if HEARTBEAT_FILE.exists():
        try:
            hb = float(HEARTBEAT_FILE.read_text().strip())
            age = time.time() - hb
            if age > MAX_HEARTBEAT_AGE:
                return need_restart(f"心跳过期 ({age:.0f}s > {MAX_HEARTBEAT_AGE}s)")
        except (ValueError, OSError) as e:
            return need_restart(f"心跳文件读取失败: {e}")
    else:
        return need_restart("心跳文件不存在")

    # 一切正常
    log(f"✅ 正常 (PID={pid})")


if __name__ == "__main__":
    main()
