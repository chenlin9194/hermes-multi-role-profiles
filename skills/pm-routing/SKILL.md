---
name: pm-routing
description: PM任务路由与分派技能。定义如何拆解用户需求、按角色分派任务、以及对外输出的审稿流水线。
---

# PM 路由技能

## 概述

作为项目经理（PM），你的核心工作是：**接收需求 → 拆解任务 → 按角色路由 → 验收汇总 → 交付用户**。

## 数据共享契约

所有角色的工作数据统一存放于共享数据仓库：
- **路径：** `D:\Work\YYYY-MM-DD\`（WSL: `/mnt/d/Work/YYYY-MM-DD/`）
- **目录结构：** `shared/`（公共）、`assistant/`（助理）、`se/`（技术）、`writer/`（写手）、`reviewer/`（审稿）
- **角色写入规则：** 助理→assistant/，SE→se/，写手→writer/，审稿→reviewer/
- **PM 可读：** 所有目录
- **详见：** `D:\Work\数据共享契约.md`

## 任务路由规则

### 1. 任务拆解

收到用户需求后，按以下维度拆解：

| 任务类型 | 路由目标 | 分派方式 | 示例 |
|---------|---------|---------|------|
| 技术分析/根因定位 | SE | `delegate_task` | Crash分析、Log排查 |
| 信息整理/会议纪要/日常事务 | 助理 | `delegate_task` 或 写入 assistant/ | 会议纪要整理、碎片信息归档 |
| 文档/PPT/Excel生成 | 写手 | `delegate_task` 见【2a. 文档生成前置流程】 | 日报、周报、PPT |
| 审稿/质量检查 | 审稿 | `delegate_task` 或 读writer/后检查 | PPT审稿、文档纠错 |
| 事务性操作（创建文件/目录） | 助理 | `delegate_task` | 目录创建、文件整理 |

### 1a. 跨Profile会话检索（重要）

用户可能在PM之外的其他Profile（如Assistant、SE）中输入过信息。PM应主动检索：

#### 检索 Claude Code 分析结果

当用户提到"让 Claude Code 分析了...", 需要从 Claude Code 的会话日志中提取结论：

```bash
# 1. 找到 Claude Code 的会话元信息（所有会话列表）
ls ~/.claude/sessions/

# 2. 查看具体会话的元数据（PID、sessionId、cwd、时间戳）
cat ~/.claude/sessions/<id>.json

# 3. 读取会话完整对话内容（JSONL格式，每行一个消息事件）
cat ~/.claude/projects/<encoded-path>/<sessionId>.jsonl

# 4. 定位 Claude Code 的分析结论
#    在 JSONL 文件的末尾寻找 assistant 角色的 text 内容
#    关键字: `type: "text"` 或最后的 assistant 消息
#    会话标题在 `"aiTitle"` 字段中
```

**会话文件位置映射**：`~/.claude/projects/` 下按 cwd 路径的编码名组织：
- `/mnt/c/Users/Administrator/Desktop` → `-mnt-c-Users-Administrator-Desktop`
- `/home/linchen/` → `-home-linchen`
- 每个目录下按 <sessionId>.jsonl 存储对话内容

**适用场景**：
- 用户说"我让 Claude Code 分析了性能问题" → 查最近的 Claude Code 会话
- 用户说"Claude Code 之前查过这个问题" → 按关键词搜索 JSONL 内容
- 需要提取 Claude Code 的调试/诊断结论作为参考

详见 `references/claude-code-session-retrieval.md`。

```bash
# 1. 查看目标Profile的会话元信息
cat ~/.hermes/profiles/<profile>/sessions/sessions.json

