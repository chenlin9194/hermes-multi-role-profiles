# Hermes Gateway Watchdog

多角色 Hermes Gateway 独立健康监控 + 自动重连 + 飞书告警。零 Token 消耗。

## 架构

```
watchdog.py (守护进程) ──每30s─→ L1: PID存活 + L2: WebSocket状态 → 5 Gateway
       │
       ├─ 检测异常 → 自动重启 (kill僵尸→clean→hermes --replace)
       ├─ 状态变化 → 飞书 Webhook 卡片告警
       └─ 心跳文件 ← cron_check.py (每分钟) ← cron 兜底
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `watchdog.py` | 主守护进程。每 30s 轮询 5 个 Gateway 的 L1（PID 存活）+ L2（WebSocket 连接） |
| `cron_check.py` | Cron 兜底检查。每分钟验证 watchdog 心跳，2 分钟无更新则自动重启 |
| `config.example.json` | 配置模板。复制为 `config.json` 并填入飞书 Webhook URL |

## 部署

```bash
# 1. 复制配置模板
cp config.example.json config.json
# 编辑 config.json 填入飞书 Webhook URL

# 2. 启动守护进程
cd ~/.hermes/watchdog/
python3 watchdog.py &

# 3. 设置 cron 兜底
crontab -e
# 添加: * * * * * python3 /home/linchen/.hermes/watchdog/cron_check.py
```

## 配置说明 (`config.json`)

```json
{
  "webhook_url": "YOUR_FEISHU_WEBHOOK_URL",
  "poll_interval": 30,           // 轮询间隔（秒）
  "gateways": {                  // 被监控的 Gateway 列表
    "PM":       {"profile": null,            "pid_file": "~/.hermes/gateway.pid"},
    "Assistant":{"profile": "assistant",     "pid_file": "~/.hermes/profiles/assistant/gateway.pid"},
    "SE":       {"profile": "se",            "pid_file": "~/.hermes/profiles/se/gateway.pid"},
    "Writer":   {"profile": "writer",        "pid_file": "~/.hermes/profiles/writer/gateway.pid"},
    "Reviewer": {"profile": "reviewer",      "pid_file": "~/.hermes/profiles/reviewer/gateway.pid"}
  },
  "max_retries": 3,              // 每轮最大重试次数
  "backoff_seconds": [1, 5, 30], // 重试等待间隔
  "alert_cooldown_seconds": 300  // 同角色告警冷却（秒）
}
```

## 验证

手动杀掉一个 Gateway 进程，观察：

1. Watchdog 日志: `tail -f ~/.hermes/watchdog/watchdog.log`
2. 飞书告警群: 应收到 🔴 红色卡片
3. 自动恢复后: 应收到 ✅ 绿色卡片
