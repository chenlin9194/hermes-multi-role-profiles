---
name: deploy-hermes-multi-role
category: software-development
description: 部署 Hermes Agent 多角色协作系统，包含 PM/SE/Assistant/Writer/Reviewer 五个专业角色
tags: [hermes, multi-role, ai, deployment, configuration]
---

# Hermes 多角色协作系统部署技能

## 概述
这个技能用于部署基于 Hermes Agent 的多角色协作系统，支持四个专业角色的切换和协作。
包含两个方向：**准备迁移**（源机器→GitHub）和**部署安装**（GitHub→新机器）。

## 适用场景
- 需要多个专业化 AI 助手协作的工作流程
- 项目管理、技术分析、文档编写等多角色任务
- 提高工作效率的专业化分工
- **将本地 Hermes 配置迁移到新机器**

---

## 方向A：准备迁移（源机器 → GitHub）

当本地 Hermes 已配置好 SOUL.md、skills、profiles 后，需要迁移到另一台机器时执行。

### 1. 清理——移除平台默认技能

Hermes 初始化时会为每个 profile 铺一套默认技能（apple/creative/github/research 等约 45+ 个）。**这些技能在新机器上运行 Hermes 就有，不需要入 Git。**

```bash
# 在源机器上，只看自定义/修改过的技能
# 不同角色维护在不同路径下：
#   PM → ~/.hermes/skills/
#   writer/reviewer/se/assistant → ~/.hermes/profiles/<角色>/skills/
```

使用 `hermes-skills-audit-and-dedup` 技能系统梳理一遍，按职责归并后，只把自定义技能入 Git。

### 2. 剥离 secrets

```bash
# config.yaml 含有 API Key，绝不能提交
# 创建脱敏模板：
cp ~/.hermes/config.yaml ./config.yaml.example
# 然后手动编辑替换 api_key 为 YOUR_API_KEY_HERE
```

写入 `.gitignore`：
```
config.yaml
.env
**/auth.json
**/gateway.pid
**/state.db*
```

### 3. 精简 skills/ 目录

**入 Git 的**（体积小，自定义配置）：minimax-docx / minimax-xlsx / minimax-pdf / pptx-generator / ppt-review-workflow / powerpoint / nano-pdf

**不入 Git 的**（体积超大或平台默认）：
- `ppt-master`（~515MB，含大量 SVG 模板/图标库）→ 通过 setup.sh 脚本从 GitHub 仓库 clone
- 所有 `apple/` `creative/` `github/` `research/` 等 → 新机器自动有

```bash
# .gitignore 追加大文件排除规则
cat >> .gitignore << 'EOF'
skills/ppt-master/
skills/apple/
skills/creative/
skills/github/
EOF
```

### 4. 创建/更新部署脚本（setup.sh）

setup.sh 负责在新机器上自动完成：
- 复制 profiles/ 到 ~/.hermes/profiles/
- 复制 SOUL.md、memories/USER.md
- 复制自定义 skills 到对应角色的 skills 目录
- 安装 ppt-master（git clone + .venv + pip install）
- 从 config.yaml.example 创建 config.yaml

```bash
# 核心框架（伪代码）：
for role in writer reviewer se assistant; do
    mkdir -p ~/.hermes/profiles/$role
    cp -r repo_dir/profiles/$role/* ~/.hermes/profiles/$role/
done
# PM 技能放根 skills/
cp -r repo_dir/skills/pptx-generator ~/.hermes/skills/
# Writer 技能放 writer/skills/
cp -r repo_dir/skills/minimax-docx ~/.hermes/profiles/writer/skills/
# Reviewr 技能放 reviewer/skills/productivity/
cp -r repo_dir/skills/powerpoint ~/.hermes/profiles/reviewer/skills/productivity/
```

### 5. 提交到 GitHub

```bash
git add -A
git commit -m "清理仓库：精简skills、更新setup.sh、添加config模板"
git push origin main
```

### 6. 🔑 GitHub Token（一次性）

首次从本机推送到远程仓库需要 Personal Access Token：
```bash
# 配置 remote 使用 token（只有一次 push 用，用完即清理）
git remote set-url origin https://<用户名>:<PAT>@github.com/<用户名>/<仓库名>.git
git push origin main
# 推完后立即恢复公开 URL
git remote set-url origin https://github.com/<用户名>/<仓库名>.git
```