# 2. 读取会话JSONL文件（包含完整对话内容）
cat ~/.hermes/profiles/<profile>/sessions/<session_id>.jsonl
```

**适用场景：**
- 用户说"我让助理整理过项目信息" -> 去Assistant的sessions查
- 用户说"SE分析过这个Log" -> 去SE的sessions查
- **注意**：注意：Profile之间的open_id不同，需通过会话元信息判断哪个会话属于该用户。更重要的是，**跨Profile角色之间的 open_id 可能完全不匹配** — 用户 @提及角色的显示名如果对应的是另一个Feishu实体的 open_id，该角色 bot 将无法识别自己被 @。详见 `devops/health-check` 的场景5。

### 2a. 文档生成前置流程（Reject Prevention）

**凡是涉及对外交付的文档生成，必须走"先确认 -> 再生成"的流程。**

```
用户需求
    |
    +-- 用户提供了完整内容？ -> 直接进入审稿流水线
    |
    +-- 用户说"自己去查" -> 检索相关Profile的会话 -> 整理成草稿
    |                           |
    |                           v
    |                 【关键步骤】向用户提交内容确认
    |                 "以下是我整理的内容，请确认是否正确？"
    |                           |
    |               +-----------+-----------+
    |               ✅ 正确               ❌ 不正确/要修改
    |               |                       |
    |               v                       v
    |         进入审稿流水线          用户修改后重新确认
    |
    +-- 用户说"用XX文件里的数据" -> 读取共享数据仓库 -> 整理确认
```

### 2b. delegate_task 失败兜底

委托给子Agent的任务可能因以下原因失败：
- max_iterations 限制（最常见）
- API错误（reasoning_content格式、密钥过期等）
- 技能路径不存在

**PM兜底策略：**
1. delegate_task 失败后不要重复尝试（大概率再次失败）
2. 检查子Agent是否已创建了部分文件
3. 直接使用PM可用的技能接手（如 pptx-generator、minimax-docx 等）
4. 完成后仍应走审稿流程

### 2. 分派格式

每次路由使用标准格式：

```
【任务ID】TASK-{日期}-{序号}
【优先级】P0/P1/P2
【目标角色】SE/助理/写手/审稿
【任务描述】...
【上下文】文件路径、背景信息、约束条件
【输出要求】写入哪个目录、输出格式
```

### 3. 对外输出审稿流水线（强制性）

凡是涉及**对外交付**的内容（PPT、日报、周报、汇报材料），必须走以下流水线：

```
用户需求 → PM拆解
    │
    ▼
写手产出 → 写入 writer/目标文件
    │
    ▼
审稿检查 → 写入 reviewer/审稿意见.md
    │
    ├── 通过（状态：review_approved）→ PM验收 → 交付用户
    │
    └── 不通过 → PM退回写手修改 → 再次送审
```

**判断标准：** 只有 `reviewer/` 目录下存在 `.status.review_approved` 标记时，方可交付。

### 4. 错误处理

| 场景 | 处理方式 |
|------|---------|
| `delegate_task` 执行失败 | 重试1次，如仍失败则PM自行处理并备注 |
| 审稿发现问题 | 写手修改后自动重新送审（最多2轮） |
| 数据缺失 | 标记 `#待确认#` 并向用户追问 |
| 系统健康检查（查岗） | 使用 `devops/health-check` 三层验证流程，禁止仅用 `ps` 或 `grep` 做单层判定。注意：角色在公共群组中操作而非 PM 的私有群，查岗日志需在公共群组 ID 下验证 |
| 角色不响应 @mention（L1/L2/L3 正常） | 诊断流程：① 检查角色 gateway.log 是否收到该消息 ② 提取消息中 @mention 列表的 open_id ③ 对比角色自身 open_id。根因通常是飞书群内显示名 ≠ bot 实际 open_id。修复：统一群内显示名与 bot 身份，见 `devops/health-check` 的 场景5 |
| 角色不可用/进程残留 | 强杀残留PID → `hermes --profile <role> gateway run --replace` → 三层验证确认 |
| 模型 API 异常 | 检查角色 `.env` 中的 API key 和 base_url |
| 角色故障恢复 | PM → 助理 | delegate_task 重启网关 + 验证 | PA/SE/Writer/Reviewer 掉线后重启 |

## 6. 技能生命周期管理（Skill-to-Role Mapping）

作为 PM，你需要管理各角色拥有的技能清单。以下是从本次对话中总结的关键教训：

### 6a. 技能的"双重属性"

一个技能可能由 **两层** 组成：

