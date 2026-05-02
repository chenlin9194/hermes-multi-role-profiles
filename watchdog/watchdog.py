#!/usr/bin/env python3
"""
Hermes Gateway Watchdog
多角色 Gateway 独立健康监控 + 自动重连 + 飞书告警
零 Token 消耗，纯本地检查 (L1: PID + L2: WebSocket 日志)
"""

import json
import os
import time
import logging
import subprocess
import signal
import sys
from pathlib import Path

import requests

# ---
#  配置加载
# ---

CONFIG_PATH = Path.home() / ".hermes" / "watchdog" / "config.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

config = load_config()

def resolve(p):
    return str(Path(p).expanduser())

GATEWAYS = config["gateways"]
WEBHOOK_URL = config["webhook_url"]
POLL_INTERVAL = config["poll_interval"]
BACKOFF = config["backoff_seconds"]
MAX_RETRIES = config["max_retries"]
ALERT_COOLDOWN = config["alert_cooldown_seconds"]

HEARTBEAT_FILE = resolve(config["heartbeat_file"])
WATCHER_PID_FILE = resolve(config["pid_file"])
STATE_FILE = resolve(config["state_file"])
LOG_FILE = resolve(config["log_file"])

# ---
#  日志
# ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("watchdog")

# ---
#  状态管理
# ---

state: dict = {}  # {name: {status, last_alert, last_recovery, retry_count, detail}}


def load_state():
    global state
    try:
        with open(STATE_FILE) as f:
            stored = json.load(f)
        for name, s in stored.items():
            state[name] = s
        # 确保所有 gateway 都有条目
        for name in GATEWAYS:
            if name not in state:
                state[name] = {"status": "online", "last_alert": 0.0,
                               "last_recovery": 0.0, "retry_count": 0, "detail": ""}
    except (FileNotFoundError, json.JSONDecodeError):
        state = {name: {"status": "online", "last_alert": 0.0,
                        "last_recovery": 0.0, "retry_count": 0, "detail": ""}
                 for name in GATEWAYS}


def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ---
#  L1: PID 存活检查
# ---

def check_pid(pid_file):
    """读 gateway.pid → 确认进程存活 + 非僵尸。返回 (pid, is_alive, detail)"""
    pid_file = resolve(pid_file)
    try:
        with open(pid_file) as f:
            data = json.load(f)
        pid = data.get("pid")
        if not pid:
            return None, False, "no pid in file"
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None, False, str(e)

    # 检查 /proc/<pid> 是否存在
    proc_path = f"/proc/{pid}"
    if not os.path.exists(proc_path):
        return pid, False, "process not found"

    try:
        with open(f"{proc_path}/stat") as f:
            stat_parts = f.read().split()
        stat_code = stat_parts[2] if len(stat_parts) > 2 else "?"
        if stat_code == "Z":
            return pid, False, "zombie"
        return pid, True, f"alive (stat={stat_code})"
    except (FileNotFoundError, IndexError) as e:
        return pid, False, str(e)


# ---
#  L2: WebSocket 连接状态
# ---

def check_websocket(profile):
    """读 agent.log → 最近连接事件。返回 (status, detail)"""
    if profile is None:
        log_dir = Path.home() / ".hermes" / "logs"
    else:
        log_dir = Path.home() / ".hermes" / "profiles" / profile / "logs"

    agent_log = log_dir / "agent.log"
    if not agent_log.exists():
        return "unknown", "no log file"

    try:
        result = subprocess.run(
            ["grep", "-a",
             "Connected in websocket\\|keepalive ping timeout\\|"
             "trying to reconnect\\|Disconnected\\|connect failed\\|"
             "connected to wss",
             str(agent_log)],
            capture_output=True, text=True, timeout=5
        )
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        if not lines:
            return "unknown", "no ws events"

        last = lines[-1]
        if "connected to wss" in last or "Connected in websocket" in last:
            return "connected", last[:150]
        if "trying to reconnect" in last:
            return "reconnecting", last[:150]
        if "Disconnected" in last:
            return "disconnected", last[:150]
        if "keepalive ping timeout" in last:
            return "timeout", last[:150]
        if "connect failed" in last:
            return "failed", last[:150]
        return "unknown", last[:150]
    except subprocess.TimeoutExpired:
        return "error", "grep timeout"
    except Exception as e:
        return "error", str(e)


# ---
#  综合健康检查 (L1 + L2)
# ---