> ⚠️ 不要将 PAT 写入任何脚本或配置文件。用完立即从 git remote 中清除。

### 7. 安全清理

```bash
# 离开前删除临时工作目录
rm -rf /tmp/hermes-multi-role-profiles
```

---

## 方向B：部署安装（GitHub → 新机器）

### 部署步骤

### 1. 克隆仓库
```bash
git clone https://github.com/chenlin9194/hermes-multi-role-profiles.git
```

### 2. 复制配置文件
```bash
cp -r hermes-multi-role-profiles/* ~/.hermes/
```

### 3. 修复角色切换脚本
由于原脚本可能存在问题，需要创建或修复 `~/.hermes/bin/hermes-profile`：

```bash
#!/bin/bash

# Hermes 多角色切换脚本
# 用法: hermes-profile [角色名称]

PROFILE_DIR="$HOME/.hermes/profiles"
CURRENT_SOUL="$HOME/.hermes/SOUL.md"

# 检查参数
if [ $# -eq 0 ]; then
    echo "可用角色:"
    echo "  pm    - 项目经理 (默认)"
    echo "  se    - 技术专家"
    echo "  assistant - 助理"
    echo "  writer - 写手"
    echo "  reviewer - 审稿专家"
    echo ""
    echo "当前角色: $(basename $(readlink -f $CURRENT_SOUL) 2>/dev/null || echo 'default')"
    exit 0
fi

ROLE=$1

# 检查角色是否存在
if [ ! -d "$PROFILE_DIR/$ROLE" ]; then
    echo "错误: 角色 '$ROLE' 不存在"
    echo "可用角色: pm, se, assistant, writer, reviewer"
    exit 1
fi

# 切换到指定角色
if [ "$ROLE" = "pm" ]; then
    # PM 是默认角色，使用根目录的 SOUL.md
    cp "$PROFILE_DIR/pm/SOUL.md" "$CURRENT_SOUL"
else
    cp "$PROFILE_DIR/$ROLE/SOUL.md" "$CURRENT_SOUL"
fi

echo "✅ 已切换到 $ROLE 角色"
echo "📍 当前 SOUL.md: $CURRENT_SOUL"
```

### 4. 添加执行权限
```bash
chmod +x ~/.hermes/bin/hermes-profile
```

### 5. 配置 PATH（可选）
```bash
# 临时生效（当前会话）
export PATH="$HOME/.hermes/bin:$PATH"

# 永久生效（添加到 ~/.bashrc）
echo 'export PATH="$HOME/.hermes/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## 角色说明

| 角色 | 职责 | 适用场景 |
|------|------|----------|
| **PM (项目经理)** | 目标拆解、任务路由、成果汇总 | 项目管理、任务分配、进度跟踪 |
| **SE (技术专家)** | 技术难题、代码分析、方案设计 | 技术攻关、代码审查、架构设计 |
| **Assistant (助理)** | 事务执行、信息检索、结构化输出 | 日常事务、信息整理、格式化输出 |
| **Writer (写手)** | 文档撰写、PPT生成、汇报材料 | 文档编写、报告制作、内容创作 |
| **Reviewer (审稿专家)** | 内容审查、视觉美学优化、PPT/文档审稿 | 文档审稿、PPT美化、质量把关 |

## 使用方法

### 命令行切换
```bash
# 切换到技术专家
hermes-profile se

# 切换到项目经理
hermes-profile pm

# 切换到助理
hermes-profile assistant

# 切换到写手
hermes-profile writer

# 切换到审稿专家
hermes-profile reviewer

# 查看可用角色
hermes-profile
```

### 对话中指定角色
直接在对话中说明：
- "让 SE 分析这个技术问题"
- "让 PM 帮我规划这个项目"
- "让 Assistant 整理这些信息"
- "让 Writer 帮我写个文档"

### 委派任务
PM 角色可通过 `delegate_task` 将任务分发给其他角色。

## 系统结构
```
~/.hermes/
├── SOUL.md              # 当前激活的角色配置
├── config.yaml          # 核心配置
├── profiles/            # 多角色配置目录
│   ├── pm/SOUL.md
│   ├── se/SOUL.md
│   ├── assistant/SOUL.md
│   ├── writer/SOUL.md
│   └── reviewer/SOUL.md
├── memories/            # 长期记忆（共享）
├── skills/              # 自定义技能（共享）
└── bin/                 # 工具脚本
    └── hermes-profile   # 角色切换脚本
