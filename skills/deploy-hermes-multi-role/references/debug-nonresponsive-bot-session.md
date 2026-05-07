# 排查 Bot 不响应 — 真实案例（2026-04-30）

## 场景

多角色 Hermes 系统中（5 个独立 Feishu Bot：PM/助理/SE/写手/审稿），其中 Writer Bot 在群里被 @all 后始终不回应，其他 4 个 Bot 正常。

## 排查步骤（按顺序执行）

### 步骤 1：确认进程

```bash
ps aux | grep 'profile writer' | grep -v grep
```

### 步骤 2：查看 Gateway 状态

```bash
cat ~/.hermes/profiles/writer/gateway_state.json | python3 -m json.tool
```

### 步骤 3：分析 Gateway 日志

```bash
tail -100 ~/.hermes/profiles/writer/logs/gateway.log
```

## 日志流分析

### 阶段 1：ImportError 崩溃

```
2026-04-30 12:32:36,979 ERROR gateway.run: Agent error in session ...
Traceback (most recent call last):
    from tools.terminal_tool import cleanup_vm, get_active_env, is_persistent_env
    from tools.approval import (
    from hermes_cli.config import cfg_get
ImportError: cannot import name 'cfg_get' from 'hermes_cli.config' (/home/linchen/.hermes/hermes-agent/hermes_cli/config.py)
```

**agent.log 同样显示多个模块导入失败：**
```
WARNING tools.registry: Could not import tool module tools.browser_tool: cannot import name 'cfg_get' from 'hermes_cli.config'
WARNING tools.registry: Could not import tool module tools.memory_tool: cannot import name 'atomic_replace' from 'utils'
```

**根因：** `config.py` 修改时间 12:15，但 `__pycache__/config.cpython-311.pyc` 编译时间 12:33（崩溃时生成）。字节码缓存与源码不一致。

### 阶段 2：修复缓存后 → Unauthorized user

清 pycache + 重启后，日志变为：

```
2026-04-30 12:37:15,498 WARNING gateway.run: Unauthorized user: ou_f8c6407751e804379c95a25b8bda784b (None) on feishu
```

所有消息都被 Gateway 层的用户授权检查拒绝。

### 阶段 3：分析配对存储

对比各角色配对文件：

```bash
# 查看配对存储
ls -la ~/.hermes/profiles/<角色>/platforms/pairing/

# 正常角色（助理）有 approved 文件
cat ~/.hermes/profiles/assistant/platforms/pairing/feishu-approved.json
# → {"ou_7f2628d10c645ad3f993ba64bcec1328": {"user_name": "", "approved_at": 1777270241}}

# Writer 没有 approved 文件，只有 pending
cat ~/.hermes/profiles/writer/platforms/pairing/feishu-pending.json
# → {"VDC48MCR": {"user_id": "ou_f8c6407751e804379c95a25b8bda784b", ...}}
```

**根因：** 部署时只完成了 4 个角色的配对，Writer 被遗漏。每个 Feishu Bot 的 open_id 不同。

### 阶段 4：修复配对

创建 `~/.hermes/profiles/writer/platforms/pairing/feishu-approved.json`：

```json
{
  "ou_f8c6407751e804379c95a25b8bda784b": {
    "user_name": "",
    "approved_at": 1777270241.9251142
  }
}
```

文件创建后立刻生效（无需重启，PairingStore 实时读取磁盘）。

## 验证

确认响应链路完整：

```
12:59:51 - Received raw message (DM "hi")
12:59:52 - Flushing text batch
12:59:54 - inbound message (Auth pass! 无 "Unauthorized user")
13:00:15 - response ready (21.1s, 2 API calls, 239 chars)
13:00:15 - Sending response
```

## 关键发现

1. **`__pycache__` 是稳定复现的陷阱**：代码修改后首次启动若崩溃，生成的缓存可能损坏。清所有 pycache 后再重启。
2. **Feishu open_id 跨 Bot 隔离**：同一个人在不同 Bot 中 open_id 不同，不能用 PM 的配对记录推断 Writer。
3. **配对方式**：`feishu-approved.json` 文件写入后即时生效，比修改 `.env` 再重启更优雅。
4. **日志诊断捷径**：看 `Flushing` 后的下一行——"Unauthorized user" 还是 "inbound message" 还是 traceback，直接定位问题类别。