def check_gateway(name, gw_config):
    """返回 (status, detail)。status: healthy/dead/unhealthy/recovering"""
    pid, alive, detail = check_pid(gw_config["pid_file"])
    profile = gw_config["profile"]

    if not alive:
        return "dead", detail

    ws_status, ws_detail = check_websocket(profile)

    if ws_status == "connected":
        return "healthy", f"PID={pid}"
    if ws_status == "reconnecting":
        return "recovering", f"PID={pid}, {ws_detail}"
    if ws_status in ("timeout", "failed", "disconnected"):
        return "unhealthy", f"PID={pid}, {ws_detail}"
    # unknown/error — 进程活着但 WS 状态不明，保守为 healthy
    return "healthy", f"PID={pid} (ws={ws_status})"


def get_hermes_path():
    """查找 hermes 命令的完整路径"""
    for p in ["/home/linchen/.local/bin/hermes",
              "/home/linchen/.hermes/node/bin/hermes",
              "/usr/local/bin/hermes",
              "/usr/bin/hermes"]:
        if os.path.exists(p):
            return p
    # 最后尝试 PATH 查找
    import shutil
    return shutil.which("hermes") or "hermes"


# ---
#  网关重启
# ---

def restart_gateway(name, gw_config):
    """按序: kill → clean → restart。返回 bool"""
    profile = gw_config["profile"]
    pid_file = resolve(gw_config["pid_file"])
    hermes_bin = get_hermes_path()

    # Step 1: kill 旧进程
    try:
        with open(pid_file) as f:
            data = json.load(f)
        old_pid = data.get("pid")
        if old_pid:
            log.info(f"[{name}] 杀掉旧 PID {old_pid}")
            try:
                os.kill(old_pid, signal.SIGKILL)
                time.sleep(1)
            except ProcessLookupError:
                pass
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Step 2: 清理 stale PID 文件
    try:
        os.remove(pid_file)
    except FileNotFoundError:
        pass

    # Step 3: 启动新网关
    if profile is None:
        cmd = [hermes_bin, "gateway", "run", "--replace"]
    else:
        cmd = [hermes_bin, "--profile", profile, "gateway", "run", "--replace"]

    log.info(f"[{name}] 启动: {' '.join(cmd)}")
    try:
        # 使用 Popen 异步启动（gateway 会自动 daemonize）
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        # 等待 PID 文件生成（最长 60s）
        for _ in range(12):
            time.sleep(5)
            if os.path.exists(pid_file):
                try:
                    with open(pid_file) as f:
                        data = json.load(f)
                    if data.get("pid"):
                        log.info(f"[{name}] 启动成功 PID={data['pid']}")
                        return True
                except (json.JSONDecodeError, KeyError):
                    pass
        log.error(f"[{name}] 启动超时 (60s，PID 文件未生成)")
        return False
    except Exception as e:
        log.error(f"[{name}] 启动异常: {e}")
        return False


# ---
#  飞书卡片告警
# ---

def send_feishu_card(title, color, lines):
    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": line}}
        for line in lines
    ]
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color,
            },
            "elements": elements,
        },
    }
    try:
        resp = requests.post(WEBHOOK_URL, json=card, timeout=10)
        if resp.status_code == 200:
            log.info(f"飞书告警已发送: {title[:30]}")
        else:
            log.warning(f"飞书告警返回 {resp.status_code}: {resp.text[:150]}")
    except requests.RequestException as e:
        log.warning(f"飞书告警失败: {e}")


def send_disconnect(name, detail):
    send_feishu_card(
        "🔴 Hermes 告警",
        "red",
        [
            f"角色: **{name}**",
            f"事件: **Gateway 异常**",
            f"详情: {detail}",
            f"时间: {time.strftime('%m-%d %H:%M:%S')}",
            f"动作: 触发自动重连…",
        ],
    )


def send_recovery(name, detail):
    send_feishu_card(
        "✅ Hermes 恢复",
        "green",
        [
            f"角色: **{name}**",
            f"事件: **Gateway 已恢复**",
            f"详情: {detail}",
            f"时间: {time.strftime('%m-%d %H:%M:%S')}",
        ],
    )


def send_critical(name, detail):
    send_feishu_card(
        "🚨 Hermes 需人工介入",
        "purple",
        [
            f"角色: **{name}**",
            f"事件: **自动重连失败**",
            f"详情: {detail}",
            f"时间: {time.strftime('%m-%d %H:%M:%S')}",
            f"建议: 手动检查 Gateway 配置或网络",
        ],
    )


# ---
#  主循环
# ---