```

## 核心特性

1. **角色隔离**：每个独立 Gateway 进程有完全隔离的 `sessions/`、`memories/` 和 `state.db`
2. **按需调度**：PM 根据任务性质自动路由任务（通过 `delegate_task`）
3. **人格隔离**：每个角色有独立的 `SOUL.md` 定义

> ⚠️ **重要**：当角色作为独立 Gateway 进程运行时（每个 profile 有自己的 gateway），**`memories/` 和 `skills/` 是不共享的**。每个 profile 的存储路径在 `profiles/<角色>/memories/` 和 `profiles/<角色>/skills/`，与主实例的 `~/.hermes/memories/` 完全隔离。这是后续所有协作模式设计的根本约束。

---

## 🚨 生产教训：数据孤岛是运行时第一大坑

### 真实案例

用户先与**助理**对话，助理整理了会议纪要和待办事项，存入了 `D:\Work\YYYY-MM-DD\` 共享目录。随后用户向 **PM** 要求输出日报，PM 完全不知道助理存了什么——因为两个角色的 `sessions/` 和 `memories/` 是彻底隔离的。

```
助理（独立Gateway）：收到信息 → 整理 → 写入 D:\Work\ ✅
PM  （另一独立Gateway）：收到\"出日报\" → 不知道数据在哪 → 输出空 ❌
```

### 根因：角色间的通信是两个独立问题

| 问题 | 本质 | 解决方案 |
|------|------|---------|
| **任务路由**（谁做什么） | 控制流问题 | `delegate_task` 程序化分派 |
| **数据共享**（结果放哪） | 数据流问题 | 共享文件系统总线 |

**两者必须同时解决**，缺一不可。

---

## 🛠 生产级协作模式：双通道数据总线

### 通道1：PM 程序化路由（delegate_task）

PM 用 `delegate_task` 内部拆分子任务，子任务结果自动回流：

```
用户需求 → PM拆解
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
 delegate  delegate  delegate
  (SE)     (助理)    (写手)
      │         │         │
      └─────────┼─────────┘
                ▼
          PM汇总验收 → 交付
```

每个 delegate 通过 `context` 字段注入 SOUL.md 内容，让子 Agent 以指定角色身份执行。

**优势**：
- ✅ 程序化，无需手动 @
- ✅ 支持批量并发
- ✅ 结果自动回流
- ✅ 内置超时/重试
- ✅ 上下文隔离（中间结果不进 PM token）

### 通道2：共享文件系统总线

所有角色的**持久化数据**写入约定好的共享目录，作为数据交换的"共享硬盘"：

```
约定的共享路径：/mnt/d/Work/YYYY-MM-DD/（或相应平台路径）
                  │
        ┌─────────┴─────────┐
        │                   │
   助理写入整理数据      PM读取生成日报
   写手读取素材              SE写入分析报告
   审稿读取审稿结果          ...
        │                   │
        └─────────┬─────────┘
                  ▼
           所有角色可见
```

**数据契约规范**：

```bash
# 目录结构（标准化版本）
D:\Work\YYYY-MM-DD\              ← 当日工作目录
 ├── shared\                     ← 公共区：所有人可读可写
 │   ├── tasks.md                ← 今日待办（助理维护）
 │   ├── risks.md                ← 风险登记（SE/全员可登记）
 │   └── decisions.md            ← 关键决议（全员可登记）
 ├── assistant\                  ← 助理工作区（会议纪要、日常整理）
 ├── se\                         ← 技术专家工作区（技术分析报告）
 ├── writer\                     ← 写手工作区（文档/PPT产出）
 └── reviewer\                   ← 审稿工作区（审稿意见）
```

**每个角色的写入和读取权限**：

| 角色 | 写入目录 | 可读目录 |
|------|---------|---------|
| PM | -（不直接写） | 所有目录 |
| 助理 | `assistant/` + `shared/tasks.md` + `shared/risks.md` | 所有目录 |
| SE | `se/` + `shared/risks.md` | `shared/`, `assistant/` |
| 写手 | `writer/` | `shared/`, `assistant/`, `se/` |
| 审稿 | `reviewer/` | `writer/`, `shared/` |

**文件命名规范**：`{类型}-{项目名}-{主题}.{扩展名}`（如 `会议纪要-Infiniti项目-STR4预评审.md`）

### 将数据契约注入各角色 SOUL.md

创建好共享目录后，必须将数据共享规则写入每个角色的 `SOUL.md`，否则各独立 Gateway 进程不知道共享目录的存在。在 SOUL.md 末尾追加一个 `## 团队数据共享契约` 章节：

