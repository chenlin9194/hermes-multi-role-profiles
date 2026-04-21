# Hermes 多角色协作配置

基于 Hermes Agent 的多角色协作系统配置，四个角色共享数据、按需调度。

## 角色定义

| 角色 | 职责 | 配置文件 |
|------|------|----------|
| PM (项目经理) | 目标拆解、任务路由、成果汇总 | `SOUL.md` (默认) |
| SE (技术专家) | 技术难题、代码分析、方案设计 | `profiles/se/SOUL.md` |
| Assistant (助理) | 事务执行、信息检索、结构化输出 | `profiles/assistant/SOUL.md` |
| Writer (写手) | 文档撰写、PPT生成、汇报材料 | `profiles/writer/SOUL.md` |

## 目录结构

```
~/.hermes/
├── SOUL.md              # 默认人格 (PM)
├── config.yaml          # 核心配置
├── profiles/            # 多角色配置
│   ├── pm/SOUL.md
│   ├── se/SOUL.md
│   ├── assistant/SOUL.md
│   └── writer/SOUL.md
├── memories/            # 长期记忆
│   ├── MEMORY.md        # 系统记忆
│   └── USER.md          # 用户画像
├── skills/              # 自定义技能
└── bin/                 # 工具脚本
    └── hermes-profile   # 角色切换脚本
```

## 使用方式

### 方式一：对话中指定角色
直接在对话中说明："让 SE 分析这个技术问题"

### 方式二：命令行切换
```bash
hermes-profile se    # 切换到技术专家
hermes-profile pm    # 切换到项目经理
```

### 方式三：委派任务
PM 角色可通过 `delegate_task` 将任务分发给其他角色。

## 核心特性

1. **数据共享**：所有角色共享 `memories/` 和 `skills/`
2. **按需调度**：PM 根据任务性质自动路由
3. **人格隔离**：每个角色有独立的 `SOUL.md` 定义

## 安装

将文件复制到 `~/.hermes/` 目录即可：

```bash
git clone https://github.com/chenlin9194/hermes-multi-role-profiles.git
cp -r hermes-multi-role-profiles/* ~/.hermes/
chmod +x ~/.hermes/bin/hermes-profile
```

## 注意事项

⚠️ **敏感信息安全**：
- `.env` 包含 API 密钥，**绝不上传**
- `auth.json` 包含登录凭证，**绝不上传**
- 上传前请检查 `config.yaml` 是否包含密钥

## License

MIT
