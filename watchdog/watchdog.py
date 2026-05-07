#!/usr/bin/env python3
"""
Hermes Gateway Watchdog v2
多角色 Gateway 独立健康监控 + 自动重连 + 飞书 Bot 私聊卡片（原地更新）
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

# --- 配置加载 ---

CONFIG_PATH = Path.home() / ".hermes" / "watchdog" / "config.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

config = load_config()

def resolve(p):
    return str(Path(p).expanduser())

BOT = config["bot"]
GATEWAYS = config["gateways"]
POLL_INTERVAL = config["poll_interval"]
BACKOFF = config["backoff_seconds"]
MAX_RETRIES = config["max_retries"]
ALERT_COOLDOWN = config["alert_cooldown_seconds"]

HEARTBEAT_FILE = resolve(config["heartbeat_file"])
WATCHER_PID_FILE = resolve(config["pid_file"])
STATE_FILE = resolve(config["state_file"])
LOG_FILE = resolve(config["log_file"])

# --- 日志 ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("watchdog")

# ============================================================
#  Feishu Bot API 客户端（支持卡片原地更新）
# ============================================================

FEISHU_BASE = "https://open.feishu.cn/open-apis"

class FeishuBot:
    def __init__(self, bot_cfg):
        self.app_id = bot_cfg["app_id"]
        self.app_secret = bot_cfg["app_secret"]
        self.user_open_id = bot_cfg["user_open_id"]
        self._token = None
        self._token_expire = 0

    def _ensure_token(self):
        if self._token and time.time() < self._token_expire - 60:
            return
        resp = requests.post(
            f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取 token 失败: {data}")
        self._token = data["tenant_access_token"]
        self._token_expire = time.time() + data["expire"]
        log.info("Feishu token 已刷新")

    def _headers(self):
        self._ensure_token()
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def _build_card(self, header_title, header_color, elements_md_lines):
        """构建飞书卡片 JSON"""
        elements = []
        for line in elements_md_lines:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": line},
            })
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": header_title},
                "template": header_color,
            },
            "elements": elements,
        }

    def send_card(self, title, color, lines):
        """发送新卡片，返回 message_id"""
        card = self._build_card(title, color, lines)
        payload = {
            "receive_id": self.user_open_id,
            "msg_type": "interactive",
            "receive_id_type": "open_id",
            "content": json.dumps(card, ensure_ascii=False),
        }
        resp = requests.post(
            f"{FEISHU_BASE}/im/v1/messages?receive_id_type=open_id",
            headers=self._headers(),
            json=payload,
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            log.warning(f"发卡片失败: {data}")
            return None
        mid = data.get("data", {}).get("message_id")
        if mid:
            log.info(f"新卡片已发送 message_id={mid}")
        return mid

    def update_card(self, message_id, title, color, lines):
        """更新已有卡片，返回 True/False"""
        card = self._build_card(title, color, lines)
        payload = {
            "content": json.dumps(card, ensure_ascii=False),
        }
        resp = requests.patch(
            f"{FEISHU_BASE}/im/v1/messages/{message_id}",
            headers=self._headers(),
            json=payload,
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            log.warning(f"更新卡片失败 ({data.get('code')}): {data.get('msg','')}")
            return False
        return True

# ============================================================
#  状态管理
# ============================================================

state: dict = {}
_cached_message_id = None  # 当前活跃的卡片 message_id

def load_state():
    global state, _cached_message_id
    try:
        with open(STATE_FILE) as f:
            stored = json.load(f)
        for name, s in stored.items():
            if name == "_meta":
                _cached_message_id = s.get("message_id")
                continue
            state[name] = s
        for name in GATEWAYS:
            if name not in state:
                state[name] = {"status": "online", "last_alert": 0.0,
                               "last_recovery": 0.0, "retry_count": 0, "detail": ""}
    except (FileNotFoundError, json.JSONDecodeError):
        state = {name: {"status": "online", "last_alert": 0.0,
                        "last_recovery": 0.0, "retry_count": 0, "detail": ""}
                 for name in GATEWAYS}
        _cached_message_id = None

def save_state():
    payload = dict(state)
    payload["_meta"] = {"message_id": _cached_message_id}
    with open(STATE_FILE, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

# ============================================================
#  L1: PID 存活检查
# ============================================================

def check_pid(pid_file):
    pid_file = resolve(pid_file)
    try:
        with open(pid_file) as f:
            data = json.load(f)
        pid = data.get("pid")
        if not pid:
            return None, False, "no pid in file"
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None, False, str(e)

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

# ============================================================
#  L2: WebSocket 连接状态
# ============================================================

MESSAGE_STALE_THRESHOLD = config.get("message_stale_threshold", 3600)  # 默认 1 小时
L3_COOLDOWN = MESSAGE_STALE_THRESHOLD * 2  # L3 重启后至少等待 N 秒才再次触发（原 *4 太保守）

def check_message_delivery(log_dir_input) -> tuple:
    """L3: 检查是否有最近成功接收的消息。

    读取 gateway.log 中最后一条 "Received raw message" 的时间戳，
    如果超过 MESSAGE_STALE_THRESHOLD 未收到新消息，判定为消息通道失效。
    返回 (ok: bool, detail: str)
    """
    if isinstance(log_dir_input, str):
        log_dir = Path(log_dir_input).expanduser()
    else:
        log_dir = log_dir_input
    gateway_log = log_dir / "gateway.log"
    if not gateway_log.exists():
        return True, "no gateway.log yet"

    try:
        result = subprocess.run(
            ["grep", "-a", "Received raw message", str(gateway_log)],
            capture_output=True, text=True, timeout=5
        )
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        if not lines:
            return True, "no received messages yet"

        last_line = lines[-1]
        # 格式: 2026-05-04 17:07:34,380 INFO ... [Feishu] Received raw message ...
        ts_str = last_line[:19]  # "2026-05-04 17:07:34"
        try:
            last_ts = time.mktime(time.strptime(ts_str, "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            return True, f"cannot parse timestamp: {ts_str}"

        elapsed = time.time() - last_ts
        if elapsed > MESSAGE_STALE_THRESHOLD:
            return False, f"no msg received for {elapsed:.0f}s (> {MESSAGE_STALE_THRESHOLD}s)"
        return True, f"last msg {elapsed:.0f}s ago"
    except subprocess.TimeoutExpired:
        return True, "grep timeout"
    except Exception as e:
        return True, f"check error: {e}"


def check_gateway_state_json(profile):
    """读取 gateway_state.json 中的 feishu 连接状态和连接时间"""
    if profile is None:
        state_path = Path.home() / ".hermes" / "gateway_state.json"
    else:
        state_path = Path.home() / ".hermes" / "profiles" / profile / "gateway_state.json"

    if not state_path.exists():
        return None, None

    try:
        with open(state_path) as f:
            data = json.load(f)
        feishu = data.get("platforms", {}).get("feishu", {})
        state = feishu.get("state", "unknown")
        updated_at_str = feishu.get("updated_at", "")
        return state, updated_at_str
    except (json.JSONDecodeError, OSError):
        return None, None


def check_websocket(profile):
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

# ============================================================
#  综合健康检查 (L1 + L2)
# ============================================================

def check_gateway(name, gw_config, last_recovery=0.0):
    pid, alive, detail = check_pid(gw_config["pid_file"])
    profile = gw_config["profile"]

    if not alive:
        return "dead", detail

    ws_status, ws_detail = check_websocket(profile)

    if ws_status != "connected":
        if ws_status == "reconnecting":
            return "recovering", f"PID={pid}, {ws_detail}"
        if ws_status in ("timeout", "failed", "disconnected"):
            return "unhealthy", f"PID={pid}, {ws_detail}"
        return "healthy", f"PID={pid} (ws={ws_status})"

    # WS 已连接 — 对 PM Gateway 额外做 L3 消息接收检测 + 假活检测
    log_dir = gw_config.get("log_dir")
    if log_dir:
        # 刚恢复不久时不触发 L3（避免无消息时段反复重启）
        if last_recovery and (time.time() - last_recovery < L3_COOLDOWN):
            return "healthy", f"PID={pid} (L3 skipped, recovery cooldown)"

        # 假活检测：连接已建立超过阈值但无消息
        feishu_state, feishu_updated = check_gateway_state_json(profile)
        if feishu_state == "connected" and feishu_updated:
            try:
                # ISO 格式: "2026-05-06T10:06:20.123105+00:00"
                conn_ts_str = feishu_updated.split(".")[0]
                conn_time = time.mktime(time.strptime(conn_ts_str, "%Y-%m-%dT%H:%M:%S"))
                conn_elapsed = time.time() - conn_time
                # 连接时长超过 30 分钟才开始做假活判断
                if conn_elapsed > 1800:
                    msg_ok, msg_detail = check_message_delivery(log_dir)
                    if not msg_ok:
                        return "unhealthy", f"PID={pid}, {msg_detail}"
                    # 再次检查连接是否仍显示 "connected"（可能检查期间已断开）
                    feishu_state2, _ = check_gateway_state_json(profile)
                    if feishu_state2 != "connected":
                        return "unhealthy", f"PID={pid}, feishu disconnected during check"
            except (ValueError, OSError) as e:
                # timestamp parse error，降级到普通 L3 检查
                msg_ok, msg_detail = check_message_delivery(log_dir)
                if not msg_ok:
                    return "unhealthy", f"PID={pid}, {msg_detail}"

    return "healthy", f"PID={pid}"

# ============================================================
#  Gateway 重启
# ============================================================

def get_hermes_path():
    for p in ["/home/linchen/.local/bin/hermes",
              "/home/linchen/.hermes/node/bin/hermes",
              "/usr/local/bin/hermes",
              "/usr/bin/hermes"]:
        if os.path.exists(p):
            return p
    import shutil
    return shutil.which("hermes") or "hermes"

def resolve_dns(hostname="open.feishu.cn", timeout=5):
    """快速检测 DNS 是否可用，避免在 DNS 故障时盲目重启"""
    try:
        import socket
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(hostname)
        return True
    except (OSError, socket.gaierror):
        return False


def restart_gateway(name, gw_config):
    profile = gw_config["profile"]
    pid_file = resolve(gw_config["pid_file"])
    hermes_bin = get_hermes_path()

    # DNS 预检 — 针对飞书 Gateway 确保 DNS 可达
    if profile is None or profile in ("assistant", "se", "writer", "reviewer"):
        if not resolve_dns():
            log.warning(f"[{name}] DNS 解析失败 (open.feishu.cn)，等待重试...")
            for _ in range(6):  # 最多等 30s
                time.sleep(5)
                if resolve_dns():
                    log.info(f"[{name}] DNS 已恢复")
                    break
            else:
                log.error(f"[{name}] DNS 持续不可达，推迟重启")
                return False

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

    try:
        os.remove(pid_file)
    except FileNotFoundError:
        pass

    if profile is None:
        cmd = [hermes_bin, "gateway", "run", "--replace"]
    else:
        cmd = [hermes_bin, "--profile", profile, "gateway", "run", "--replace"]

    log.info(f"[{name}] 启动: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
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
        log.error(f"[{name}] 启动超时 (60s)")
        return False
    except Exception as e:
        log.error(f"[{name}] 启动异常: {e}")
        return False

# ============================================================
#  构建状态看板卡片
# ============================================================

STATUS_ICON = {
    "online": "🟢",
    "offline": "🔴",
    "recovering": "🟡",
    "critical": "🚨",
    "unhealthy": "🔴",
    "healthy": "🟢",
    "dead": "🔴",
}

def build_dashboard_lines(gw_states):
    """生成 5 个 Gateway 的状态行 + 摘要"""
    lines = []
    for name in GATEWAYS:
        gs = gw_states.get(name, {})
        s = gs.get("status", "online")
        detail = gs.get("detail", "")
        icon = STATUS_ICON.get(s, "⚪")
        status_label = {"online": "运行中", "offline": "离线",
                        "recovering": "恢复中", "critical": "需介入",
                        "unhealthy": "异常"}.get(s, s)
        if detail:
            lines.append(f"{icon} **{name:12s}**　{status_label}　`{detail[:60]}`")
        else:
            lines.append(f"{icon} **{name:12s}**　{status_label}")
    return lines

def get_overall_status(gw_states):
    """根据所有 Gateway 状态决定卡片颜色和标题"""
    critical = any(gs.get("status") == "critical" for gs in gw_states.values())
    offline = any(gs.get("status") in ("offline", "unhealthy", "dead") for gs in gw_states.values())
    recovering = any(gs.get("status") == "recovering" for gs in gw_states.values())

    healthy_count = sum(1 for gs in gw_states.values() if gs.get("status") == "online")
    total = len(GATEWAYS)

    if critical:
        return "🚨 Hermes 需人工介入", "purple"
    if offline:
        return "🔴 Hermes Gateway 异常", "red"
    if recovering:
        return "🟡 Hermes 恢复中", "yellow"
    return "🟢 Hermes 一切正常", "green"

DATETIME_FORMAT = "%m-%d %H:%M:%S"

def build_card_payload(gw_states):
    """组装卡片标题、颜色、行内容"""
    title, color = get_overall_status(gw_states)
    lines = build_dashboard_lines(gw_states)

    healthy_count = sum(1 for gs in gw_states.values() if gs.get("status") == "online")
    total = len(GATEWAYS)
    now_str = time.strftime(DATETIME_FORMAT)

    lines.append("")
    lines.append(f"📊 健康: **{healthy_count}/{total}**　🕐 最后更新: {now_str}")

    # 如果有异常，追加告警摘要
    abnormal = [n for n, g in gw_states.items() if g.get("status") not in ("online", "healthy")]
    if abnormal:
        lines.append(f"⚠️ 异常角色: {', '.join(abnormal)}")
    else:
        lines.append("✅ 全部正常")

    return title, color, lines

# ============================================================
#  飞书推送（发送或更新卡片）
# ============================================================

bot = FeishuBot(BOT)

def push_to_feishu():
    """发送或更新状态看板卡片"""
    global _cached_message_id

    title, color, lines = build_card_payload(state)
    mid = _cached_message_id

    if mid:
        # 尝试更新已有卡片
        ok = bot.update_card(mid, title, color, lines)
        if ok:
            log.debug("卡片已更新")
            return
        # 更新失败（可能消息被删/过期），降级为发新卡片
        log.warning("卡片更新失败，将发送新卡片")
        mid = None

    # 发新卡片
    mid = bot.send_card(title, color, lines)
    if mid:
        _cached_message_id = mid
        save_state()

# ============================================================
#  主循环
# ============================================================

def watch_loop():
    global _cached_message_id

    log.info("=" * 55)
    log.info(f"Hermes Watchdog v2 启动 | 监控 {len(GATEWAYS)} 个 Gateway")
    log.info(f"角色: {', '.join(GATEWAYS.keys())}")
    log.info(f"轮询: {POLL_INTERVAL}s | 重试: {MAX_RETRIES} 次")
    log.info("=" * 55)

    load_state()
    log.info(f"恢复卡片 message_id: {_cached_message_id}")

    # 写入自身 PID
    os.makedirs(os.path.dirname(WATCHER_PID_FILE), exist_ok=True)
    with open(WATCHER_PID_FILE, "w") as f:
        json.dump({"pid": os.getpid(), "start_time": time.time()}, f)

    # 启动时立即推一次状态看板
    push_to_feishu()

    while True:
        try:
            # 更新心跳
            os.makedirs(os.path.dirname(HEARTBEAT_FILE), exist_ok=True)
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(f"{time.time()}\n")

            now = time.time()
            status_changed = False

            for name, gw_config in GATEWAYS.items():
                try:
                    gs = state.setdefault(name, {
                        "status": "online", "last_alert": 0.0,
                        "last_recovery": 0.0, "retry_count": 0, "detail": "",
                    })
                    status, detail = check_gateway(name, gw_config, gs.get("last_recovery", 0.0))
                    prev = gs["status"]

                    if status == "healthy":
                        if prev in ("offline", "recovering", "critical", "unhealthy"):
                            log.info(f"[{name}] ✅ 恢复: {detail}")
                            gs["status"] = "online"
                            gs["retry_count"] = 0
                            gs["last_recovery"] = now
                            gs["detail"] = detail
                            status_changed = True

                    elif status in ("dead", "unhealthy"):
                        in_cooldown = (now - gs["last_alert"] < ALERT_COOLDOWN)

                        if not in_cooldown:
                            log.warning(f"[{name}] ❌ 异常: [{status}] {detail}")
                            gs["last_alert"] = now
                            gs["detail"] = detail
                            status_changed = True

                        gs["status"] = "offline"

                        # 重连尝试
                        recovered = False
                        for attempt in range(MAX_RETRIES):
                            gs["status"] = "recovering"
                            status_changed = True

                            backoff = BACKOFF[min(attempt, len(BACKOFF) - 1)]
                            log.info(f"[{name}] 重连 {attempt+1}/{MAX_RETRIES} (等待 {backoff}s)")
                            time.sleep(backoff)

                            ok = restart_gateway(name, gw_config)
                            if ok:
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
                                    recovered = True
                                    break
                                log.warning(f"[{name}] 重连后仍异常: {re_detail}")
                            else:
                                log.warning(f"[{name}] 重启命令失败")

                        if not recovered:
                            log.error(f"[{name}] 🚨 {MAX_RETRIES} 次重连均失败")
                            gs["status"] = "critical"
                            gs["retry_count"] = gs.get("retry_count", 0) + 1
                            status_changed = True

                    elif status == "recovering":
                        if prev != "recovering":
                            log.info(f"[{name}] ⚠️ 内部重连中: {detail}")

                except Exception as e:
                    log.error(f"[{name}] 检查异常: {e}", exc_info=True)

            # 状态有变化 → 更新飞书卡片
            if status_changed:
                push_to_feishu()

            # 摘要日志
            healthy_count = sum(1 for g in state.values() if g["status"] == "online")
            abnormal = [n for n, g in state.items() if g["status"] != "online"]
            if abnormal:
                log.info(f"📊 健康={healthy_count}/{len(GATEWAYS)}, 异常={abnormal}")
            else:
                log.info(f"📊 全员健康 ({healthy_count}/{len(GATEWAYS)})")

            save_state()

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

def handle_sigterm(sig, frame):
    log.info("Watchdog 退出 (SIGTERM)")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

if __name__ == "__main__":
    watch_loop()