```markdown
## 团队数据共享契约

本团队使用共享数据仓库进行跨角色数据同步。详见 `D:\Work\数据共享契约.md`。

### 你的职责
- 📝 **写入目录**：`D:\Work\YYYY-MM-DD\<角色目录>\`
- 📖 **可读目录**：`shared/`、`assistant/`、`se/` 等
- 📋 **公共区**：同步写入 `shared/tasks.md`、`shared/risks.md` 等

### 文件规范
- 文件名格式：`{类型}-{项目名}-{主题}.{扩展名}`
- 文件头标注日期和来源角色
- 使用 Markdown 格式，表格用 Pipe 格式
```

同时创建一份 **数据契约文档** `D:\Work\数据共享契约.md` 供各角色查阅

### 初始化共享目录

首次建立共享数据总线时，执行以下步骤：

```bash
# 1. 创建分角色目录
TODAY=$(date +%F)
WORK_DIR="/mnt/d/Work/$TODAY"
mkdir -p "$WORK_DIR"/{shared,assistant,se,writer,reviewer}

# 2. 创建 shared 公共文件
cat > "$WORK_DIR/shared/tasks.md" << 'EOF'
# ... 待办表格 ...
EOF
cat > "$WORK_DIR/shared/risks.md" << 'EOF'
# ... 风险表格 ...
EOF
cat > "$WORK_DIR/shared/decisions.md" << 'EOF'
# ... 决议表格 ...
EOF

# 3. 写入数据契约文档
# 见 D:\Work\数据共享契约.md
```

### 每个角色都知道去共享目录找什么
- **助理**：负责写入结构化整理数据到 `assistant/`，同步待办到 `shared/tasks.md`
- **PM**：负责从共享目录读取所有数据，汇总生成日报/周报
- **SE**：负责写入技术分析报告到 `se/`，同步风险到 `shared/risks.md`
- **写手**：负责从 `shared/` + `assistant/` + `se/` 读取素材，产出文档到 `writer/`
- **审稿**：负责从 `writer/` 读取待审文档，写入审稿意见到 `reviewer/`

### 决策矩阵：用哪个通道？

| 场景 | 推荐通道 | 原因 |
|------|---------|------|
| 技术分析、数据处理 | `delegate_task` | 结果直接回流，无需持久化 |
| 日报/周报生成 | 文件总线 | 需阅读历史数据，多人衔接 |
| 批量并行任务 | `delegate_task` | 并发能力强 |
| 文件/PPT 产出 | 文件总线 | 文件格式需持久化到磁盘 |
| 信息整理归档 | 文件总线 | 长期保存，后续检索 |
| 临时计算、一次查询 | `delegate_task` | 用完即弃，不污染文件系统 |

### 标准工作流

```
1. PM接收用户需求
2. PM拆解为子任务
     ├─ 技术类 → delegate(SE)
     ├─ 整理类 → delegate(助理)
     └─ 输出类 → delegate(写手) → 写入共享文件
3. SE/助理/写手执行任务
     ├─ 中间结果：用 delegate 回流给 PM
     └─ 持久化结果：写入 D:\Work\ 共享目录
4. PM汇总所有结果，验收
5. PM输出最终交付
```

### 对外输出审稿流水线（强制规则）

所有对外交付的文档/PPT，必须经过以下**强制流水线**，由 PM 路由逻辑保证：

```
写手产出 → 写入 writer/目录
               ↓
    PM 自动触发 Reviewer
               ↓
    Reviewer 审稿 → 写入 reviewer/审稿意见.md
               ↓
       ┌── 通过？→ PM 交付给用户
       └── 有问题？→ 退回 Writer 修改 → 再次送审
```

**判定条件**（PM 检查）：

- `reviewer/` 目录下缺少对应审稿意见文件 → 拒绝交付，强行触发 Reviewer
- 审稿意见中有 P0 级别问题 → 退回 Writer
- 审稿意见全部 P1/P2 可选修改 → 可选择是否交付

**事后审稿流程**（初次建立共享总线时，对已交付内容补审）：

