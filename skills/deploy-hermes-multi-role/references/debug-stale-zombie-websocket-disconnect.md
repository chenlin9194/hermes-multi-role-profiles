# 排查网关进程残留 + WebSocket 断连 — 真实案例（2026-04-30）

## 场景

多角色 Hermes 系统中，Assistant 网关进程看似存活（`ps aux` 有输出），但在飞书群中 **不回任何消息**。其他 4 个角色（PM/SE/Writer/Reviewer）全部正常。

## 排查步骤

### 步骤 1：确认进程存活

```bash
ps aux | grep 'profile assistant' | grep -v grep
```

**输出（正常）**：
```
linchen    25980  0.0  3.8 630460 264652 ?  Ssl  12:58   0:13 python -m hermes_cli.main --profile assistant gateway run --replace
```

进程在，PID 25980，状态 S（sleeping），0% CPU，RSS 264MB。**看起来正常。** 但这就是陷阱。

### 步骤 2：查看 Gateway 状态文件

```bash
cat ~/.hermes/profiles/assistant/gateway_state.json | python3 -m json.tool
```

**关键字段**：
- `gateway_state`: `"running"` — 仍标为运行
- `platforms.feishu.state`: `"connected"` — 仍标为已连接
- `pid`: `25980` — 与 ps 一致
- `updated_at`: `2026-04-30T05:05:51` — ⚠️ **最后更新时间是 5 小时前！**

> **危险信号**：`updated_at` 远早于当前时间，说明状态文件可能已过时（stale），gateway 实际已无心跳更新。

### 步骤 3：翻阅日志找断连时间点

```bash
tail -50 ~/.hermes/profiles/assistant/logs/agent.log
```

**关键日志**：

```
13:02   INFO gateway.run: Previous gateway exited cleanly — skipping session suspension
13:02   INFO gateway.run: ✓ feishu connected
13:06   INFO gateway.run: inbound message → response ready (正常处理了一条消息)
14:11   INFO gateway.run: Agent cache idle sweep (正常 idle)
17:54   ERROR Lark: receive message loop exit, err: sent 1011 (internal error)
              keepalive ping timeout; no close frame received
17:54   INFO Lark: disconnected to wss://...
17:54   INFO Lark: trying to reconnect for the 1st time
        ← 日志在此处结束 →
```

### 步骤 4：追查 --replace 历史

```bash
grep -i "SIGTERM\|takeover\|replace\|stopping" ~/.hermes/profiles/assistant/logs/gateway.log
```

**发现**：

```
13:02:03  INFO gateway.run: Received SIGTERM as a planned --replace takeover — exiting cleanly
13:02:03  INFO gateway.run: Stopping gateway...
13:02:03  INFO gateway.platforms.feishu: [Feishu] Disconnected
13:02:03  INFO gateway.run: Gateway stopped
13:02:05  INFO gateway.run: Starting Hermes Gateway... (新进程 PID 25733)
```

**结论**：13:02 发生了 `--replace` 信号。旧进程 25980 收到 SIGTERM 后**应该退出**，但实际**没死透**（Ssleep 挂起）。新进程 25733 正常启动并处理了 13:06 的消息。

## 故障链

```
12:58  PID 25980 启动（Assistant 初始进程）
13:02  PID 25980 收到 SIGTERM（--replace 接管信号）
       → PID 25733 启动（替换进程）
       → PID 25980 未能完全退出 → 变成**挂起残留**
13:06  PID 25733 响应了一条 @all test，正常工作
17:54  PID 25733 的飞书 WebSocket ping 超时断开（错误码 1011）
       代码尝试重连（logged "trying to reconnect for the 1st time"）
       重连失败，进程静默退出
       残留进程 25980 仍在 ps 输出中，但已无飞书连接
18:00+  ps 显示有进程 → 误判为正常 → 实际无响应
```

## 关键发现

### 1. `--replace` 旧进程可能不彻底退出

`--replace` 的语义是 "发送 SIGTERM 给旧进程，启动新进程"。**但如果旧进程挂住不退**（SIGTERM 处理异常、I/O 阻塞等），会出现：

- 旧进程（Ssleep/0%CPU/不再处理消息）留在进程表中
- 新进程正常启动并工作
- 如果新进程退出，旧进程的残留会给排查者 "进程还在" 的假象

**验证方法**：对比 `gateway_state.json` 里的 `pid` 与 `ps aux` 中 `gateway run --profile assistant` 的真实进程 PID。如果状态文件中的 PID 在 ps 中但实际不处理请求（最近 1 小时内无日志），就是残留。

### 2. WebSocket 1011 超时后可能无法自动恢复

飞书 WebSocket 的 keepalive ping 超时（`sent 1011 (internal error) keepalive ping timeout`）后的重连机制**不是 100% 可靠**。本案例中：

- 尝试了重连（日志说 "trying to reconnect for the 1st time"）
- 但后续没有 "connected" 日志
- 进程静默退出（可能是重连循环中被异常终止）

**对排查的影响**：如果只看 `ps aux` 误以为进程存活，会浪费大量时间检查飞书 Bot 配置、权限、配对等问题，而实际是网关进程早已失联。

### 3. 核心诊断：追踪日志流

| 诊断维度 | 命令 | 预期结果 |
|---------|------|---------|
| 进程存在性 | `ps aux \| grep 'profile <角色>'` | 应输出至少 1 行 |
| 状态文件 | `cat .../gateway_state.json \| python3 -m json.tool` | `state: "running"`, `feishu.state: "connected"` |
| 最近活动 | `tail -10 .../logs/agent.log` | 最晚日志在 5 分钟内 |
| 最近错误 | `tail -10 .../logs/errors.log` | 无 WebSocket 断开或 ImportError |
| 断链检测 | `grep -E "1011\|timed out\|disconnect\|reconnect" .../logs/agent.log` | 不应有近期的 WebSocket 错误 |

**综合判定**：
- `ps` 有进程 + `gateway_state.json` 正常 + 日志 5 分钟内有消息处理 = 正常
- `ps` 有进程 + 日志停在 30 分钟前 = **残留进程或死锁** → 强杀 + 重启

## 修复步骤

### 1. 强杀残留进程

```bash
# 直接从状态文件拿 PID
kill -9 $(cat ~/.hermes/profiles/<角色>/gateway.pid 2>/dev/null)
# 或：从 ps 输出手动 kill -9 PID
```

### 2. 重启网关

```bash
hermes --profile <角色> gateway run --replace
```

### 3. 验证连接

```bash
sleep 10
tail -5 ~/.hermes/profiles/<角色>/logs/agent.log
# 应看到 "✓ feishu connected"
```

## 预防建议

1. **定期健康检查**：`gateway_state.json` 的 `updated_at` 如果超过 5 分钟未更新，说明可能 stale
2. **监控 WebSocket 丢连**：在 agent.log 中搜索 `1011` / `timed out` / `disconnect`，出现即告警
3. **批量重启脚本**（加入 crontab 每日凌晨执行）：
   ```bash
   for p in se reviewer assistant writer; do
     kill $(cat ~/.hermes/profiles/$p/gateway.pid 2>/dev/null) 2>/dev/null
     hermes --profile $p gateway run --replace
   done
   ```
