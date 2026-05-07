# Sync Hermes Config to GitHub Reference Repo

## 场景
当本地 `~/.hermes/` 配置经过大量迭代后，需要将最新状态同步到 GitHub 参考仓库（如 `chenlin9194/hermes-multi-role-profiles`）时使用。

## 前提
- 本地已克隆 GitHub 仓库：`git clone <repo> /mnt/d/hermes-repo-check`
- GitHub 仓库是**配置模板仓库**（不含 secrets / runtime data），不是 ~/.hermes 的完整备份

## 差异化比对方法论

### 1. 分类需比对的文件（非 Hermes Agent 自带代码）

| 类别 | 路径 | 比对方法 |
|------|------|---------|
| SOUL | `SOUL.md`、`memories/USER.md` | 逐文件 diff |
| Profiles | `profiles/*/SOUL.md` | 按角色 diff |
| Bin | `bin/hermes-profile` | 检查是否损坏 + diff |
| Config | `config.yaml.example` | 检查密钥泄露 + 行数对比 |
| Scripts | `setup.sh`、`.gitignore`、`README.md` | diff |
| Watchdog | `watchdog/*.py`、`config.example.json` | diff |
| Skills | `skills/` 下自定义技能 | 逐技能对比 |

### 2. 检查清单（必须项）

```bash
# 关键检查项
grep -n 'api_key\|api_key\|token\|secret\|password' config.yaml.example
# ↑ 检查是否有真实 API Key 泄露

head -5 bin/hermes-profile
# ↑ 检查文件是否损坏（不应为"File unchanged since last read..."）

wc -l config.yaml.example
# ↑ 检查是否过旧（现代版约 359 行，config_version: 22）
```

### 3. 状态分类

| 标记 | 含义 | 操作 |
|------|------|------|
| [CHANGED] | 内容有变化 | diff 确认后覆盖 |
| [CORRUPTED] | 文件损坏 | 用本地真实版覆盖 |
| [LEAKED] | 含真实密钥 | 替换为 `<YOUR_API_KEY>` 占位符 |
| [NEW] | 仓库缺失 | 添加 |
| [SAME] | 无变化 | 跳过 |
| [REMOVED] | 仓库有但本地不再需要 | 仓库删除 |

## 安全规则

### 不允许入 Git 的文件
```
config.yaml
.env
**/auth.json
**/gateway.pid
**/state.db*
**/gateway_state.json
**/heartbeat
**/feishu_seen_message_ids.json
**/watchdog/config.json    # 含实际 app_id/app_secret
**/watchdog/state.json
**/watchdog/watchdog.log
```

### config.yaml.example 脱敏规则
- 所有 `api_key:` 值 → `<YOUR_API_KEY>`
- 所有 `app_id:` / `app_secret:` → `<YOUR_APP_ID>` / `<YOUR_APP_SECRET>`
- 所有 `webhook_url:` → `<YOUR_WEBHOOK_URL>`
- 所有 `token:` / `secret:` / `password:` → 占位符
- 所有 `open_id:` / `user_id:` → `<YOUR_USER_ID>`

## 同步方向

### 本地 → 仓库（推送本地变更）
```bash
cd /mnt/d/hermes-repo-check
# 1. 替换损坏/过时文件
cp ~/.hermes/bin/hermes-profile bin/hermes-profile
# 2. 生成脱敏 config 模板
cat ~/.hermes/config.yaml | sed 's/api_key: .*/api_key: <YOUR_API_KEY>/g' \
  | sed 's/app_id: .*/app_id: <YOUR_APP_ID>/g' \
  | sed 's/app_secret: .*/app_secret: <YOUR_APP_SECRET>/g' \
  > config.yaml.example
# 3. 同步 watchdog v2
cp ~/.hermes/watchdog/watchdog.py watchdog/
cp ~/.hermes/watchdog/cron_check.py watchdog/
# 4. 添加新内容
cp -r ~/.hermes/scripts/ ./scripts/
cp -r ~/.hermes/skills/deploy-hermes-multi-role/ ./skills/
cp ~/.hermes/部署说明.md ./
```

### 仓库 → 本地（补全缺失）
```bash
# 从仓库同步 reviewr 技能
cp -r /mnt/d/hermes-repo-check/skills/nano-pdf ~/.hermes/profiles/reviewer/skills/productivity/
cp -r /mnt/d/hermes-repo-check/skills/powerpoint ~/.hermes/profiles/reviewer/skills/productivity/
# 从仓库同步脚本
cp /mnt/d/hermes-repo-check/setup.sh ~/.hermes/
cp /mnt/d/hermes-repo-check/.gitignore ~/.hermes/
cp /mnt/d/hermes-repo-check/watchdog/README.md ~/.hermes/watchdog/
```

## Watchdog v2 升级注意事项

本地升级到 v2 时，配置结构发生变化：

| 旧版 (v1) | 新版 (v2) |
|-----------|-----------|
| `webhook_url: <URL>` | `bot: {app_id, app_secret, user_open_id}` |
| Webhook 卡片（POST 每次新发） | Feishu Bot API（卡片原地 PATCH 更新） |
| 仅 L1+L2 检测 | + L3 消息接收检测（假活检测） |
| 无 DNS 预检 | + DNS 预检（重启前检查 feishu.cn 可达性） |

## Git Push 认证

### 典型问题：SSH 连接被重置（`kex_exchange_identification: read: Connection reset by peer`）

常见于中国网络环境。解决方案：

```bash
# 方案 A：HTTPS + Personal Access Token（推荐）
git remote set-url origin https://<用户名>@github.com/<用户名>/<仓库名>.git
# 系统会提示输入密码，输入 PAT（不是 GitHub 密码）
git push origin main
# 推完后恢复
git remote set-url origin git@github.com:<用户名>/<仓库名>.git

# 方案 B：配置 gh CLI
gh auth login
git push origin main

# 方案 C：设置 git credential.helper 缓存 PAT
git config --global credential.helper store
# 首次 push 时输入用户名+PAT，后续自动使用
```

> ⚠️ 不要将 PAT 写入任何脚本、.env 或 .gitconfig 文件。用完后建议清除 credential store。

## 真实案例参考

参见本会话（2026-05-07）：完整执行了 17 文件改动（+2716/-156 行）的差异化同步，包括：
- 修复损坏的 `bin/hermes-profile`
- 发现并清理 `config.yaml.example` 中的 API Key 泄露
- 升级 watchdog v2 到仓库
- 双向同步 skills（nano-pdf, powerpoint, deploy-hermes-multi-role, pm-routing）
- 添加 scripts/ 和 部署说明.md