1. 从写手的 PPT/文档输出路径找到已交付文件
2. 提取内容（`python -m markitdown file.pptx` 或 `python-pptx`）
3. 按逐页审查标准（文字、排版、视觉、布局、内容完整度）出审稿意见
4. 写入 `reviewer/审稿意见-{目标文件名}.md`
5. 告知用户审稿结论和修改建议

**审稿意见格式**：

```markdown
## 审稿意见 - {PPT/文档名称}

**审稿日期：** YYYY-MM-DD
**审稿人：** Reviewer

### 第N页（{页面标题}）
| 类型 | 问题描述 | 建议修改 | 优先级 |
|------|---------|---------|-------|
| 文字 | ... | ... | P0 |
| 排版 | ... | ... | P1 |
| 视觉 | ... | ... | P2 |

优先级定义：
- P0：必须改（内容/数据错误）
- P1：建议改（措辞/排版/布局优化）
- P2：锦上添花（视觉细节/模板规范）
```

---

## ⚠️ 常见误区：为什么角色在飞书/消息平台上不回应？

很多用户期望在飞书上可以直接 @写手 或 @SE 单独对话，但这是不工作的。原因如下：

### 架构真相：只有「一个 Agent + 一堆岗位说明书」

```
用户 ──▶ 飞书 ──▶ Hermes 网关（1个实例）
                      │
                      ├── 加载 SOUL.md → 当前角色
                      │
                      └── profiles/ ── 其他角色的"说明书"文件
                           ├── writer/SOUL.md    ← 只是定义，不是进程
                           ├── se/SOUL.md        ← 只是定义，不是进程
                           └── assistant/SOUL.md ← 只是定义，不是进程
```

- **Hermes 网关只跑了一个进程**，它的身份由 `~/.hermes/SOUL.md` 决定
- **其他角色的 SOUL.md 只是定义文件**（岗位说明书），不是独立运行的 Agent
- **没有独立的消息通道**，子角色不监听飞书消息

### 正确用法

**通过 PM 路由，不要直接找子角色对话：**

| ❌ 错误用法 | ✅ 正确用法 |
|-----------|-----------|
| 飞书对写手说："写一份周报" | 飞书对 PM 说："**让写手**帮我写一份周报" |
| 飞书对SE说："分析这个bug" | 飞书对 PM 说："**让SE**分析这个bug" |
| @写手Bot 发消息（没有独立Bot） | PM 接收后用 `delegate_task()` 派发给子角色 |

### 子角色如何"干活"？

PM 收到用户请求后，用 `delegate_task()` 创建子 Agent：
- 子 Agent 在**隔离上下文**中执行任务
- 干完后结果返回给 PM
- PM **验收并整理后**回复用户
- 子角色**不直接回消息**给用户

### 如果一定要独立对话

详见下一节「独立 Bot 方案」

## 独立 Bot 方案（可选进阶）

如果需要让每个角色成为独立的飞书机器人（用户可直接 @对应Bot 对话），需要：

### 前提条件
- 飞书开放平台管理员权限
- 每个角色一个自建应用（APP_ID / APP_SECRET）

### 关键：访问权限控制

Bot 配置完成后，如果 `FEISHU_ALLOW_ALL_USERS=false`（默认），用户发消息会显示：
```
Unauthorized user: ou_f8c6407751e804379c95a25b8bda784b (None) on feishu
```

**解决方案**（二选一）：

```bash
# 方式 A：开放给所有用户（开发/测试用，推荐）
sed -i 's/FEISHU_ALLOW_ALL_USERS=false/FEISHU_ALLOW_ALL_USERS=true/' ~/.hermes/profiles/<角色>/.env

# 方式 B：仅限特定用户（生产用）
echo 'FEISHU_ALLOW_ALL_USERS=false' >> ~/.hermes/profiles/<角色>/.env
echo 'FEISHU_ALLOWED_USERS=ou_xxx1,ou_xxx2' >> ~/.hermes/profiles/<角色>/.env
```

> ⚠️ **修改后必须重启网关才生效！** 见下方「WSL 环境中的网关管理」

### 步骤（使用 Hermes Profile，推荐）

如果使用 `hermes profile create` 创建的独立 profile（每个 profile 有独立的 `.env` 和 `config.yaml`）：