def watch_loop():
    log.info("=" * 55)
    log.info(f"Hermes Watchdog 启动 | 监控 {len(GATEWAYS)} 个 Gateway")
    log.info(f"角色: {', '.join(GATEWAYS.keys())}")
    log.info(f"轮询: {POLL_INTERVAL}s | 重试: {MAX_RETRIES} 次")
    log.info("=" * 55)

    load_state()

    # 写入自身 PID
    os.makedirs(os.path.dirname(WATCHER_PID_FILE), exist_ok=True)
    with open(WATCHER_PID_FILE, "w") as f:
        json.dump({"pid": os.getpid(), "start_time": time.time()}, f)

    while True:
        try:
            # 更新心跳
            os.makedirs(os.path.dirname(HEARTBEAT_FILE), exist_ok=True)
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(f"{time.time()}\n")

            now = time.time()

            for name, gw_config in GATEWAYS.items():
                try:
                    status, detail = check_gateway(name, gw_config)
                    gs = state.setdefault(name, {
                        "status": "online", "last_alert": 0.0,
                        "last_recovery": 0.0, "retry_count": 0, "detail": "",
                    })
                    prev = gs["status"]

                    if status == "healthy":
                        if prev in ("offline", "recovering", "critical", "unhealthy"):
                            log.info(f"[{name}] ✅ 恢复: {detail}")
                            gs["status"] = "online"
                            gs["retry_count"] = 0
                            gs["last_recovery"] = now
                            gs["detail"] = detail
                            save_state()
                            send_recovery(name, detail)

                    elif status in ("dead", "unhealthy"):
                        # 冷却期内不告警，但继续检查和修复
                        in_cooldown = (now - gs["last_alert"] < ALERT_COOLDOWN)

                        if not in_cooldown:
                            log.warning(f"[{name}] ❌ 异常: [{status}] {detail}")
                            gs["last_alert"] = now
                            gs["detail"] = detail
                            save_state()
                            send_disconnect(name, detail)

                        gs["status"] = "offline"

                        # 重连尝试
                        recovered = False
                        for attempt in range(MAX_RETRIES):
                            gs["status"] = "recovering"
                            save_state()

                            backoff = BACKOFF[min(attempt, len(BACKOFF) - 1)]
                            log.info(f"[{name}] 重连 {attempt + 1}/{MAX_RETRIES} (等待 {backoff}s)")
                            time.sleep(backoff)

                            ok = restart_gateway(name, gw_config)
                            if ok:
                                # 轮询等待网关就绪：最长 35s，每 5s 检查一次
                                re_status, re_detail = "unknown", "waiting for connect"
                                for _ in range(7):
                                    time.sleep(5)
                                    re_status, re_detail = check_gateway(name, gw_config)
                                    if re_status == "healthy":
                                        break
                                if re_status == "healthy":
                                    log.info(f"[{name}] ✅ 重连成功: {re_detail}")
                                    gs["status"] = "online"
                                    gs["retry_count"] = 0
                                    gs["last_recovery"] = now
                                    gs["detail"] = re_detail
                                    save_state()
                                    send_recovery(name, re_detail)
                                    recovered = True
                                    break
                                log.warning(f"[{name}] 重连后仍异常 ({re_status}): {re_detail}")
                            else:
                                log.warning(f"[{name}] 重启命令失败")

                        if not recovered:
                            log.error(f"[{name}] 🚨 {MAX_RETRIES} 次重连均失败")
                            gs["status"] = "critical"
                            gs["retry_count"] = gs.get("retry_count", 0) + 1
                            save_state()
                            send_critical(name, f"{MAX_RETRIES} 次失败，末次: {detail}")

                    elif status == "recovering":
                        if prev != "recovering":
                            log.info(f"[{name}] ⚠️ 内部重连中: {detail}")

                except Exception as e:
                    log.error(f"[{name}] 检查异常: {e}", exc_info=True)

            # 轮询结束后记录摘要日志
            healthy_count = sum(1 for g in state.values() if g["status"] == "online")
            abnormal = [n for n, g in state.items() if g["status"] != "online"]
            if abnormal:
                log.info(f"📊 摘要: 健康={healthy_count}/{len(GATEWAYS)}, 异常={abnormal}")
            else:
                log.info(f"📊 摘要: 全员健康 ({healthy_count}/{len(GATEWAYS)})")

            # 强制刷日志缓冲区
            for hdlr in logging.root.handlers:
                hdlr.flush()

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log.info("Watchdog 退出 (SIGINT)")
            break
        except Exception as e:
            log.error(f"主循环异常: {e}", exc_info=True)
            for hdlr in logging.root.handlers:
                hdlr.flush()
            time.sleep(POLL_INTERVAL)


# ---
#  信号处理
# ---

def handle_sigterm(sig, frame):
    log.info("Watchdog 退出 (SIGTERM)")
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_sigterm)

if __name__ == "__main__":
    watch_loop()