| 层级 | 内容 | 位置 | 大小 |
|------|------|------|------|
| 指令层 | SKILL.md（操作说明书） | `~/.hermes/skills/<category>/<skill>/` | ~4KB |
| 工具箱层 | references/ scripts/ templates/ assets/ workflows/ | 同上目录（或外部项目仓库） | 可达 25MB+ |

**做技能迁移时的检查清单：**
1. ✅ 检查 SKILL.md 是否存在
2. ✅ 检查 references/ scripts/ templates/ 等依赖目录是否存在
3. ✅ 对比项目仓库内 `skills/<skill>/` 下的完整版本（可能比 Hermes 目录下的更完整）
4. ✅ 完整 `cp -r` 而非只复制单个 SKILL.md

### 6b. 从项目仓库提取完整技能

当项目仓库（如 ppt-master GitHub repo）在自身 `skills/` 目录下存有完整 skill 定义时：

```bash
# 源路径：项目仓库内
/mnt/d/Users/.../ppt-master/skills/ppt-master/
    ├── SKILL.md
    ├── references/    # 12+ 角色/标准文档
    ├── scripts/       # 生成/后处理脚本
    ├── templates/     # 布局模板 + 图标库
    └── workflows/     # 工作流定义

# 目标路径：角色技能目录
~/.hermes/profiles/<role>/skills/ppt-master/
```

**注意：** 这种仓库内的技能副本通常比人工在 Hermes 下创建的单文件 SKILL.md **更完整、更权威**。优先使用项目仓库版本。

### 6c. 迁移技能到其他角色

```bash
# 1. 删除目标角色的旧版本（如果存在）
rm -rf ~/.hermes/profiles/<role>/skills/<category>/<skill>/

# 2. 从源复制完整技能目录
cp -r /path/to/source/skill ~/.hermes/profiles/<role>/skills/<skill>

# ⚠️ 重要：25MB+/11953文件的 cp -r 需要 180s+ 的 timeout
#    默认 60s 会超时导致部分复制

# 3. 验证
ls ~/.hermes/profiles/<role>/skills/<skill>/
find ~/.hermes/profiles/<role>/skills/<skill>/ -type f | wc -l

# 4. 清理原路径中空置的父分类目录
#    先检查分类下是否还有其他技能
ls ~/.hermes/skills/<category>/   # 如果只剩 DESCRIPTION.md 可删除
```

### 6d. 技能迁移的场景

| 场景 | 操作 | 示例 |
|------|------|------|
| 技能专属于某个角色 | 从主角色彩迁到角色 profile | minimax-* → Writer |
| 技能位置不对（分类目录 vs 根层） | mv 到正确层级 | productivity/ppt-master → ppt-master |
| 技能内容不全 | 从项目仓库提取完整版替换 | SKILL.md → SKILL.md + refs + scripts |
| 项目仓库的 skills/ 有更完整版本 | 用项目版本覆盖 Hermes 版本 | ppt-master GitHub repo 内部版本 |

### 6e. 路径假设的陷阱（重要）

**永远不要假设一个路径就是用户的工作目录，只因为它包含了某个项目文件。**

错误示例：`D:\Users\80318604\` 下有 ppt-master → 就认为这是用户的工作目录。
正确做法：先确认用户的实际工作数据存放位置（如 `D:\Work\`），再确认项目文件是否为迁移/克隆产生的遗留结构。

当不确定时：直接问用户。

## 每日启动检查

每次对话开始后，PM 应自动检查：
1. `D:\Work\` 下今天的数据目录是否存在 → 如不存在则创建
2. `shared/tasks.md` 中是否有待办事项需要提醒用户
3. 是否有审稿意见待处理（`reviewer/` 是否有未处理的返修）
4. **健康检查**：查看近期是否有角色掉线记录（`shared/tasks.md` 或日志中是否有异常标记）
   - 响应 "查岗" 请求时，必须使用 `devops/health-check` 技能的三层验证流程
   - 禁止仅用 `ps aux | grep` 或 `grep "Connected"` 做单层判定
   - **⚠️ 群体陷阱**：PM 有私有 Home Channel，下属角色工作在公共群组中。查角色日志时要在公共群组（如 `oc_d17d5b4da3a43c070662b7a499590f92`）下验证，而非 PM 自己的群组