1. 在飞书开放平台为每个 Bot 创建自建应用，开通机器人能力
2. 为每个 profile 的 `.env` 填入对应的 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`：
   ```bash
   # ~/.hermes/profiles/<角色>/.env
   FEISHU_APP_ID=cli_xxx
   FEISHU_APP_SECRET=xxx
   FEISHU_DOMAIN=feishu
   FEISHU_CONNECTION_MODE=websocket
   ```
3. **关键：设置访问权限** — 否则用户发消息会显示 `Unauthorized user`：
   ```bash
   # 方式 A：开放给所有用户（测试用）
   echo 'FEISHU_ALLOW_ALL_USERS=true' >> ~/.hermes/profiles/<角色>/.env

   # 方式 B：仅限特定用户（生产用）
   echo 'FEISHU_ALLOW_ALL_USERS=false' >> ~/.hermes/profiles/<角色>/.env
   echo 'FEISHU_ALLOWED_USERS=ou_xxx1,ou_xxx2' >> ~/.hermes/profiles/<角色>/.env
   ```
4. 启动网关：
   ```bash
   hermes --profile <角色> gateway run --replace
   ```

### 批量配置脚本

```bash
# 一键给所有 profile 启用全部开放
for p in se reviewer assistant writer; do
  sed -i 's/FEISHU_ALLOW_ALL_USERS=false/FEISHU_ALLOW_ALL_USERS=true/' ~/.hermes/profiles/$p/.env
done

# 批量重启
for p in se reviewer assistant writer; do
  kill $(cat ~/.hermes/profiles/$p/gateway.pid 2>/dev/null) 2>/dev/null
  hermes --profile $p gateway run --replace
done
```

### 验证连接

```bash
# 方法 A：查看 profile 列表状态
hermes profile list

# 方法 B：查看进程
ps aux | grep "gateway run" | grep -v grep

# 方法 C：查看飞书 WebSocket 连接日志（WSL 可用）
journalctl --user -u hermes-gateway* --no-pager | grep "connected to wss"

# 方法 D：通过飞书 API 验证 Bot 身份
curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"<APP_ID>","app_secret":"<APP_SECRET>"}' | jq -r '.tenant_access_token' | \
  xargs -I {} curl -s -H "Authorization: Bearer {}" "https://open.feishu.cn/open-apis/bot/v3/info"
```

### 注意：open_id 跨应用隔离

每个飞书应用的用户 open_id 是**应用级隔离**的：
- PM Bot 看到用户是 `ou_cfb089cf77...`
- Writer Bot 看同一个用户是不同的 `ou_9637675e8...`
- 不能用 PM 的 open_id 通过 Writer 的 API 发消息（`open_id cross app` 错误）

测试各 Bot 收发消息时，需要在对应 Bot 的飞书对话框内直接发送。

## WSL 环境中的网关管理

WSL 没有 systemd 用户会话，`hermes gateway restart` 会报错：
```
✗ User systemd not reachable:
  User D-Bus socket is missing even though linger is enabled.
```

### 查看网关进程

```bash
# 查看所有 profile 网关进程
ps aux | grep "gateway run" | grep -v grep

# 输出示例：
# ... --profile writer gateway run --replace
# ... --profile se gateway run --replace
# ... --profile reviewer gateway run --replace
```

### 停止网关（手动）

```bash
# 方式 A：通过 PID 文件（推荐）
kill $(cat ~/.hermes/profiles/<角色>/gateway.pid 2>/dev/null)

# 方式 B：强力终止已知 PID
kill -9 <PID>

# 清理 stale PID 文件
rm -f ~/.hermes/profiles/<角色>/gateway.pid
```

### 启动/重启网关

```bash
# 单 profile 启动
hermes --profile <角色> gateway run --replace
```

`--replace` 是关键标志：它会检查是否有同 profile 旧进程并替换之，然后自动 daemonize 到后台。

> ⚠️ **不能使用 & background** 启动（Hermes 会拒绝）。直接用 `gateway run --replace`，命令会自动 daemonize。

### 批量管理脚本

```bash
# 一键重启所有非 default profile 的网关
for p in se reviewer assistant writer; do
  kill $(cat ~/.hermes/profiles/$p/gateway.pid 2>/dev/null) 2>/dev/null
  rm -f ~/.hermes/profiles/$p/gateway.pid
  hermes --profile $p gateway run --replace
done

# 等待连接
sleep 5
# 验证
ps aux | grep "gateway run" | grep -v grep
journalctl --user -u hermes-gateway* --no-pager | grep "connected to wss"
```

### 常见 Debug：飞书连接

| 症状 | 原因 | 解决 |
|------|------|------|
| `Unauthorized user: ou_xxx` | `ALLOW_ALL_USERS=false` 且用户未批准 | 设为 `true` 或添加 `ALLOWED_USERS`；或写入 pairing store |
| `Code 'xxx' not found or expired` | 配对码发到了错的 Hermes 实例 | 去生成该配对码的 profile 进程里执行 approve |
| Bot 收不到消息但进程在跑 | 权限配置变更后未重启 | 重启网关进程 |
| `FEISHU_ALLOW_ALL_USERS` 修改后不生效 | 进程仍在用旧环境变量 | Kill 旧进程 → 重新 `--replace` |
| `open_id cross app` | 用 A App 的 open_id 通过 B App 发消息 | 每个 Bot 用各自 App 内的 open_id |
| Bot 显示在线（ps 有进程）但长时间不回复 | `--replace` 残留僵尸 + WebSocket 断连后进程静默退出 | 对比 `gateway_state.json.pid` 与真实进程；检查 `agent.log` 最近日志时间戳；强杀后重启 |
| Agent 崩溃: `ImportError: cannot import name 'cfg_get' from 'hermes_cli.config'` | `__pycache__` 字节码缓存与源码不一致 | 清所有 `__pycache__` + `*.pyc`，重启 gateway |
| Agent 崩溃: `ImportError: cannot import name 'atomic_replace' from 'utils'` | 同上 — 批量缓存损坏 | 同上 |

### 系统性诊断流程：Bot 不响应

当某个角色的 Bot 在飞书群里不响应时，不要零散排查。按以下顺序系统排查：

```bash
# 步骤 1：确认进程存活
ps aux | grep "gateway run --profile <角色>" | grep -v grep
# → 没进程：`hermes --profile <角色> gateway run --replace`

# 步骤 2：确认 Feishu 连接状态
cat ~/.hermes/profiles/<角色>/gateway_state.json | python3 -m json.tool
# → 检查 platforms.feishu.state 是否为 "connected"

# 步骤 3：检查 gateway.log 看错误类型
tail -50 ~/.hermes/profiles/<角色>/logs/gateway.log
# → 找新消息到达后的关键日志：Received → Flushing → next action
```

**日志流模式判断：**

```
日志流 A: Received → Flushing → "inbound message" → "response ready" → "Sending"
  结论：正常。Bot 已响应。

日志流 B: Received → Flushing → "Unauthorized user: ou_xxx"
  结论：用户未授权。修复见下方「配对存储」节。

日志流 C: Received → Flushing → "Agent error" + ImportError traceback
  结论：Agent 启动失败。修复：

    1. 清理字节码缓存：
       find /home/linchen/.hermes/hermes-agent -name "__pycache__" -type d -exec rm -rf {} +
       find /home/linchen/.hermes/hermes-agent -name "*.pyc" -delete

    2. 重启：
       kill $(cat ~/.hermes/profiles/<角色>/gateway.pid)
       hermes --profile <角色> gateway run --replace

日志流 D: Flushing 后的行完全不出现（空档）
  结论：Agent 启动失败但日志被截断，或模型 API 超时。检查 agent.log + errors.log。

日志流 E: 日志在 30 分钟前完全停止，但 ps 显示进程仍在
  结论：***关键陷阱*** — 进程是 `--replace` 后的残留僵尸，真正的网关进程已因 WebSocket 断连（1011 keepalive ping timeout）静默退出。
  修复：强杀残留 `kill -9 $(cat .../gateway.pid)` → `hermes --profile <角色> gateway run --replace`
  详见 [debug-stale-zombie-websocket-disconnect.md](references/debug-stale-zombie-websocket-disconnect.md)
```

### 配对/批准机制详解

#### 两独立层次的用户认证

用户消息从飞书到达后，需通过 **两层检查**：

```
飞书消息 → ① Feishu Adapter 层级 → ② Gateway 层级 → Agent
                │                            │
        检查 FEISHU_GROUP_POLICY       检查 FEISHU_ALLOW_ALL_USERS
        和 allowed_group_users         和 FEISHU_ALLOWED_USERS
                                      和 pairing_store.is_approved()
```

即使 Adapter 层放行（`GROUP_POLICY=open`），Gateway 层仍可能拒绝（`Unauthorized user`）。

#### 配对存储

每个 profile 的批准用户存储在：

```
~/.hermes/profiles/<角色>/platforms/pairing/
    ├── feishu-approved.json    ← 已批准用户列表
    ├── feishu-pending.json     ← 待批准配对码
    └── _rate_limits.json       ← 速率限
```

**已批准** 示例（与其他角色格式一致）：
```json
{
  "ou_f8c6407751e804379c95a25b8bda784b": {
    "user_name": "",
    "approved_at": 1777270241.9251142
  }
}
```

**每个 Feishu bot 有自己的 App ID 和 Feishu 租户。** 同一个人在不同的 Bot 中有不同的 `open_id`。所以：
- 助理 Bot 中用户 ID：`ou_7f2628d10c645ad3f993ba64bcec1328`
- Writer Bot 中同一用户：`ou_f8c6407751e804379c95a25b8bda784b`
- SE Bot：`ou_9637675e8e736e6ba40778bc4da18c0e`
- Reviewer Bot：`ou_1fa9c918711c9a34af8f29e567986bba`

**误判案例：** 其他角色都工作，唯独 Writer 不响应。原因不是 Writer 配置不同，而是其他角色在部署时已完成配对（`feishu-approved.json` 存在），Writer 从未配过。

#### 修复方案（三选一）

```bash
# 方式 A：创建批准文件（推荐）
# 1. 从 "Unauthorized user" 日志中获取用户 open_id
# 2. 创建配对批准
cat > ~/.hermes/profiles/<角色>/platforms/pairing/feishu-approved.json << 'EOF'
{
  "ou_<用户open_id>": {
    "user_name": "",
    "approved_at": $(date +%s)
  }
}
EOF

# 方式 B：使用配对码
# 1. 在飞书向该 Bot 发私信 → Bot 返回配对码
# 2. 在 Bot 所在 profile 下执行配对批准
hermes pairing approve feishu <配对码>

# 方式 C：开放所有人
# 适合测试/开发环境，不推荐生产
sed -i 's/FEISHU_ALLOW_ALL_USERS=false/FEISHU_ALLOW_ALL_USERS=true/' ~/.hermes/profiles/<角色>/.env
# ⚠️ 修改后必须重启 gateway
```

> ⚠️ 配对批准文件创建后立刻生效（PairingStore 每次调用都从磁盘读取），**无需重启 gateway**。但如果修改 .env 中的 `FEISHU_ALLOW_ALL_USERS`，则必须重启。

### 权衡
- **优点**：角色完全隔离，用户可直接找对应 Bot 对话
- **缺点**：运维成本高（5个进程）、角色间不共享对话上下文、需逐一创建飞书应用
- **推荐**：先用单 Bot + 角色路由方案，确有需要再升级

## 故障排除

### 命令未找到
```bash
# 检查 PATH
echo $PATH | grep ~/.hermes/bin

# 如果没有输出，添加 PATH
export PATH="$HOME/.hermes/bin:$PATH"
```

### 角色切换失败
```bash
# 检查脚本权限
ls -la ~/.hermes/bin/hermes-profile

# 检查角色目录
ls -la ~/.hermes/profiles/

# 检查 SOUL.md 文件
ls -la ~/.hermes/SOUL.md
```

## 验证部署
```bash
# 测试角色切换
hermes-profile se
hermes-profile pm
hermes-profile assistant
hermes-profile writer

# 查看当前角色配置
head -10 ~/.hermes/SOUL.md
```

## 注意事项

- 确保 Hermes Agent 已正确安装
- 角色配置文件路径正确
- 脚本具有执行权限
- PATH 配置正确以便命令可用

## Reference Files

| File | Description |
|------|-------------|
| [debug-nonresponsive-bot-session.md](references/debug-nonresponsive-bot-session.md) | Real-world case study: debugging a non-responsive Feishu Bot (pycache corruption + pairing/approval missing) |
| [debug-stale-zombie-websocket-disconnect.md](references/debug-stale-zombie-websocket-disconnect.md) | Real-world case study: stale `--replace` zombie process + WebSocket 1011 ping timeout → silent exit |
| [deploy-github-skill-to-profile.md](references/deploy-github-skill-to-profile.md) | Deploying a GitHub repo as a Hermes profile skill (cross-filesystem rsync, symlinks, .venv setup) |
| [sync-config-to-github.md](references/sync-config-to-github.md) | Syncing local ~/.hermes config to GitHub reference repo: diff methodology, security rules, watchdog v2 upgrade, push auth |